import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.supabase_client import get_supabase, get_supabase_admin
from datetime import date

professor_bp = Blueprint("professor", __name__)


def professor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session or session["user"].get("tipo") != "professor":
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def get_turma_ativa():
    """Retorna o turma_id da sessão."""
    return session.get("turma_id")


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@professor_bp.route("/dashboard")
@professor_required
def dashboard():
    sb = get_supabase_admin()
    turma_id = get_turma_ativa()

    stats = {"total_alunos": 0, "media_geral": 0, "presenca_media": 0, "trabalhos_pendentes": 0}
    ranking = []
    aniversariantes = []
    turmas = []

    try:
        # Listar turmas do professor
        t = sb.table("turmas").select("*").eq("professor_id", session["user"]["id"]).execute()
        turmas = t.data or []

        if not turma_id and turmas:
            turma_id = turmas[0]["id"]
            session["turma_id"] = turma_id

        if turma_id:
            # Total de alunos
            alunos_r = sb.table("turma_alunos").select("aluno_id, profiles(*)").eq("turma_id", turma_id).execute()
            alunos = alunos_r.data or []
            stats["total_alunos"] = len(alunos)

            # Aniversariantes do mês
            hoje = date.today()
            for a in alunos:
                p = a.get("profiles", {})
                dn = p.get("data_nasc")
                if dn:
                    try:
                        mes_nasc = int(dn.split("-")[1])
                        if mes_nasc == hoje.month:
                            aniversariantes.append(p)
                    except Exception:
                        pass

            # Médias de notas
            notas_r = sb.table("respostas_prova").select("nota, aluno_id").eq("corrigida", True).execute()
            notas = [x["nota"] for x in (notas_r.data or []) if x.get("nota") is not None]
            if notas:
                stats["media_geral"] = round(sum(notas) / len(notas), 1)

            # Presença média
            presencas_r = sb.table("presencas").select("status").eq("turma_id", turma_id).execute()
            pres = presencas_r.data or []
            if pres:
                presentes = sum(1 for p in pres if p["status"] == "presente")
                stats["presenca_media"] = round((presentes / len(pres)) * 100, 1)

            # Trabalhos pendentes de correção
            entregas_r = sb.table("entregas_trabalho").select("id").is_("nota", "null").execute()
            stats["trabalhos_pendentes"] = len(entregas_r.data or [])

            # Ranking de alunos
            aluno_notas = {}
            for a in alunos:
                aid = a["aluno_id"]
                aluno_notas[aid] = {"nome": a.get("profiles", {}).get("nome", ""), "media": 0, "notas": []}

            notas_r2 = sb.table("respostas_prova").select("aluno_id, nota").eq("corrigida", True).execute()
            for n in (notas_r2.data or []):
                if n["aluno_id"] in aluno_notas and n.get("nota") is not None:
                    aluno_notas[n["aluno_id"]]["notas"].append(n["nota"])

            for aid, info in aluno_notas.items():
                if info["notas"]:
                    info["media"] = round(sum(info["notas"]) / len(info["notas"]), 1)

            ranking = sorted(aluno_notas.values(), key=lambda x: x["media"], reverse=True)

    except Exception as e:
        flash(f"Erro ao carregar dashboard: {e}", "error")

    return render_template(
        "professor/dashboard.html",
        stats=stats,
        ranking=ranking[:10],
        aniversariantes=aniversariantes,
        turmas=turmas,
        turma_id=turma_id,
        user=session["user"]
    )


@professor_bp.route("/trocar-turma/<turma_id>")
@professor_required
def trocar_turma(turma_id):
    session["turma_id"] = turma_id
    return redirect(request.referrer or url_for("professor.dashboard"))


# ─── ALUNOS ──────────────────────────────────────────────────────────────────

