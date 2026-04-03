import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from apps.config import settings
from apps.handlers.messages import router as messages_router


async def main() -> None:
    print("STARTING BOT...")

    bot = None

    try:
        if settings.proxy_url:
            session = AiohttpSession(proxy=settings.proxy_url)
            bot = Bot(
                token=settings.bot_token,
                session=session,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
        else:
            bot = Bot(
                token=settings.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )

        dp = Dispatcher()
        dp.include_router(messages_router)

        me = await bot.get_me()
        print(f"Бот запущен: @{me.username}")
        print("START POLLING...")

        await dp.start_polling(bot)

    finally:
        if bot:
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("BOT STOPPED")
    except Exception as error:
        print(f"FATAL ERROR: {error}")
        raise