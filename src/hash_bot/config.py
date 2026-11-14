"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when required application configuration is invalid."""


def parse_user_ids(raw_value: str) -> frozenset[int]:
    """Parse a comma-separated Telegram user ID allowlist."""
    if not raw_value.strip():
        return frozenset()

    user_ids: set[int] = set()
    for item in raw_value.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            user_id = int(value)
        except ValueError as exc:
            raise ConfigError(
                "ALLOWED_USER_IDS must contain only numeric IDs separated by commas."
            ) from exc
        if user_id <= 0:
            raise ConfigError("Telegram user IDs in ALLOWED_USER_IDS must be positive.")
        user_ids.add(user_id)
    return frozenset(user_ids)


def parse_bool(raw_value: str, *, name: str) -> bool:
    """Parse a human-friendly boolean environment variable."""
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be one of: true, false, 1, 0, yes, no.")


def parse_max_input_length(raw_value: str) -> int:
    """Validate the Telegram text input limit used by the bot."""
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError("MAX_INPUT_LENGTH must be a number.") from exc
    if not 1 <= value <= 4096:
        raise ConfigError("MAX_INPUT_LENGTH must be between 1 and 4096.")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str = field(repr=False)
    allowed_user_ids: frozenset[int]
    delete_input_messages: bool = True
    max_input_length: int = 4096

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ConfigError(
                "TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and add the token."
            )

        return cls(
            telegram_bot_token=token,
            allowed_user_ids=parse_user_ids(os.getenv("ALLOWED_USER_IDS", "")),
            delete_input_messages=parse_bool(
                os.getenv("DELETE_INPUT_MESSAGES", "true"),
                name="DELETE_INPUT_MESSAGES",
            ),
            max_input_length=parse_max_input_length(os.getenv("MAX_INPUT_LENGTH", "4096")),
        )
