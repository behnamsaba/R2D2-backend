from typing import Any, Dict, List

from .quality import build_quality_guardrails
from .text_utils import (
    build_fallback_follow_up_emails,
    build_hashtags_from_content,
    extract_hashtags,
    extract_question_sentence,
    extract_tagged_block,
    infer_call_to_action,
    normalize_list_from_text,
    pick_sentences_by_keywords,
    split_sentences,
)


def build_market_structured(
    company: str, competitors_text: str, analysis_text: str
) -> Dict[str, Any]:
    summary_sentences = split_sentences(analysis_text)
    opportunities = pick_sentences_by_keywords(
        analysis_text,
        ("opportunit", "growth", "potential", "expand", "advantage"),
    )
    risks = pick_sentences_by_keywords(
        analysis_text,
        ("risk", "challenge", "weakness", "threat", "constraint"),
    )
    actions = pick_sentences_by_keywords(
        analysis_text,
        ("recommend", "should", "consider", "focus", "prioritize", "action"),
    )

    return {
        "company": company,
        "competitorList": normalize_list_from_text(competitors_text, max_items=8),
        "summary": " ".join(summary_sentences[:2]) if summary_sentences else analysis_text,
        "opportunities": opportunities or ["Identify the strongest product differentiator."],
        "risks": risks or ["Monitor competitor positioning and pricing shifts."],
        "recommendedActions": actions
        or ["Prioritize the segment with the clearest value proposition."],
        "quality": build_quality_guardrails(analysis_text),
    }


def build_personalize_structured(
    original_email: str, rewritten_email: str
) -> Dict[str, Any]:
    original_topic = split_sentences(original_email)
    fallback_subject_source = original_topic[0] if original_topic else "your proposal"
    fallback_subject = f"Follow-up regarding {fallback_subject_source[:60]}"

    return {
        "rewrittenBody": rewritten_email,
        "subjectSuggestion": fallback_subject,
        "callToAction": infer_call_to_action(
            rewritten_email,
            "Would you be open to a short call this week?",
        ),
        "keyPoints": normalize_list_from_text(rewritten_email, max_items=4),
        "quality": build_quality_guardrails(rewritten_email),
    }


def build_crm_structured(
    output: str, values: Dict[str, str], mode: str
) -> Dict[str, Any]:
    base_payload: Dict[str, Any] = {
        "message": output,
        "nextStepQuestion": extract_question_sentence(
            output, "Would you like me to send over a short summary?"
        ),
        "keyPoints": normalize_list_from_text(output, max_items=4),
    }

    if mode == "welcome":
        base_payload.update(
            {
                "customerName": values.get("customerName", ""),
                "productName": values.get("productName", ""),
                "goal": "Build trust and introduce value clearly.",
            }
        )
    else:
        base_payload.update(
            {
                "prospectName": values.get("prospectName", ""),
                "followUpReason": values.get("followUpReason", ""),
                "goal": "Re-engage the prospect with a clear next step.",
            }
        )

    base_payload["quality"] = build_quality_guardrails(output)
    return base_payload


def build_marketing_structured(
    output: str, values: Dict[str, str], mode: str
) -> Dict[str, Any]:
    hashtags = extract_hashtags(output)
    if not hashtags:
        hashtags = build_hashtags_from_content(values.get("postContent", ""), max_items=5)

    payload: Dict[str, Any] = {
        "copy": output,
        "hashtags": hashtags,
        "callToAction": infer_call_to_action(
            output, "Follow for more updates and product insights."
        ),
        "keyPoints": normalize_list_from_text(output, max_items=4),
    }

    if mode == "post":
        payload.update(
            {
                "platform": values.get("platform", ""),
                "objective": values.get("postObjective", ""),
            }
        )
    else:
        payload.update(
            {
                "tone": values.get("postTone", ""),
            }
        )

    payload["quality"] = build_quality_guardrails(output)
    return payload


def build_sales_call_pipeline_structured(transcript_notes: str, output: str) -> Dict[str, Any]:
    summary = extract_tagged_block(output, "SUMMARY")
    objections = normalize_list_from_text(
        extract_tagged_block(output, "OBJECTIONS"), max_items=6
    )
    next_actions = normalize_list_from_text(
        extract_tagged_block(output, "NEXT_ACTIONS"), max_items=6
    )

    follow_up_emails: List[str] = []
    for index in range(1, 4):
        candidate = extract_tagged_block(output, f"FOLLOW_UP_EMAIL_{index}")
        if candidate:
            follow_up_emails.append(candidate)

    if not summary:
        summary_sentences = split_sentences(output)
        summary = " ".join(summary_sentences[:2]) if summary_sentences else transcript_notes

    if not objections:
        objections = pick_sentences_by_keywords(
            output,
            ("objection", "concern", "hesitat", "budget", "timeline", "risk"),
            max_items=4,
        )

    if not next_actions:
        next_actions = pick_sentences_by_keywords(
            output,
            ("next", "follow", "schedule", "send", "book", "share"),
            max_items=4,
        )

    if len(follow_up_emails) < 3:
        fallback_variants = build_fallback_follow_up_emails(summary, next_actions)
        follow_up_emails.extend(fallback_variants[len(follow_up_emails) : 3])

    quality_source = " ".join([summary, *objections, *next_actions, *follow_up_emails])
    return {
        "summary": summary,
        "objections": objections,
        "nextActions": next_actions,
        "followUpEmails": follow_up_emails[:3],
        "quality": build_quality_guardrails(quality_source),
    }


def normalize_market_history_item(entry: Dict[str, Any]) -> Dict[str, Any]:
    output_payload = entry.get("output", {})
    input_payload = entry.get("input", {})
    company = output_payload.get("id") or input_payload.get("prompt", "")
    competitors = output_payload.get("competitors", "")
    analysis = output_payload.get("analysis") or output_payload.get("analyze", "")
    structured = output_payload.get("structured")
    if not isinstance(structured, dict):
        structured = build_market_structured(str(company), str(competitors), str(analysis))

    return {
        "id": str(company),
        "competitors": str(competitors),
        "analysis": str(analysis),
        "analyze": str(analysis),
        "structured": structured,
        "createdAt": entry.get("createdAt"),
    }
