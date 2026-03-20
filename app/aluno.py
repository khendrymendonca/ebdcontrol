import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.supabase_client import get_supabase, get_supabase_admin
from datetime import date
import json

aluno_bp = Blueprint("aluno", __name__)


def aluno_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def get_turma_aluno():
    """Retorna a turma_id do aluno logado."""
    return session.get("turma_id")


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@aluno_bp.route("/dashboard")
@aluno_required
def dashboard():
    sb = get_supabase_admin()
    aluno_id = session["user"]["id"]
    turma_id = get_turma_aluno()

    if not turma_id:
        # Buscar matrícula do aluno
        r = sb.table("turma_alunos").select("turma_id").eq("aluno_id", aluno_id).maybe_single().execute()
        if r.data:
            turma_id = r.data["turma_id"]
            session["turma_id"] = turma_id

    stats = {"media": 0, "presenca_pct": 0, "ranking": 0, "trabalhos_pendentes": 0}
    ranking = []
    aniversariantes = []
    proximo_prazo = None

    try:
        # Notas do aluno
        notas_r = sb.table("respostas_prova").select("nota").eq("aluno_id", aluno_id).eq("corrigida", True).execute()
        notas = [x["nota"] for x in (notas_r.data or []) if x.get("nota") is not None]
        if notas:
            stats["media"] = round(sum(notas) / len(notas), 1)

        # Presença
        if turma_id:
            pres_r = sb.table("presencas").select("status").eq("aluno_id", aluno_id).eq("turma_id", turma_id).execute()
            pres = pres_r.data or []
            if pres:
                presentes = sum(1 for p in pres if p["status"] == "presente")
                stats["presenca_pct"] = round((presentes / len(pres)) * 100, 1)

            # Ranking geral
            alunos_r = sb.table("turma_alunos").select("aluno_id").eq("turma_id", turma_id).execute()
            medias_alunos = []
            for a in (alunos_r.data or []):
                nr = sb.table("respostas_prova").select("nota").eq("aluno_id", a["aluno_id"]).eq("corrigida", True).execute()
                ns = [x["nota"] for x in (nr.data or []) if x.get("nota") is not None]
                medias_alunos.append((a["aluno_id"], round(sum(ns)/len(ns), 1) if ns else 0))

            medias_alunos.sort(key=lambda x: -x[1])
            for i, (aid, _) in enumerate(medias_alunos):
                if aid == aluno_id:
                    stats["ranking"] = i + 1
                    break
            ranking = medias_alunos[:5]

            # Próximo prazo
            trab_r = sb.table("trabalhos").select("titulo, prazo").eq("turma_id", turma_id).eq("visivel", True).order("prazo").limit(1).execute()
            if trab_r.data:
                proximo_prazo = trab_r.data[0]

            # Trabalhos pendentes de entrega
            trablist = sb.table("trabalhos").select("id").eq("turma_id", turma_id).eq("visivel", True).execute()
            pendentes = 0
            for t in (trablist.data or []):
                e = sb.table("entregas_trabalho").select("id").eq("aluno_id", aluno_id).eq("trabalho_id", t["id"]).execute()
                if not e.data:
                    pendentes += 1
            stats["trabalhos_pendentes"] = pendentes

            # Aniversariantes
            hoje = date.today()
            alunos_aniv = sb.table("turma_alunos").select("profiles(nome, data_nasc)").eq("turma_id", turma_id).execute()
            for a in (alunos_aniv.data or []):
                p = a.get("profiles", {})
                dn = p.get("data_nasc", "")
                if dn:
                    try:
                        mes = int(dn.split("-")[1])
                        if mes == hoje.month:
                            aniversariantes.append(p)
                    except Exception:
                        pass

    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("aluno/dashboard.html",
                           stats=stats, ranking=ranking,
                           aniversariantes=aniversariantes,
                           proximo_prazo=proximo_prazo,
                           turma_id=turma_id, user=session["user"])


# ─── MATERIAIS ───────────────────────────────────────────────────────────────

@aluno_bp.route("/materiais")
@aluno_required
def materiais():
    sb = get_supabase_admin()
    turma_id = get_turma_aluno()
    lista = []
    try:
        r = sb.table("materiais").select("*").eq("turma_id", turma_id).eq("visivel", True).order("created_at", desc=True).execute()
        lista = r.data or []
    except Exception as e:
        flash(f"Erro: {e}", "error")
    return render_template("aluno/materiais.html", materiais=lista, user=session["user"])


# ─── PROVAS ──────────────────────────────────────────────────────────────────

@aluno_bp.route("/provas")
@aluno_required
def provas():
    sb = get_supabase_admin()
    turma_id = get_turma_aluno()
    aluno_id = session["user"]["id"]
    lista = []
    try:
        r = sb.table("provas").select("*").eq("turma_id", turma_id).eq("visivel", True).execute()
        provas_raw = r.data or []
        for prova in provas_raw:
            # Verificar se já respondeu
            resp = sb.table("respostas_prova").select("*").eq("aluno_id", aluno_id).eq("prova_id", prova["id"]).maybe_single().execute()
            prova["resposta"] = resp.data
            lista.append(prova)
    except Exception as e:
        flash(f"Erro: {e}", "error")
    return render_template("aluno/provas.html", provas=lista, user=session["user"])


