from typing import Any, Dict, Iterable, Optional, Tuple

from flask import jsonify, request


def error_response(message: str, status_code: int):
    return jsonify({"error": message}), status_code


def parse_json_payload() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return None, error_response("Request body must be valid JSON.", 400)
    return payload, None


def require_non_empty_strings(
    payload: Dict[str, Any], fields: Iterable[str]
) -> Tuple[Optional[Dict[str, str]], Optional[Tuple[Any, int]]]:
    normalized: Dict[str, str] = {}
    for field in fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            return None, error_response(
                f"Field '{field}' is required and must be a non-empty string.", 400
            )
        normalized[field] = value.strip()
    return normalized, None


def parse_limit(
    limit_value: Optional[str], default: int = 20
) -> Tuple[Optional[int], Optional[Tuple[Any, int]]]:
    if limit_value is None or str(limit_value).strip() == "":
        return default, None

    try:
        parsed_limit = int(limit_value)
    except ValueError:
        return None, error_response("Query param 'limit' must be an integer.", 400)

    if parsed_limit < 1 or parsed_limit > 100:
        return None, error_response("Query param 'limit' must be between 1 and 100.", 400)

    return parsed_limit, None
