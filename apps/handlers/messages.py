from aiogram import Router
from aiogram.types import Message

from apps.services.antispam import check_message_for_spam
from apps.utils.logger import logger
import re
import time
from collections import defaultdict


router = Router()
user_message_counts = defaultdict(int)



async def is_admin(message: Message) -> bool:
    if not message.from_user:
        return False

    member = await message.bot.get_chat_member(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
    )
    return member.status in ("administrator", "creator")

def normalize_text(text: str) -> str:
    text = text.lower()

    # убрать повторения букв
    text = re.sub(r"(.)\1{2,}", r"\1", text)

    # убрать мусор
    text = re.sub(r"[^a-zа-я0-9\s]", "", text)

    return text


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

    chat_user_key = (message.chat.id, message.from_user.id)
    user_message_counts[chat_user_key] += 1
    user_messages_seen = user_message_counts[chat_user_key]

    has_media = bool(
        message.photo
        or message.video
        or message.document
        or message.animation
    )

    extra_score = 0
    extra_reasons = []

    if has_media and not text.strip():
        extra_score += 2
        extra_reasons.append("media_no_text")

    mentions_count = text.count("@")
    text_len = len(text.strip())

    if has_media and mentions_count >= 1 and text_len < 40:
        extra_score += 2
        extra_reasons.append("media_username_short")

    result = check_message_for_spam(text)

    final_score = result.score + extra_score
    final_reason_parts = []

    if result.reason:
        final_reason_parts.append(result.reason)

    if extra_reasons:
        final_reason_parts.append(", ".join(extra_reasons))

    if user_messages_seen >= 20:
        final_score = max(0, final_score - 1)
        final_reason_parts.append("trusted_user_20")

    if user_messages_seen >= 50:
        final_score = max(0, final_score - 1)
        final_reason_parts.append("trusted_user_50")

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
        logger.info(
            f"DELETED | chat_id={message.chat.id} | "
            f"message_id={message.message_id} | "
            f"user_id={message.from_user.id} | score={final_score}"
        )
    except Exception as error:
        logger.exception(
            f"DELETE_ERROR | chat_id={message.chat.id} | "
            f"message_id={message.message_id} | "
            f"user_id={message.from_user.id} | error={error}"
        )