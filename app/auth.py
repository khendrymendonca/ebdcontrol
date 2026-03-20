from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.supabase_client import get_supabase

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if "user" in session:
        user = session["user"]
        if user.get("tipo") == "professor":
            return redirect(url_for("professor.dashboard"))
        return redirect(url_for("aluno.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()

        try:
            sb = get_supabase()
            result = sb.auth.sign_in_with_password({"email": email, "password": senha})

            if result.user:
                user_id = result.user.id
                # Buscar perfil completo
                profile = sb.table("profiles").select("*").eq("id", user_id).single().execute()
                if profile.data:
                    session["user"] = {
                        "id": user_id,
                        "nome": profile.data.get("nome", ""),
                        "email": email,
                        "tipo": profile.data.get("tipo", "aluno"),
                        "avatar_url": profile.data.get("avatar_url", ""),
                        "access_token": result.session.access_token,
                    }
                    session["turma_id"] = profile.data.get("turma_id")

                    if profile.data.get("tipo") == "professor":
                        return redirect(url_for("professor.dashboard"))
                    return redirect(url_for("aluno.dashboard"))
                else:
                    flash("Perfil não encontrado. Contate o administrador.", "error")
            else:
                flash("Email ou senha incorretos.", "error")
        except Exception as e:
            msg = str(e)
            if "Invalid login credentials" in msg:
                flash("Email ou senha incorretos.", "error")
            else:
                flash(f"Erro ao fazer login: {msg}", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    session.clear()
    return redirect(url_for("auth.login"))
