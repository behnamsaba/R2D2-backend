from typing import Optional

from flask import Flask
from flask_cors import CORS

from storage import init_db

from .api import api_bp
from .auth_service import create_token_serializer
from .settings import Settings, load_settings


def create_app(settings: Optional[Settings] = None) -> Flask:
    resolved_settings = settings or load_settings()

    app = Flask(__name__)
    app.config.update(
        OPENAI_API_KEY=resolved_settings.openai_api_key,
        APP_ENV=resolved_settings.app_env,
        AUTH_TOKEN_MAX_AGE_SECONDS=resolved_settings.auth_token_max_age_seconds,
        HOST=resolved_settings.host,
        PORT=resolved_settings.port,
        DEBUG=resolved_settings.debug,
    )
    app.extensions["auth_serializer"] = create_token_serializer(
        resolved_settings.auth_secret_key
    )

    if resolved_settings.cors_origins is None:
        CORS(app)
    else:
        CORS(app, resources={r"/api/*": {"origins": resolved_settings.cors_origins}})

    init_db()
    app.register_blueprint(api_bp)
    return app
