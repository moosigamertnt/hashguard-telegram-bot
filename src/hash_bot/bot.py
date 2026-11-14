"""Application assembly and executable entry point."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from hash_bot.config import ConfigError, Settings
from hash_bot.handlers import post_init, register_handlers


def build_application(settings: Settings) -> Application:
    """Build the Telegram application without starting network I/O."""
    application = (
        ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).build()
    )
    application.bot_data["settings"] = settings
    register_handlers(application)
    return application


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    if not settings.allowed_user_ids:
        logging.getLogger(__name__).warning(
            "The allowlist is empty. Hashing stays locked; use /id to bootstrap access."
        )

    application = build_application(settings)
    logging.getLogger(__name__).info("HashGuard started. Press Ctrl+C to stop.")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