@professor_bp.route("/alunos", methods=["GET", "POST"])
@professor_required
def alunos():
    sb = get_supabase_admin()
    turma_id = get_turma_ativa()

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "criar":
                nome = request.form["nome"]
                email = request.form["email"]
                senha = request.form["senha"]
                data_nasc = request.form.get("data_nasc", "")
                # Criar usuário no Supabase Auth
                result = sb.auth.admin.create_user({
                    "email": email,
                    "password": senha,
                    "email_confirm": True
                })
                uid = result.user.id
                # Criar perfil
                sb.table("profiles").insert({
                    "id": uid, "nome": nome, "email": email,
                    "tipo": "aluno", "data_nasc": data_nasc or None
                }).execute()
                # Matricular na turma
                if turma_id:
                    sb.table("turma_alunos").insert({"turma_id": turma_id, "aluno_id": uid}).execute()
                flash(f"Aluno '{nome}' criado com sucesso!", "success")

            elif action == "editar":
                aluno_id = request.form["aluno_id"]
                sb.table("profiles").update({
                    "nome": request.form["nome"],
                    "data_nasc": request.form.get("data_nasc") or None
                }).eq("id", aluno_id).execute()
                flash("Aluno atualizado!", "success")

            elif action == "remover":
                aluno_id = request.form["aluno_id"]
                sb.table("turma_alunos").delete().eq("turma_id", turma_id).eq("aluno_id", aluno_id).execute()
                flash("Aluno removido da turma.", "success")

            elif action == "criar_turma":
                sb.table("turmas").insert({
                    "nome": request.form["nome_turma"],
                    "professor_id": session["user"]["id"],
                    "ano": request.form.get("ano", "2025"),
                    "semestre": request.form.get("semestre", "1")
                }).execute()
                flash("Turma criada!", "success")

        except Exception as e:
            flash(f"Erro: {e}", "error")

        return redirect(url_for("professor.alunos"))

    # GET
    alunos_lista = []
    turmas = []
    try:
        t = sb.table("turmas").select("*").eq("professor_id", session["user"]["id"]).execute()
        turmas = t.data or []
        if turma_id:
            r = sb.table("turma_alunos").select("aluno_id, profiles(*)").eq("turma_id", turma_id).execute()
            alunos_lista = [{"id": x["aluno_id"], **x.get("profiles", {})} for x in (r.data or [])]
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("professor/alunos.html",
                           alunos=alunos_lista, turmas=turmas,
                           turma_id=turma_id, user=session["user"])


# ─── PRESENÇA ────────────────────────────────────────────────────────────────

@professor_bp.route("/presenca", methods=["GET", "POST"])
@professor_required
def presenca():
    sb = get_supabase_admin()
    turma_id = get_turma_ativa()
    data_sel = request.args.get("data", str(date.today()))

    if request.method == "POST":
        data_aula = request.form.get("data_aula", str(date.today()))
        aluno_ids = request.form.getlist("alunos")
        presentes = set(request.form.getlist("presentes"))
        justificados = set(request.form.getlist("justificados"))
        try:
            # Remover registros anteriores desse dia
            sb.table("presencas").delete().eq("turma_id", turma_id).eq("data", data_aula).execute()
            registros = []
            for aid in aluno_ids:
                if aid in presentes:
                    status = "presente"
                elif aid in justificados:
                    status = "justificada"
                else:
                    status = "falta"
                registros.append({"aluno_id": aid, "turma_id": turma_id, "data": data_aula, "status": status})
            if registros:
                sb.table("presencas").insert(registros).execute()
            flash("Presença registrada!", "success")
        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("professor.presenca", data=data_aula))

    alunos_lista = []
    presencas_dia = {}
    historico = []
    try:
        r = sb.table("turma_alunos").select("aluno_id, profiles(*)").eq("turma_id", turma_id).execute()
        alunos_lista = [{"id": x["aluno_id"], **x.get("profiles", {})} for x in (r.data or [])]

        p = sb.table("presencas").select("*").eq("turma_id", turma_id).eq("data", data_sel).execute()
        presencas_dia = {x["aluno_id"]: x["status"] for x in (p.data or [])}

        h = sb.table("presencas").select("*").eq("turma_id", turma_id).order("data", desc=True).limit(50).execute()
        historico = h.data or []
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("professor/presenca.html",
                           alunos=alunos_lista, presencas_dia=presencas_dia,
                           historico=historico, data_sel=data_sel,
                           turma_id=turma_id, user=session["user"])


# ─── MATERIAIS ───────────────────────────────────────────────────────────────

