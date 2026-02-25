import re
from typing import Any, Dict, Optional, Tuple

from flask import current_app, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from storage import get_user_by_id

from .http_utils import error_response


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 12
SPECIAL_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9]")
AUTH_TOKEN_SALT = "r2d2-auth"


def sanitize_email(email: str) -> str:
    return email.strip().lower()


def sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "createdAt": user.get("createdAt"),
    }


def validate_password_policy(password: str) -> Optional[str]:
    policy_errors = []

    if len(password) < PASSWORD_MIN_LENGTH:
        policy_errors.append(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
        )
    if not re.search(r"[A-Z]", password):
        policy_errors.append("Password must include at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        policy_errors.append("Password must include at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        policy_errors.append("Password must include at least one number.")
    if not SPECIAL_CHAR_PATTERN.search(password):
        policy_errors.append("Password must include at least one special character.")

    if policy_errors:
        return " ".join(policy_errors)
    return None


def create_token_serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt=AUTH_TOKEN_SALT)


def _get_token_serializer() -> URLSafeTimedSerializer:
    serializer = current_app.extensions.get("auth_serializer")
    if not isinstance(serializer, URLSafeTimedSerializer):
        raise RuntimeError("Authentication serializer is not configured.")
    return serializer


def create_auth_token(user_id: int) -> str:
    return _get_token_serializer().dumps({"user_id": user_id})


def parse_bearer_token() -> Optional[str]:
    authorization_header = request.headers.get("Authorization", "")
    if not authorization_header.startswith("Bearer "):
        return None
    return authorization_header.split(" ", 1)[1].strip() or None


def get_authenticated_user() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    token = parse_bearer_token()
    if not token:
        return None, error_response("Authentication required.", 401)

    try:
        payload = _get_token_serializer().loads(
            token,
            max_age=int(current_app.config.get("AUTH_TOKEN_MAX_AGE_SECONDS", 60 * 60 * 24 * 7)),
        )
    except SignatureExpired:
        return None, error_response("Authentication token has expired.", 401)
    except BadSignature:
        return None, error_response("Invalid authentication token.", 401)

    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        return None, error_response("Invalid authentication token payload.", 401)

    user = get_user_by_id(user_id)
    if user is None:
        return None, error_response("User no longer exists.", 401)

    return user, None
