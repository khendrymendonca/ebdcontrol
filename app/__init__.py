import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "logos-dev-secret-2024")

    from app.auth import auth_bp
    from app.professor import professor_bp
    from app.aluno import aluno_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(professor_bp, url_prefix="/professor")
    app.register_blueprint(aluno_bp, url_prefix="/aluno")

    # Injeta variáveis do Supabase em todos os templates (necessário para realtime.js)
    @app.context_processor
    def inject_supabase_config():
        return {
            "SUPABASE_URL": os.environ.get("SUPABASE_URL", ""),
            "SUPABASE_ANON_KEY": os.environ.get("SUPABASE_ANON_KEY", ""),
        }

    return app