@professor_bp.route("/materiais", methods=["GET", "POST"])
@professor_required
def materiais():
    sb = get_supabase_admin()
    turma_id = get_turma_ativa()

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "upload":
                titulo = request.form["titulo"]
                descricao = request.form.get("descricao", "")
                visivel = "visivel" in request.form
                arquivo = request.files.get("arquivo")
                arquivo_url = ""

                if arquivo and arquivo.filename:
                    # Upload para Supabase Storage
                    file_bytes = arquivo.read()
                    file_name = f"{turma_id}/{arquivo.filename}"
                    sb.storage.from_("materiais").upload(file_name, file_bytes,
                        {"content-type": arquivo.content_type or "application/pdf"})
                    pub = sb.storage.from_("materiais").get_public_url(file_name)
                    arquivo_url = pub

                sb.table("materiais").insert({
                    "titulo": titulo, "descricao": descricao,
                    "arquivo_url": arquivo_url, "turma_id": turma_id,
                    "visivel": visivel
                }).execute()
                flash("Material enviado!", "success")

            elif action == "toggle":
                mid = request.form["material_id"]
                visivel = request.form.get("visivel") == "true"
                sb.table("materiais").update({"visivel": visivel}).eq("id", mid).execute()

            elif action == "deletar":
                mid = request.form["material_id"]
                sb.table("materiais").delete().eq("id", mid).execute()
                flash("Material removido.", "success")

        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("professor.materiais"))

    lista = []
    try:
        r = sb.table("materiais").select("*").eq("turma_id", turma_id).order("created_at", desc=True).execute()
        lista = r.data or []
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("professor/materiais.html",
                           materiais=lista, turma_id=turma_id, user=session["user"])


# ─── PROVAS ──────────────────────────────────────────────────────────────────

@professor_bp.route("/provas", methods=["GET", "POST"])
@professor_required
def provas():
    sb = get_supabase_admin()
    turma_id = get_turma_ativa()

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "criar":
                import json
                titulo = request.form["titulo"]
                descricao = request.form.get("descricao", "")
                peso = float(request.form.get("peso", 10))
                data_prova = request.form.get("data_prova", "")
                visivel = "visivel" in request.form

                # Montar questões
                questoes = []
                i = 1
                while f"questao_{i}" in request.form:
                    q = {
                        "enunciado": request.form[f"questao_{i}"],
                        "tipo": request.form.get(f"tipo_{i}", "dissertativa"),
                        "valor": float(request.form.get(f"valor_{i}", 1)),
                        "opcoes": []
                    }
                    if q["tipo"] == "multipla":
                        opcoes = []
                        j = 1
                        while request.form.get(f"opcao_{i}_{j}"):
                            opcoes.append(request.form[f"opcao_{i}_{j}"])
                            j += 1
                        q["opcoes"] = opcoes
                        q["correta"] = request.form.get(f"correta_{i}", "0")
                    questoes.append(q)
                    i += 1

                sb.table("provas").insert({
                    "titulo": titulo, "descricao": descricao,
                    "turma_id": turma_id, "peso": peso,
                    "data": data_prova or None, "visivel": visivel,
                    "questoes_json": json.dumps(questoes, ensure_ascii=False)
                }).execute()
                flash("Prova criada!", "success")

            elif action == "toggle":
                pid = request.form["prova_id"]
                visivel = request.form.get("visivel") == "true"
                sb.table("provas").update({"visivel": visivel}).eq("id", pid).execute()

            elif action == "deletar":
                pid = request.form["prova_id"]
                sb.table("provas").delete().eq("id", pid).execute()
                flash("Prova removida.", "success")

        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("professor.provas"))

    lista = []
    try:
        r = sb.table("provas").select("*").eq("turma_id", turma_id).order("created_at", desc=True).execute()
        lista = r.data or []
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("professor/provas.html",
                           provas=lista, turma_id=turma_id, user=session["user"])


@professor_bp.route("/provas/<prova_id>/corrigir", methods=["GET", "POST"])
@professor_required
def corrigir_prova(prova_id):
    sb = get_supabase_admin()

    if request.method == "POST":
        try:
            resposta_id = request.form["resposta_id"]
            nota = float(request.form["nota"])
            feedback = request.form.get("feedback", "")
            sb.table("respostas_prova").update({
                "nota": nota, "feedback": feedback, "corrigida": True
            }).eq("id", resposta_id).execute()
            flash("Resposta corrigida!", "success")
        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("professor.corrigir_prova", prova_id=prova_id))

    prova = {}
    respostas = []
    try:
        import json
        p = sb.table("provas").select("*").eq("id", prova_id).single().execute()
        prova = p.data or {}
        if prova.get("questoes_json"):
            prova["questoes"] = json.loads(prova["questoes_json"])

        r = sb.table("respostas_prova").select("*, profiles(nome)").eq("prova_id", prova_id).execute()
        respostas = r.data or []
        for resp in respostas:
            if resp.get("respostas_json"):
                resp["respostas"] = json.loads(resp["respostas_json"])
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("professor/corrigir_prova.html",
                           prova=prova, respostas=respostas, user=session["user"])