@aluno_bp.route("/provas/<prova_id>/responder", methods=["GET", "POST"])
@aluno_required
def responder_prova(prova_id):
    sb = get_supabase_admin()
    aluno_id = session["user"]["id"]

    if request.method == "POST":
        try:
            respostas = {}
            for key, val in request.form.items():
                if key.startswith("questao_"):
                    respostas[key] = val

            # Verificar se já respondeu
            existe = sb.table("respostas_prova").select("id").eq("aluno_id", aluno_id).eq("prova_id", prova_id).maybe_single().execute()
            if existe.data:
                flash("Você já respondeu esta prova.", "error")
            else:
                sb.table("respostas_prova").insert({
                    "aluno_id": aluno_id,
                    "prova_id": prova_id,
                    "respostas_json": json.dumps(respostas),
                    "corrigida": False
                }).execute()
                flash("Prova enviada! Aguarde a correção.", "success")
        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("aluno.provas"))

    prova = {}
    try:
        r = sb.table("provas").select("*").eq("id", prova_id).single().execute()
        prova = r.data or {}
        if prova.get("questoes_json"):
            prova["questoes"] = json.loads(prova["questoes_json"])
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("aluno/responder_prova.html", prova=prova, user=session["user"])


# ─── TRABALHOS ───────────────────────────────────────────────────────────────

@aluno_bp.route("/trabalhos", methods=["GET", "POST"])
@aluno_required
def trabalhos():
    sb = get_supabase_admin()
    turma_id = get_turma_aluno()
    aluno_id = session["user"]["id"]

    if request.method == "POST":
        trabalho_id = request.form["trabalho_id"]
        arquivo = request.files.get("arquivo")
        try:
            arquivo_url = ""
            if arquivo and arquivo.filename:
                file_bytes = arquivo.read()
                file_name = f"entregas/{turma_id}/{aluno_id}/{arquivo.filename}"
                sb.storage.from_("trabalhos").upload(file_name, file_bytes,
                    {"content-type": arquivo.content_type or "application/pdf"})
                arquivo_url = sb.storage.from_("trabalhos").get_public_url(file_name)

            existe = sb.table("entregas_trabalho").select("id").eq("aluno_id", aluno_id).eq("trabalho_id", trabalho_id).maybe_single().execute()
            if existe.data:
                sb.table("entregas_trabalho").update({
                    "arquivo_url": arquivo_url, "data_entrega": str(date.today())
                }).eq("id", existe.data["id"]).execute()
                flash("Trabalho atualizado!", "success")
            else:
                sb.table("entregas_trabalho").insert({
                    "aluno_id": aluno_id, "trabalho_id": trabalho_id,
                    "arquivo_url": arquivo_url, "data_entrega": str(date.today())
                }).execute()
                flash("Trabalho enviado!", "success")
        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("aluno.trabalhos"))

    lista = []
    try:
        r = sb.table("trabalhos").select("*").eq("turma_id", turma_id).eq("visivel", True).order("prazo").execute()
        for trab in (r.data or []):
            e = sb.table("entregas_trabalho").select("*").eq("aluno_id", aluno_id).eq("trabalho_id", trab["id"]).maybe_single().execute()
            trab["entrega"] = e.data
            lista.append(trab)
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("aluno/trabalhos.html", trabalhos=lista, user=session["user"])


# ─── NOTAS ───────────────────────────────────────────────────────────────────

@aluno_bp.route("/notas")
@aluno_required
def notas():
    sb = get_supabase_admin()
    turma_id = get_turma_aluno()
    aluno_id = session["user"]["id"]
    notas_provas = []
    notas_trabalhos = []
    media_geral = None
    posicao_ranking = None

    try:
        # Notas de provas
        r = sb.table("respostas_prova").select("*, provas(titulo, peso)").eq("aluno_id", aluno_id).eq("corrigida", True).execute()
        notas_provas = r.data or []

        # Notas de trabalhos
        e = sb.table("entregas_trabalho").select("*, trabalhos(titulo, peso)").eq("aluno_id", aluno_id).execute()
        notas_trabalhos = [x for x in (e.data or []) if x.get("nota") is not None]

        # Média geral
        valores = [(x["nota"], x.get("provas", {}).get("peso", 1)) for x in notas_provas if x.get("nota") is not None]
        valores += [(x["nota"], x.get("trabalhos", {}).get("peso", 1)) for x in notas_trabalhos]
        if valores:
            total = sum(n * p for n, p in valores)
            peso = sum(p for _, p in valores)
            media_geral = round(total / peso, 1) if peso else 0

        # Ranking
        alunos_r = sb.table("turma_alunos").select("aluno_id").eq("turma_id", turma_id).execute()
        medias = []
        for a in (alunos_r.data or []):
            nr = sb.table("respostas_prova").select("nota").eq("aluno_id", a["aluno_id"]).eq("corrigida", True).execute()
            ns = [x["nota"] for x in (nr.data or []) if x.get("nota") is not None]
            medias.append((a["aluno_id"], round(sum(ns)/len(ns), 1) if ns else 0))
        medias.sort(key=lambda x: -x[1])
        for i, (aid, _) in enumerate(medias):
            if aid == aluno_id:
                posicao_ranking = i + 1
                break

    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("aluno/notas.html",
                           notas_provas=notas_provas, notas_trabalhos=notas_trabalhos,
                           media_geral=media_geral, posicao_ranking=posicao_ranking,
                           total_alunos=len(alunos_r.data) if 'alunos_r' in dir() else 0,
                           user=session["user"])
