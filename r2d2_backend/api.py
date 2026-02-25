import logging
import sqlite3
from typing import Any, Dict, Optional

from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from storage import create_user, get_user_by_email, list_generations, save_generation

from .auth_service import (
    EMAIL_PATTERN,
    create_auth_token,
    get_authenticated_user,
    sanitize_email,
    sanitize_user,
    validate_password_policy,
)
from .export_utils import build_export_file, validate_sales_pipeline_export_payload
from .http_utils import error_response, parse_json_payload, parse_limit, require_non_empty_strings
from .llm_service import (
    caption_template,
    competitors_template,
    create_post_template,
    followup_template,
    personalize_template,
    products_template,
    run_chain,
    sales_call_pipeline_template,
    welcome_template,
)
from .structured_output import (
    build_crm_structured,
    build_market_structured,
    build_marketing_structured,
    build_personalize_structured,
    build_sales_call_pipeline_structured,
    normalize_market_history_item,
)


logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


def _get_openai_api_key() -> Optional[str]:
    api_key = current_app.config.get("OPENAI_API_KEY")
    if isinstance(api_key, str) and api_key.strip():
        return api_key.strip()
    return None


def persist_generation_for_user(
    feature: str,
    input_payload: Dict[str, Any],
    output_payload: Dict[str, Any],
    user_id: Optional[int],
) -> None:
    try:
        save_generation(feature, input_payload, output_payload, user_id=user_id)
    except Exception:
        logger.exception("Failed to persist generation for feature '%s'.", feature)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.post("/auth/register")
def register():
    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    values, validation_error = require_non_empty_strings(payload, ("email", "password"))
    if validation_error:
        return validation_error

    email = sanitize_email(values["email"])
    password = values["password"]

    if not EMAIL_PATTERN.match(email):
        return error_response("Field 'email' must be a valid email address.", 400)

    password_policy_error = validate_password_policy(password)
    if password_policy_error:
        return error_response(password_policy_error, 400)

    existing_user = get_user_by_email(email)
    if existing_user is not None:
        return error_response("User already exists.", 409)

    try:
        user = create_user(email=email, password_hash=generate_password_hash(password))
    except sqlite3.IntegrityError:
        return error_response("User already exists.", 409)
    except Exception:
        logger.exception("Failed to create user.")
        return error_response("Failed to create user.", 500)

    token = create_auth_token(int(user["id"]))
    return jsonify({"token": token, "user": sanitize_user(user)})


@api_bp.post("/auth/login")
def login():
    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    values, validation_error = require_non_empty_strings(payload, ("email", "password"))
    if validation_error:
        return validation_error

    email = sanitize_email(values["email"])
    password = values["password"]

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["passwordHash"], password):
        return error_response("Invalid email or password.", 401)

    token = create_auth_token(int(user["id"]))
    return jsonify({"token": token, "user": sanitize_user(user)})


@api_bp.get("/auth/me")
def auth_me():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error
    return jsonify({"user": sanitize_user(user)})


@api_bp.get("/history")
def history():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    feature = request.args.get("feature")
    limit, parse_error = parse_limit(request.args.get("limit"))
    if parse_error:
        return parse_error

    try:
        history_rows = list_generations(
            feature=feature,
            limit=limit or 20,
            user_id=int(user["id"]),
        )
    except Exception:
        logger.exception("Failed to read history.")
        return error_response("Failed to read history.", 500)

    return jsonify({"data": history_rows})


@api_bp.get("/market-research/history")
def market_research_history():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    limit, parse_error = parse_limit(request.args.get("limit"))
    if parse_error:
        return parse_error

    try:
        history_rows = list_generations(
            feature="market_research",
            limit=limit or 20,
            user_id=int(user["id"]),
        )
    except Exception:
        logger.exception("Failed to read market research history.")
        return error_response("Failed to read market research history.", 500)

    normalized = [normalize_market_history_item(item) for item in history_rows]
    return jsonify({"data": normalized})


@api_bp.post("/market-research")
def market_research():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    values, validation_error = require_non_empty_strings(payload, ("prompt",))
    if validation_error:
        return validation_error

    company = values["prompt"]

    try:
        openai_api_key = _get_openai_api_key()
        competitors = run_chain(competitors_template, {"company": company}, openai_api_key)
        analysis = run_chain(products_template, {"company": company}, openai_api_key)
    except RuntimeError as exc:
        logger.warning("Configuration error in market_research: %s", exc)
        return error_response(str(exc), 503)
    except Exception:
        logger.exception("Unexpected error while generating market research.")
        return error_response("Failed to generate market research.", 500)

    structured = build_market_structured(company, competitors, analysis)
    response_payload = {
        "id": company,
        "competitors": competitors,
        "analysis": analysis,
        "analyze": analysis,
        "structured": structured,
    }
    persist_generation_for_user(
        "market_research",
        {"prompt": company},
        response_payload,
        user_id=int(user["id"]),
    )
    return jsonify(response_payload)


@api_bp.post("/personalize-email")
def personalize_email():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    values, validation_error = require_non_empty_strings(payload, ("prompt",))
    if validation_error:
        return validation_error

    try:
        rewritten_email = run_chain(personalize_template, {"email": values["prompt"]}, _get_openai_api_key())
    except RuntimeError as exc:
        logger.warning("Configuration error in personalize_email: %s", exc)
        return error_response(str(exc), 503)
    except Exception:
        logger.exception("Unexpected error while personalizing email.")
        return error_response("Failed to personalize email.", 500)

    response_payload = {
        "data": rewritten_email,
        "structured": build_personalize_structured(values["prompt"], rewritten_email),
    }
    persist_generation_for_user(
        "personalize_email",
        values,
        response_payload,
        user_id=int(user["id"]),
    )
    return jsonify(response_payload)


