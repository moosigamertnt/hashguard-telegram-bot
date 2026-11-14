from hash_bot.bot import build_application
from hash_bot.config import Settings


def test_application_is_built_with_handlers_and_redacted_settings() -> None:
    settings = Settings("123456:TEST_TOKEN", frozenset({42}))
    application = build_application(settings)

    assert application.bot_data["settings"] is settings
    assert application.handlers
    assert "TEST_TOKEN" not in repr(settings)