# ─── TRABALHOS ───────────────────────────────────────────────────────────────

@professor_bp.route("/trabalhos", methods=["GET", "POST"])
@professor_required
def trabalhos():
    sb = get_supabase_admin()
    turma_id = get_turma_ativa()

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "criar":
                sb.table("trabalhos").insert({
                    "titulo": request.form["titulo"],
                    "descricao": request.form.get("descricao", ""),
                    "turma_id": turma_id,
                    "prazo": request.form.get("prazo") or None,
                    "peso": float(request.form.get("peso", 10)),
                    "visivel": "visivel" in request.form
                }).execute()
                flash("Trabalho criado!", "success")

            elif action == "avaliar":
                entrega_id = request.form["entrega_id"]
                nota = float(request.form["nota"])
                feedback = request.form.get("feedback", "")
                sb.table("entregas_trabalho").update({
                    "nota": nota, "feedback": feedback
                }).eq("id", entrega_id).execute()
                flash("Trabalho avaliado!", "success")

            elif action == "toggle":
                tid = request.form["trabalho_id"]
                visivel = request.form.get("visivel") == "true"
                sb.table("trabalhos").update({"visivel": visivel}).eq("id", tid).execute()

            elif action == "deletar":
                tid = request.form["trabalho_id"]
                sb.table("trabalhos").delete().eq("id", tid).execute()
                flash("Trabalho removido.", "success")

        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("professor.trabalhos"))

    lista = []
    entregas = {}
    try:
        r = sb.table("trabalhos").select("*").eq("turma_id", turma_id).order("created_at", desc=True).execute()
        lista = r.data or []
        for trab in lista:
            e = sb.table("entregas_trabalho").select("*, profiles(nome)").eq("trabalho_id", trab["id"]).execute()
            entregas[trab["id"]] = e.data or []
    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("professor/trabalhos.html",
                           trabalhos=lista, entregas=entregas,
                           turma_id=turma_id, user=session["user"])


# ─── NOTAS ───────────────────────────────────────────────────────────────────

@professor_bp.route("/notas")
@professor_required
def notas():
    sb = get_supabase_admin()
    turma_id = get_turma_ativa()
    alunos_notas = []
    provas_lista = []
    trabalhos_lista = []

    try:
        import json
        alunos_r = sb.table("turma_alunos").select("aluno_id, profiles(*)").eq("turma_id", turma_id).execute()
        alunos = [{"id": x["aluno_id"], **x.get("profiles", {})} for x in (alunos_r.data or [])]

        prov_r = sb.table("provas").select("id, titulo, peso").eq("turma_id", turma_id).execute()
        provas_lista = prov_r.data or []

        trab_r = sb.table("trabalhos").select("id, titulo, peso").eq("turma_id", turma_id).execute()
        trabalhos_lista = trab_r.data or []

        for aluno in alunos:
            notas_prova = {}
            for prova in provas_lista:
                resp = sb.table("respostas_prova").select("nota").eq("aluno_id", aluno["id"]).eq("prova_id", prova["id"]).maybe_single().execute()
                notas_prova[prova["id"]] = resp.data.get("nota") if resp.data else None

            notas_trab = {}
            for trab in trabalhos_lista:
                ent = sb.table("entregas_trabalho").select("nota").eq("aluno_id", aluno["id"]).eq("trabalho_id", trab["id"]).maybe_single().execute()
                notas_trab[trab["id"]] = ent.data.get("nota") if ent.data else None

            # Calcular média ponderada
            total_peso = 0
            total_valor = 0
            for prova in provas_lista:
                n = notas_prova.get(prova["id"])
                if n is not None:
                    total_valor += n * prova.get("peso", 1)
                    total_peso += prova.get("peso", 1)
            for trab in trabalhos_lista:
                n = notas_trab.get(trab["id"])
                if n is not None:
                    total_valor += n * trab.get("peso", 1)
                    total_peso += trab.get("peso", 1)

            media = round(total_valor / total_peso, 1) if total_peso > 0 else None
            alunos_notas.append({**aluno, "notas_prova": notas_prova, "notas_trab": notas_trab, "media": media})

        alunos_notas.sort(key=lambda x: (x["media"] is None, -(x["media"] or 0)))

    except Exception as e:
        flash(f"Erro: {e}", "error")

    return render_template("professor/notas.html",
                           alunos_notas=alunos_notas, provas=provas_lista,
                           trabalhos=trabalhos_lista, turma_id=turma_id, user=session["user"])