@api_bp.post("/crm")
def crm_api():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    has_welcome_shape = "customerName" in payload or "productName" in payload
    has_followup_shape = (
        "prospectName" in payload or "followUpReason" in payload or "note" in payload
    )

    if has_welcome_shape and has_followup_shape:
        return error_response("Request cannot mix welcome and follow-up fields.", 400)

    if has_welcome_shape:
        values, validation_error = require_non_empty_strings(
            payload, ("customerName", "productName")
        )
        if validation_error:
            return validation_error
        template = welcome_template
    elif has_followup_shape:
        values, validation_error = require_non_empty_strings(
            payload, ("prospectName", "followUpReason", "note")
        )
        if validation_error:
            return validation_error
        template = followup_template
    else:
        return error_response(
            (
                "Request must include either customerName/productName "
                "or prospectName/followUpReason/note."
            ),
            400,
        )

    try:
        output = run_chain(template, values, _get_openai_api_key())
    except RuntimeError as exc:
        logger.warning("Configuration error in crm_api: %s", exc)
        return error_response(str(exc), 503)
    except Exception:
        logger.exception("Unexpected error while generating CRM content.")
        return error_response("Failed to generate CRM content.", 500)

    feature_name = "crm_welcome" if has_welcome_shape else "crm_follow_up"
    response_payload = {
        "data": output,
        "structured": build_crm_structured(
            output,
            values,
            mode="welcome" if has_welcome_shape else "follow_up",
        ),
    }
    persist_generation_for_user(
        feature_name,
        values,
        response_payload,
        user_id=int(user["id"]),
    )
    return jsonify(response_payload)


@api_bp.post("/marketing")
def marketing_api():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    if "platform" in payload or "postObjective" in payload:
        values, validation_error = require_non_empty_strings(
            payload, ("platform", "postObjective", "postContent")
        )
        if validation_error:
            return validation_error
        template = create_post_template
    else:
        values, validation_error = require_non_empty_strings(
            payload, ("postContent", "postTone")
        )
        if validation_error:
            return validation_error
        template = caption_template

    try:
        output = run_chain(template, values, _get_openai_api_key())
    except RuntimeError as exc:
        logger.warning("Configuration error in marketing_api: %s", exc)
        return error_response(str(exc), 503)
    except Exception:
        logger.exception("Unexpected error while generating marketing content.")
        return error_response("Failed to generate marketing content.", 500)

    feature_name = (
        "marketing_post"
        if "platform" in payload or "postObjective" in payload
        else "marketing_caption"
    )
    response_payload = {
        "data": output,
        "structured": build_marketing_structured(
            output,
            values,
            mode="post" if feature_name == "marketing_post" else "caption",
        ),
    }
    persist_generation_for_user(
        feature_name,
        values,
        response_payload,
        user_id=int(user["id"]),
    )
    return jsonify(response_payload)


@api_bp.post("/sales-call-pipeline")
def sales_call_pipeline():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    values, validation_error = require_non_empty_strings(payload, ("transcriptNotes",))
    if validation_error:
        return validation_error

    try:
        output = run_chain(
            sales_call_pipeline_template,
            {"transcriptNotes": values["transcriptNotes"]},
            _get_openai_api_key(),
        )
    except RuntimeError as exc:
        logger.warning("Configuration error in sales_call_pipeline: %s", exc)
        return error_response(str(exc), 503)
    except Exception:
        logger.exception("Unexpected error while generating sales call pipeline.")
        return error_response("Failed to generate sales call pipeline.", 500)

    structured = build_sales_call_pipeline_structured(values["transcriptNotes"], output)
    response_payload = {
        "data": output,
        "structured": structured,
    }
    persist_generation_for_user(
        "sales_call_pipeline",
        values,
        response_payload,
        user_id=int(user["id"]),
    )
    return jsonify(response_payload)


@api_bp.post("/sales-call-pipeline/export")
def sales_call_pipeline_export():
    user, auth_error = get_authenticated_user()
    if auth_error:
        return auth_error

    payload, parse_error = parse_json_payload()
    if parse_error:
        return parse_error

    values, validation_error = require_non_empty_strings(payload, ("format",))
    if validation_error:
        return validation_error

    pipeline = payload.get("pipeline")
    if not isinstance(pipeline, dict):
        return error_response("Field 'pipeline' is required and must be an object.", 400)

    export_format = values["format"].lower()
    if export_format not in {"json", "csv", "markdown", "pdf"}:
        return error_response(
            "Field 'format' must be one of: json, csv, markdown, pdf.", 400
        )

    normalized_pipeline, pipeline_error = validate_sales_pipeline_export_payload(pipeline)
    if pipeline_error:
        return pipeline_error

    file_bytes, mime_type, extension = build_export_file(export_format, normalized_pipeline)
    filename = f"sales-call-pipeline.{extension}"

    persist_generation_for_user(
        "sales_call_pipeline_export",
        {"format": export_format},
        {"filename": filename, "pipeline": normalized_pipeline},
        user_id=int(user["id"]),
    )
    return Response(
        file_bytes,
        mimetype=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
