import re
from typing import Iterable, List


def split_sentences(text: str) -> List[str]:
    if not text.strip():
        return []
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def normalize_list_from_text(text: str, max_items: int = 5) -> List[str]:
    if not text.strip():
        return []

    raw_items: List[str] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        candidate = re.sub(r"^[\-\*\d\.\)\s]+", "", candidate).strip()
        if candidate:
            raw_items.append(candidate)

    if not raw_items:
        raw_items = [part.strip() for part in text.split(",") if part.strip()]

    deduped: List[str] = []
    seen = set()
    for item in raw_items:
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
        if len(deduped) >= max_items:
            break

    return deduped


def pick_sentences_by_keywords(
    text: str, keywords: Iterable[str], max_items: int = 3
) -> List[str]:
    keywords_lower = tuple(keyword.lower() for keyword in keywords)
    matches: List[str] = []
    for sentence in split_sentences(text):
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords_lower):
            matches.append(sentence)
            if len(matches) >= max_items:
                break
    return matches


def extract_question_sentence(text: str, fallback: str) -> str:
    for sentence in split_sentences(text):
        if "?" in sentence:
            return sentence
    return fallback


def infer_call_to_action(text: str, fallback: str) -> str:
    cta_keywords = (
        "reply",
        "schedule",
        "book",
        "connect",
        "sign up",
        "learn more",
        "reach out",
        "talk",
        "share",
    )
    for sentence in split_sentences(text):
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in cta_keywords):
            return sentence
    return fallback


def extract_hashtags(text: str) -> List[str]:
    tags = [f"#{tag}" for tag in re.findall(r"#([A-Za-z0-9_]+)", text)]
    deduped: List[str] = []
    seen = set()
    for tag in tags:
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(tag)
    return deduped


def build_hashtags_from_content(text: str, max_items: int = 5) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", text)
    candidates = [word for word in words if len(word) >= 5]
    deduped: List[str] = []
    seen = set()
    for candidate in candidates:
        normalized = candidate.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(f"#{candidate.capitalize()}")
        if len(deduped) >= max_items:
            break
    return deduped


def extract_tagged_block(text: str, tag: str) -> str:
    pattern = rf"(?:^|\n){re.escape(tag)}\s*:\s*(.*?)(?=\n[A-Z0-9_]+\s*:|\Z)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def build_fallback_follow_up_emails(summary: str, next_actions: List[str]) -> List[str]:
    primary_action = next_actions[0] if next_actions else "align on next steps"
    concise_summary = summary if summary else "Thanks for the conversation today."
    return [
        (
            "Hi there,\n\n"
            f"Thanks again for the call. {concise_summary}\n\n"
            f"To keep momentum, I'd like to {primary_action.lower()}.\n\n"
            "Would you be open to a 20-minute follow-up this week?\n\n"
            "Best,\n"
        ),
        (
            "Hi there,\n\n"
            "Appreciate your time earlier. I captured your priorities and concerns.\n\n"
            f"My suggestion is we {primary_action.lower()} and confirm owners/timing.\n\n"
            "If helpful, I can send a one-page plan before our next call.\n\n"
            "Best,\n"
        ),
        (
            "Hi there,\n\n"
            "Great speaking with you today. I wanted to quickly recap and propose the next step.\n\n"
            f"Based on our discussion, the immediate action is to {primary_action.lower()}.\n\n"
            "Please share two times that work this week and I will lock in the meeting.\n\n"
            "Best,\n"
        ),
    ]
