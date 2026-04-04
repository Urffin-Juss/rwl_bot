import re
from dataclasses import dataclass


WORK_WORDS = {
    "удалёнка",
    "удаленка",
    "доход",
    "заработок",
    "без вложений",
    "в день",
    "в неделю",
    "пиши",
    "пишите",
    "в лс",
    "обучение",
    "свободный график",
    "18+",
    "партнер",

}

VPN_WORDS = {
    "vpn",
    "впн",
    "vpn для telegram",
    "для telegram",
    "telegram заработал",
    "работает при блокировках",
    "обход блокировок",
}

REVIEW_SPAM = {
    "спасибо",
    "реально работает",
    "супер",
    "хорошая",
    "теперь работает",
}

DOCUMENT_WORDS = {
    "удостоверение",
    "удостоверения",
    "права",
    "документы",
    "гимс",
    "водительского удостоверения",
    "помощь с документами",
    "оформление документов",
}

ADULT_WORDS = {
    "эскорт",
    "escort",
    "интим",
    "18+",
    "досуг",
    "массаж",
    "релакс",
    "без комплексов",
    "встреча",
    "апартаменты",
    "выезд",
    "конфиденциально",
    "анон",
    "анончик",
    "свободна",
    "свободная",
    "свободен",
}

ADULT_SUSPICIOUS = {
    "пиши в лс",
    "в личку",
    "за подробностями",
    "фото в профиле",
    "цены в лс",
    "подробности в лс",
    "отдых",
    "приятное общение",
}

SERVICE_WORDS = {
    "оформление",
    "документы",
    "удостоверение",
    "права",
    "гимс",
    "помощь с",
}

CALL_TO_ACTION = {
    "обращайтесь",
    "за деталями",
    "пишите",
    "в лс",
    "в личку",
}

SUSPICIOUS_PHRASES = {
    "за деталями обращайтесь",
    "обращайтесь сюда",
    "подробности в лс",
    "за подробностями",
    "пишите сюда",
    "обращайтесь в лс",
}

LINK_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)",
    re.IGNORECASE,
)

USERNAME_PATTERN = re.compile(r"@\w+")


@dataclass
class SpamCheckResult:
    is_spam: bool
    reason: str
    score: int


def count_matches(text_lower: str, words: set[str]) -> list[str]:
    found = []
    for word in words:
        if word in text_lower:
            found.append(word)
    return found




def check_message_for_spam(text: str | None) -> SpamCheckResult:
    if not text:
        return SpamCheckResult(False, "", 0)

    text_lower = text.lower()
    score = 0
    reasons: list[str] = []

    if LINK_PATTERN.search(text):
        score += 3
        reasons.append("ссылка")

    if USERNAME_PATTERN.search(text):
        score += 2
        reasons.append("username")

    work_found = count_matches(text_lower, WORK_WORDS)
    if work_found:
        score += len(work_found)
        reasons.append(f"work:{', '.join(work_found)}")

    vpn_hits = []

    for word in VPN_WORDS:
        if word in text_lower:
            vpn_hits.append(word)

    if vpn_hits:
        score += 2 * len(vpn_hits)
        reasons.append(f"vpn:{', '.join(vpn_hits)}")

    review_hits = []

    for word in REVIEW_SPAM:
        if word in text_lower:
            review_hits.append(word)

    if review_hits:
        score += len(review_hits)
        reasons.append(f"review:{', '.join(review_hits)}")

    doc_found = count_matches(text_lower, DOCUMENT_WORDS)
    if doc_found:
        score += 2 * len(doc_found)
        reasons.append(f"docs:{', '.join(doc_found)}")

    suspicious_found = count_matches(text_lower, SUSPICIOUS_PHRASES)
    if suspicious_found:
        score += 2 * len(suspicious_found)
        reasons.append(f"suspicious:{', '.join(suspicious_found)}")

    if text.isupper() and len(text) > 10:
        score += 1
        reasons.append("капс")

    adult_hits = []
    for word in ADULT_WORDS:
        if word in text_lower:
            adult_hits.append(word)

    if adult_hits:
        score += 2 * len(adult_hits)
        reasons.append(f"adult:{', '.join(adult_hits)}")

    adult_suspicious_hits = []
    for phrase in ADULT_SUSPICIOUS:
        if phrase in text_lower:
            adult_suspicious_hits.append(phrase)

    if adult_suspicious_hits:
        score += len(adult_suspicious_hits)
        reasons.append(f"adult_suspicious:{', '.join(adult_suspicious_hits)}")

    emoji_count = sum(1 for c in text if c in "🔥🚀💰💸📈📊💵💶💷💴❗️‼️")
    if emoji_count >= 7:
        score += 1
        reasons.append("эмодзи")

    if score >= 3:
        return SpamCheckResult(
            True,
            ", ".join(reasons),
            score,
        )

    return SpamCheckResult(False, ", ".join(reasons), score)