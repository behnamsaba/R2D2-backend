import re
from typing import Any, Dict, List

from .text_utils import split_sentences


SPAM_RISK_TERMS = (
    "guaranteed",
    "act now",
    "limited time",
    "risk-free",
    "no obligation",
    "winner",
    "click here",
    "urgent",
)
CTA_PATTERN = re.compile(
    r"\b(reply|schedule|book|call|meeting|connect|share availability|let me know|next step)\b",
    re.IGNORECASE,
)


def build_quality_guardrails(text: str) -> Dict[str, Any]:
    normalized_text = text.strip()
    sentences = split_sentences(normalized_text)
    words = re.findall(r"\b[\w']+\b", normalized_text)
    word_count = len(words)
    sentence_count = len(sentences) if sentences else 1
    average_sentence_words = word_count / sentence_count

    clarity_score = 100
    if word_count < 25:
        clarity_score -= 20
    if average_sentence_words > 24:
        clarity_score -= 20
    elif average_sentence_words > 18:
        clarity_score -= 10
    if word_count > 450:
        clarity_score -= 10
    clarity_score = max(0, min(100, clarity_score))

    lowered = normalized_text.lower()
    spam_hits = [term for term in SPAM_RISK_TERMS if term in lowered]

    sensitive_warnings: List[str] = []
    if re.search(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b", normalized_text):
        sensitive_warnings.append(
            "Contains an email address. Remove personal contact details before sharing."
        )
    if re.search(r"(?:\+?\d[\d\-\s\(\)]{8,}\d)", normalized_text):
        sensitive_warnings.append(
            "Contains a phone-like number. Remove personal identifiers before sharing."
        )
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", normalized_text):
        sensitive_warnings.append(
            "Contains an SSN-like pattern. Redact sensitive identifiers."
        )
    if re.search(r"\b(?:\d[ -]*?){13,16}\b", normalized_text):
        sensitive_warnings.append(
            "Contains a card-like number. Remove payment information."
        )
    if "sk-" in lowered:
        sensitive_warnings.append(
            "Contains an API key-like token. Remove secrets before sharing."
        )

    return {
        "clarityScore": clarity_score,
        "ctaPresent": bool(CTA_PATTERN.search(normalized_text)),
        "spamRiskWording": spam_hits,
        "sensitiveDataWarnings": sensitive_warnings,
    }
