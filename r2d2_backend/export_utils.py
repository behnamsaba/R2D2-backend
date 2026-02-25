import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple

from .http_utils import error_response


def validate_string_list(
    source: Dict[str, Any], field: str, max_items: int = 50
) -> Tuple[Optional[List[str]], Optional[Tuple[Any, int]]]:
    raw_value = source.get(field)
    if not isinstance(raw_value, list):
        return None, error_response(f"Field '{field}' must be an array of strings.", 400)

    cleaned_values: List[str] = []
    for item in raw_value:
        if not isinstance(item, str) or not item.strip():
            return None, error_response(
                f"Field '{field}' must contain only non-empty strings.", 400
            )
        cleaned_values.append(item.strip())
        if len(cleaned_values) >= max_items:
            break

    return cleaned_values, None


def validate_sales_pipeline_export_payload(
    raw_pipeline: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    summary = raw_pipeline.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None, error_response("Field 'pipeline.summary' must be a non-empty string.", 400)

    objections, objections_error = validate_string_list(raw_pipeline, "objections", max_items=10)
    if objections_error:
        return None, objections_error

    next_actions, next_actions_error = validate_string_list(
        raw_pipeline, "nextActions", max_items=10
    )
    if next_actions_error:
        return None, next_actions_error

    follow_up_emails, follow_up_emails_error = validate_string_list(
        raw_pipeline, "followUpEmails", max_items=3
    )
    if follow_up_emails_error:
        return None, follow_up_emails_error

    quality = raw_pipeline.get("quality", {})
    if not isinstance(quality, dict):
        return None, error_response("Field 'pipeline.quality' must be an object.", 400)

    spam_risk_words = quality.get("spamRiskWording", [])
    if not isinstance(spam_risk_words, list):
        return None, error_response(
            "Field 'pipeline.quality.spamRiskWording' must be an array.", 400
        )
    if any(not isinstance(item, str) for item in spam_risk_words):
        return None, error_response(
            "Field 'pipeline.quality.spamRiskWording' must contain strings.", 400
        )

    sensitive_warnings = quality.get("sensitiveDataWarnings", [])
    if not isinstance(sensitive_warnings, list):
        return None, error_response(
            "Field 'pipeline.quality.sensitiveDataWarnings' must be an array.", 400
        )
    if any(not isinstance(item, str) for item in sensitive_warnings):
        return None, error_response(
            "Field 'pipeline.quality.sensitiveDataWarnings' must contain strings.",
            400,
        )

    normalized_quality = {
        "clarityScore": quality.get("clarityScore"),
        "ctaPresent": bool(quality.get("ctaPresent", False)),
        "spamRiskWording": spam_risk_words,
        "sensitiveDataWarnings": sensitive_warnings,
    }

    return (
        {
            "summary": summary.strip(),
            "objections": objections,
            "nextActions": next_actions,
            "followUpEmails": follow_up_emails,
            "quality": normalized_quality,
        },
        None,
    )


def build_sales_pipeline_csv(pipeline: Dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "value"])
    writer.writerow(["summary", pipeline.get("summary", "")])

    for item in pipeline.get("objections", []):
        writer.writerow(["objection", item])
    for item in pipeline.get("nextActions", []):
        writer.writerow(["next_action", item])
    for index, item in enumerate(pipeline.get("followUpEmails", []), start=1):
        writer.writerow([f"follow_up_email_{index}", item])

    quality = pipeline.get("quality", {})
    if isinstance(quality, dict):
        for key in ("clarityScore", "ctaPresent"):
            if key in quality:
                writer.writerow([f"quality.{key}", quality.get(key)])

        spam_terms = quality.get("spamRiskWording", [])
        if isinstance(spam_terms, list):
            for term in spam_terms:
                writer.writerow(["quality.spamRiskWording", term])

        warnings = quality.get("sensitiveDataWarnings", [])
        if isinstance(warnings, list):
            for warning in warnings:
                writer.writerow(["quality.sensitiveDataWarnings", warning])

    return output.getvalue()


