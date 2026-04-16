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
    "реально работает",
    "супер",
    "хорошая",
    "теперь работает",
    "работает",
    "реально работает",
    "помог",
    "помогло",
    "помогает",
    "лучший",
    "топ",
    "без перебоев",
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
    "досуг",
    "массаж",
    "релакс",
    "без комплексов",
    "апартаменты",
    "выезд",
    "конфиденциально",
    "свободна",
    "свободная",
}

ADULT_SUSPICIOUS = {

    "за подробностями",
    "фото в профиле",
    "цены в лс",
    "подробности в лс",
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

    money_offer_patterns = [
        "жми сюда",
        "2-3 часа",
        "1-5 часов",
        "5 000",
        "5000",
        "6 000",
        "6000",
    ]

    money_offer_hits = [p for p in money_offer_patterns if p in text_lower]





    if money_offer_hits:
        score += len(money_offer_hits)
        score += 3
        reasons.append(f"offer:{', '.join(money_offer_hits)}")

    links = LINK_PATTERN.findall(text)
    if len(links) >= 2:
        score += 3
        reasons.append("multi_links")

    if LINK_PATTERN.search(text):
        score += 1
        reasons.append("ссылка")

    if USERNAME_PATTERN.search(text):
        score += 1
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

    if "t.me/" in text_lower and "start=" in text_lower:
        score += 4
        reasons.append("ref_link")

    if len(text.split()) <= 5 and score >= 2:
        score += 1
        reasons.append("short_spam")

    if len(set(links)) == 1 and len(links) > 1:
        score += 2
        reasons.append("duplicate_links")

    review_patterns = [
        "работает",
        "реально работает",
        "очень хороший",
        "всем советую",
        "лучший",
        "помогло",
    ]

    if "спасибо" in text_lower and any(p in text_lower for p in review_patterns):
        score += 2
        reasons.append("review_spam")

    normal_context_patterns = [
        "что",
        "напомнил",
        "сказал",
        "ответил",
    ]

    if "спасибо" in text_lower and any(p in text_lower for p in normal_context_patterns):
        score -= 2
        reasons.append("normal_thanks")





    if score >= 3:
        return SpamCheckResult(
            True,
            ", ".join(reasons),
            score,
        )

    return SpamCheckResult(False, ", ".join(reasons), score)

