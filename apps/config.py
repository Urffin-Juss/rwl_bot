import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    bot_token: str
    proxy_url: str | None = None
    log_file: str = "antispam.log"


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    proxy_url = os.getenv("PROXY_URL", "").strip()
    log_file = os.getenv("LOG_FILE", "antispam.log").strip()

    if not bot_token:
        raise ValueError("BOT_TOKEN не найден в .env")

    if not proxy_url:
        proxy_url = None

    return Settings(
        bot_token=bot_token,
        proxy_url=proxy_url,
        log_file=log_file,
    )


settings = get_settings()