def build_sales_pipeline_markdown(pipeline: Dict[str, Any]) -> str:
    lines = [
        "# Sales Call Follow-Up Pipeline",
        "",
        "## Summary",
        pipeline.get("summary", ""),
        "",
        "## Objections",
    ]

    objections = pipeline.get("objections", [])
    if objections:
        lines.extend([f"- {item}" for item in objections])
    else:
        lines.append("- None captured")

    lines.extend(["", "## Next Actions"])
    next_actions = pipeline.get("nextActions", [])
    if next_actions:
        lines.extend([f"- {item}" for item in next_actions])
    else:
        lines.append("- None captured")

    lines.extend(["", "## Follow-Up Email Variants"])
    follow_up_emails = pipeline.get("followUpEmails", [])
    if follow_up_emails:
        for index, email in enumerate(follow_up_emails, start=1):
            lines.append(f"### Variant {index}")
            lines.append(email)
            lines.append("")
    else:
        lines.append("No email variants available.")
        lines.append("")

    quality = pipeline.get("quality", {})
    if isinstance(quality, dict):
        lines.extend(
            [
                "## Quality Guardrails",
                f"- Clarity score: {quality.get('clarityScore', '')}",
                f"- CTA present: {quality.get('ctaPresent', False)}",
            ]
        )

        spam_terms = quality.get("spamRiskWording", [])
        if isinstance(spam_terms, list) and spam_terms:
            lines.append(f"- Spam-risk wording: {', '.join(spam_terms)}")
        else:
            lines.append("- Spam-risk wording: none")

        warnings = quality.get("sensitiveDataWarnings", [])
        if isinstance(warnings, list) and warnings:
            for warning in warnings:
                lines.append(f"- Sensitive-data warning: {warning}")
        else:
            lines.append("- Sensitive-data warning: none")

    return "\n".join(lines).strip() + "\n"


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_text_pdf(lines: List[str]) -> bytes:
    page_line_limit = 45
    pages: List[List[str]] = []
    current_page: List[str] = []

    for line in lines:
        current_page.append(line)
        if len(current_page) >= page_line_limit:
            pages.append(current_page)
            current_page = []

    if current_page:
        pages.append(current_page)

    if not pages:
        pages = [[""]]

    font_object_id = 3 + len(pages) * 2
    objects: Dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
    }

    page_object_ids: List[int] = []
    for index, page_lines in enumerate(pages):
        page_id = 3 + index * 2
        content_id = page_id + 1
        page_object_ids.append(page_id)

        stream_lines = ["BT", "/F1 11 Tf", "50 770 Td", "14 TL"]
        for raw_line in page_lines:
            stream_lines.append(f"({escape_pdf_text(raw_line)}) Tj")
            stream_lines.append("T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1", "replace")

        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects[2] = f"<< /Type /Pages /Count {len(page_object_ids)} /Kids [{kids}] >>".encode(
        "ascii"
    )
    objects[font_object_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    max_object_id = max(objects)
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: Dict[int, int] = {}

    for object_id in range(1, max_object_id + 1):
        if object_id not in objects:
            continue
        offsets[object_id] = len(pdf)
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_id])
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {max_object_id + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for object_id in range(1, max_object_id + 1):
        if object_id in offsets:
            pdf.extend(f"{offsets[object_id]:010} 00000 n \n".encode("ascii"))
        else:
            pdf.extend(b"0000000000 65535 f \n")

    pdf.extend(
        (
            f"trailer\n<< /Size {max_object_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf)


def build_sales_pipeline_pdf(pipeline: Dict[str, Any]) -> bytes:
    lines = [
        "R2D2 Copilot - Sales Call Follow-Up Pipeline",
        "",
        "Summary:",
        pipeline.get("summary", ""),
        "",
        "Objections:",
    ]

    objections = pipeline.get("objections", [])
    if objections:
        for index, item in enumerate(objections, start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("1. None captured")

    lines.append("")
    lines.append("Next Actions:")
    next_actions = pipeline.get("nextActions", [])
    if next_actions:
        for index, item in enumerate(next_actions, start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("1. None captured")

    lines.append("")
    lines.append("Follow-Up Email Variants:")
    follow_up_emails = pipeline.get("followUpEmails", [])
    if follow_up_emails:
        for index, email in enumerate(follow_up_emails, start=1):
            lines.append(f"Variant {index}:")
            lines.extend([segment.strip() for segment in email.splitlines() if segment.strip()])
            lines.append("")
    else:
        lines.append("No email variants available.")
        lines.append("")

    quality = pipeline.get("quality", {})
    if isinstance(quality, dict):
        lines.append("Quality Guardrails:")
        lines.append(f"Clarity score: {quality.get('clarityScore', '')}")
        lines.append(f"CTA present: {quality.get('ctaPresent', False)}")

        spam_terms = quality.get("spamRiskWording", [])
        if isinstance(spam_terms, list) and spam_terms:
            lines.append(f"Spam-risk wording: {', '.join(spam_terms)}")
        else:
            lines.append("Spam-risk wording: none")

        warnings = quality.get("sensitiveDataWarnings", [])
        if isinstance(warnings, list) and warnings:
            for warning in warnings:
                lines.append(f"Sensitive-data warning: {warning}")
        else:
            lines.append("Sensitive-data warning: none")

    return build_simple_text_pdf(lines)


def build_export_file(
    export_format: str, normalized_pipeline: Dict[str, Any]
) -> Tuple[bytes, str, str]:
    if export_format == "json":
        file_bytes = json.dumps(normalized_pipeline, indent=2, ensure_ascii=False).encode("utf-8")
        mime_type = "application/json"
        extension = "json"
    elif export_format == "csv":
        file_bytes = build_sales_pipeline_csv(normalized_pipeline).encode("utf-8")
        mime_type = "text/csv"
        extension = "csv"
    elif export_format == "markdown":
        file_bytes = build_sales_pipeline_markdown(normalized_pipeline).encode("utf-8")
        mime_type = "text/markdown"
        extension = "md"
    else:
        file_bytes = build_sales_pipeline_pdf(normalized_pipeline)
        mime_type = "application/pdf"
        extension = "pdf"

    return file_bytes, mime_type, extension
