import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: Optional[str]
    app_env: str
    auth_secret_key: str
    auth_token_max_age_seconds: int
    cors_origins: Optional[List[str]]
    host: str
    port: int
    debug: bool


def _parse_cors_origins(raw_value: str) -> List[str]:
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def load_settings() -> Settings:
    app_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")).lower()
    raw_auth_secret_key = os.environ.get("APP_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if app_env in {"production", "prod"} and not raw_auth_secret_key:
        raise RuntimeError("APP_SECRET_KEY must be set when APP_ENV is production.")

    auth_secret_key = raw_auth_secret_key or "r2d2-dev-secret-change-in-production"

    raw_cors_origins = os.environ.get("CORS_ORIGINS", "").strip()
    if raw_cors_origins:
        cors_origins = _parse_cors_origins(raw_cors_origins)
    elif app_env in {"production", "prod"}:
        raise RuntimeError("CORS_ORIGINS must be set when APP_ENV is production.")
    else:
        cors_origins = None

    host = os.environ.get("HOST", "127.0.0.1")
    port_value = os.environ.get("PORT", "5000")
    try:
        port = int(port_value)
    except ValueError:
        port = 5000

    debug = os.environ.get("FLASK_DEBUG", "0").strip() == "1" and app_env not in {
        "production",
        "prod",
    }

    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        app_env=app_env,
        auth_secret_key=auth_secret_key,
        auth_token_max_age_seconds=60 * 60 * 24 * 7,
        cors_origins=cors_origins,
        host=host,
        port=port,
        debug=debug,
    )
