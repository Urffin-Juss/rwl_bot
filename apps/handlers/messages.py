from aiogram import Router
from aiogram.types import Message

from apps.services.antispam import check_message_for_spam
from apps.utils.logger import logger
from collections import defaultdict
import time


router = Router()

recent_messages = defaultdict(list)


async def is_admin(message: Message) -> bool:
    if not message.from_user:
        return False

    text = message.text or message.caption or ""
    user_id = message.from_user.id
    now = time.time()

    recent_messages[user_id] = [
        (t, txt) for t, txt in recent_messages[user_id]
        if now - t < 10
    ]

    for t, txt in recent_messages[user_id]:
        if txt == text:
            logger.info(
                f"DUPLICATE | chat_id={message.chat.id} | "
                f"user_id={user_id} | message_id={message.message_id} | text={text}"
            )
            try:
                await message.delete()
            except Exception as error:
                logger.exception(
                    f"DELETE_ERROR_DUPLICATE | chat_id={message.chat.id} | "
                    f"user_id={user_id} | message_id={message.message_id} | error={error}"
                )
            return

    recent_messages[user_id].append((now, text))

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
    result = check_message_for_spam(text)

    verdict = "SPAM" if result.is_spam else "OK"

    logger.info(
        build_log_line(
            message=message,
            verdict=verdict,
            score=result.score,
            reason=result.reason,
            text=text,
        )
    )

    if not result.is_spam:
        return

    try:
        await message.delete()
        logger.info(
            f"DELETED | chat_id={message.chat.id} | "
            f"message_id={message.message_id} | "
            f"user_id={message.from_user.id} | score={result.score}"
        )
    except Exception as error:
        logger.exception(
            f"DELETE_ERROR | chat_id={message.chat.id} | "
            f"message_id={message.message_id} | "
            f"user_id={message.from_user.id} | error={error}"
        )