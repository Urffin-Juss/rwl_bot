from collections import defaultdict
import time

from aiogram import Router
from aiogram.types import Message

from apps.services.antispam import check_message_for_spam
from apps.utils.logger import logger


router = Router()

user_stats = defaultdict(lambda: {
    "messages": 0,
    "spam_hits": 0,
    "first_seen": time.time(),
})


def get_user_trust_level(messages_count: int) -> int:
    if messages_count >= 100:
        return 3
    if messages_count >= 30:
        return 2
    if messages_count >= 10:
        return 1
    return 0


async def is_admin(message: Message) -> bool:
    if not message.from_user:
        return False

    member = await message.bot.get_chat_member(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
    )
    return member.status in ("administrator", "creator")


def build_log_line(
    message: Message,
    verdict: str,
    score: int,
    reason: str,
    text: str,
) -> str:
    user_id = message.from_user.id if message.from_user else "unknown"
    username = (
        message.from_user.username
        if message.from_user and message.from_user.username
        else "-"
    )
    full_name = message.from_user.full_name if message.from_user else "unknown"
    chat_id = message.chat.id
    chat_title = message.chat.title or "private"
    message_id = message.message_id
    safe_text = text.replace("\n", "\\n").strip()

    return (
        f"verdict={verdict} | score={score} | reason={reason or '-'} | "
        f"chat_id={chat_id} | chat_title={chat_title} | "
        f"user_id={user_id} | username=@{username if username != '-' else '-'} | "
        f"full_name={full_name} | message_id={message_id} | text={safe_text}"
    )


@router.message()
async def handle_all_messages(message: Message) -> None:
    if not message.from_user:
        return

    if await is_admin(message):
        return

    text = message.text or message.caption or ""
    text_lower = text.lower()
    user_id = message.from_user.id
    chat_user_key = (message.chat.id, user_id)

    stats = user_stats[chat_user_key]
    stats["messages"] += 1
    user_messages_seen = stats["messages"]

    trust_level = get_user_trust_level(user_messages_seen)

    is_offer = False

    if any(word in text_lower for word in ["в личку", "в лс", "подробности", "пиши"]):
        is_offer = True

    if any(word in text_lower for word in ["руб", "₽", "тыс"]):
        is_offer = True

    if "@" in text:
        is_offer = True

    has_media = bool(
        message.photo
        or message.video
        or message.document
        or message.animation
    )

    has_inline_keyboard = bool(
        message.reply_markup and getattr(message.reply_markup, "inline_keyboard", None)
    )

    is_forwarded = bool(message.forward_origin)
    is_reply = bool(message.reply_to_message)

    extra_score = 0
    extra_reasons = []

    mentions_count = text.count("@")
    text_len = len(text.strip())

    button_count = 0
    button_url_count = 0
    button_texts = []

    if has_inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for button in row:
                button_count += 1

                if getattr(button, "url", None):
                    button_url_count += 1

                if getattr(button, "text", None):
                    button_texts.append(button.text.lower())

    if has_inline_keyboard:
        extra_score += 2
        extra_reasons.append("inline_keyboard")

    if button_count >= 3:
        extra_score += 1
        extra_reasons.append("many_buttons")

    if button_url_count >= 2:
        extra_score += 2
        extra_reasons.append("button_urls")

    adult_button_words = {
        "18+",
        "video nóng",
        "clip",
        "nữ sinh",
        "hot",
        "watch",
        "sex",
    }

    joined_button_text = " ".join(button_texts)

    for word in adult_button_words:
        if word in joined_button_text:
            extra_score += 2
            extra_reasons.append(f"adult_button:{word}")

    review_words = {
        "спасибо",
        "реально",
        "рабочий",
        "работает",
        "загружается",
        "снова загружается",
        "оказался рабочий",
    }

    review_hits = [word for word in review_words if word in text_lower]

    if review_hits and trust_level <= 1:
        if is_forwarded or is_reply or has_inline_keyboard:
            extra_score += 2
            extra_reasons.append("embedded_review")

        if len(text.split()) <= 10:
            extra_score += 1
            extra_reasons.append("short_review")

    if has_inline_keyboard and trust_level <= 1:
        if any(word in text_lower for word in ["в день", "пиши", "18+", "доход", "заработок"]):
            extra_score += 2
            extra_reasons.append("button_spam_offer")

    if is_forwarded and has_inline_keyboard:
        extra_score += 1
        extra_reasons.append("forwarded_with_buttons")

    if has_media and not text.strip():
        if trust_level == 0:
            extra_score += 2
            extra_reasons.append("media_no_text_new")
        elif trust_level == 1:
            extra_score += 1
            extra_reasons.append("media_no_text_low")

    if has_media and mentions_count >= 1 and text_len < 40:
        if trust_level == 0:
            extra_score += 2
            extra_reasons.append("media_username_short_new")
        elif trust_level == 1:
            extra_score += 1
            extra_reasons.append("media_username_short_low")

    if has_media and "http" in text_lower:
        if trust_level == 0:
            extra_score += 2
            extra_reasons.append("media_link_new")
        elif trust_level == 1:
            extra_score += 1
            extra_reasons.append("media_link_low")

    if any(word in text_lower for word in ["руб", "₽", "тыс"]) and "@" in text:
        extra_score += 1
        extra_reasons.append("money_username")

    if "пиши" in text_lower and "@" in text:
        extra_score += 1
        extra_reasons.append("call_to_dm")

    # reply — сильный сигнал нормального общения
    if is_reply:
        extra_score -= 2
        extra_reasons.append("reply_context")

    # защита старых участников
    if user_messages_seen >= 20 and not is_offer:
        extra_score -= 2
        extra_reasons.append("trusted_user")

    result = check_message_for_spam(text)

    final_score = result.score + extra_score
    if final_score < 0:
        final_score = 0

    final_reason_parts = []

    if result.reason:
        final_reason_parts.append(result.reason)

    if extra_reasons:
        final_reason_parts.append(", ".join(extra_reasons))

    if trust_level == 2:
        final_score = max(0, final_score - 1)
        final_reason_parts.append("trusted_user_lvl2")

    if trust_level == 3:
        final_score = max(0, final_score - 2)
        final_reason_parts.append("trusted_user_lvl3")

    final_reason = ", ".join(final_reason_parts)
    verdict = "SPAM" if final_score >= 3 else "OK"

    logger.info(
        build_log_line(
            message=message,
            verdict=verdict,
            score=final_score,
            reason=final_reason,
            text=text,
        )
    )

    if final_score < 3:
        return

    try:
        await message.delete()
        stats["spam_hits"] += 1
        logger.info(
            f"DELETED | chat_id={message.chat.id} | "
            f"message_id={message.message_id} | "
            f"user_id={user_id} | score={final_score}"
        )
    except Exception as error:
        logger.exception(
            f"DELETE_ERROR | chat_id={message.chat.id} | "
            f"message_id={message.message_id} | "
            f"user_id={user_id} | error={error}"
        )