import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.constants import ChatType
from telegram.error import BadRequest
from telegram.ext import ConversationHandler

from hash_bot import handlers, keyboards, texts
from hash_bot.config import Settings
from hash_bot.hashing import hash_password


def make_context(*, allowed_ids: frozenset[int] = frozenset({42})) -> SimpleNamespace:
    settings = Settings("123456:TEST_TOKEN", allowed_ids)
    return SimpleNamespace(
        application=SimpleNamespace(bot_data={"settings": settings}),
        bot=SimpleNamespace(send_chat_action=AsyncMock()),
        user_data={},
        error=None,
    )


def make_update(
    text: str = "hello",
    *,
    user_id: int = 42,
    chat_type: str = ChatType.PRIVATE,
    callback_data: str | None = None,
) -> SimpleNamespace:
    message = SimpleNamespace(
        text=text,
        delete=AsyncMock(),
        reply_text=AsyncMock(),
    )
    chat = SimpleNamespace(
        id=100,
        type=chat_type,
        send_message=AsyncMock(return_value=None),
    )
    query = None
    if callback_data is not None:
        query = SimpleNamespace(
            data=callback_data,
            answer=AsyncMock(),
            edit_message_text=AsyncMock(return_value=None),
        )
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=chat,
        effective_message=message,
        callback_query=query,
    )


def run(coroutine):
    return asyncio.run(coroutine)


def last_card(update: SimpleNamespace) -> str:
    return update.effective_chat.send_message.await_args.kwargs["text"]


def test_start_renders_main_menu_for_allowed_user() -> None:
    update = make_update("/start")
    run(handlers.start(update, make_context()))

    assert "HashGuard" in last_card(update)
    assert update.effective_chat.send_message.await_args.kwargs["reply_markup"] is not None


def test_start_explains_locked_access_without_deleting_command() -> None:
    update = make_update("/start", user_id=99)
    run(handlers.start(update, make_context()))

    assert "99" in last_card(update)
    update.effective_message.delete.assert_not_awaited()


def test_show_id_is_available_before_allowlist_setup() -> None:
    update = make_update("/id", user_id=77)
    run(handlers.show_id(update, make_context(allowed_ids=frozenset())))
    assert "77" in last_card(update)


def test_plain_text_creates_argon_hash_and_deletes_input() -> None:
    update = make_update("portfolio-password")
    context = make_context()
    run(handlers.hash_plain_text(update, context))

    update.effective_message.delete.assert_awaited_once()
    context.bot.send_chat_action.assert_awaited_once()
    assert "Argon2id" in last_card(update)
    assert "$argon2id$" in last_card(update)


def test_sha_command_accepts_inline_value() -> None:
    update = make_update("/sha256 hello")
    state = run(handlers.begin_sha256(update, make_context()))

    assert state == ConversationHandler.END
    assert "SHA-256" in last_card(update)
    assert "2cf24dba" in last_card(update)


def test_callback_opens_argon_prompt_by_editing_card() -> None:
    update = make_update(callback_data=keyboards.ARGON)
    state = run(handlers.begin_argon(update, make_context()))

    assert state == handlers.ARGON_INPUT
    update.callback_query.answer.assert_awaited_once()
    assert texts.ARGON_PROMPT in update.callback_query.edit_message_text.await_args.kwargs["text"]


def test_card_falls_back_to_new_message_when_edit_fails() -> None:
    update = make_update(callback_data=keyboards.STATUS)
    update.callback_query.edit_message_text.side_effect = BadRequest("message cannot be edited")
    run(handlers.show_status(update, make_context()))
    assert "وضعیت سرویس" in last_card(update)


def test_overlong_input_is_rejected_after_deletion() -> None:
    update = make_update("too-long")
    context = make_context()
    context.application.bot_data["settings"] = Settings(
        "123456:TEST_TOKEN",
        frozenset({42}),
        max_input_length=3,
    )
    run(handlers.hash_plain_text(update, context))

    update.effective_message.delete.assert_awaited_once()
    assert "حداکثر" in last_card(update)


def test_unauthorized_hash_request_is_deleted_and_blocked() -> None:
    update = make_update("secret", user_id=99)
    run(handlers.hash_plain_text(update, make_context()))

    update.effective_message.delete.assert_awaited_once()
    assert "دسترسی محدود" in last_card(update)


def test_group_request_is_rejected() -> None:
    update = make_update("secret", chat_type=ChatType.GROUP)
    run(handlers.hash_plain_text(update, make_context()))
    update.effective_message.reply_text.assert_awaited_once()


def test_complete_verification_flow_clears_temporary_hash() -> None:
    context = make_context()
    encoded = hash_password("correct-password")

    async def scenario() -> None:
        start_update = make_update("/verify")
        assert await handlers.begin_verify(start_update, context) == handlers.VERIFY_HASH_INPUT

        hash_update = make_update(encoded)
        assert (
            await handlers.receive_verify_hash(hash_update, context)
            == handlers.VERIFY_PASSWORD_INPUT
        )

        password_update = make_update("correct-password")
        assert (
            await handlers.receive_verify_password(password_update, context)
            == ConversationHandler.END
        )
        assert "تطابق تأیید شد" in last_card(password_update)

    run(scenario())
    assert handlers.PENDING_HASH_KEY not in context.user_data


def test_invalid_argon_hash_keeps_verification_on_first_step() -> None:
    update = make_update("not-an-argon-hash")
    state = run(handlers.receive_verify_hash(update, make_context()))
    assert state == handlers.VERIFY_HASH_INPUT
    assert "معتبر" in last_card(update)


def test_information_cards_and_home_navigation() -> None:
    context = make_context()

    security = make_update(callback_data=keyboards.SECURITY)
    run(handlers.show_security(security, context))
    assert "Argon2id" in security.callback_query.edit_message_text.await_args.kwargs["text"]

    home = make_update(callback_data=keyboards.HOME)
    state = run(handlers.show_home(home, context))
    assert state == ConversationHandler.END
    assert "HashGuard" in home.callback_query.edit_message_text.await_args.kwargs["text"]


def test_unknown_command_returns_menu() -> None:
    update = make_update("/does_not_exist")
    run(handlers.unknown_command(update, make_context()))
    assert "نمی‌شناسم" in last_card(update)


def test_post_init_registers_public_commands() -> None:
    application = SimpleNamespace(bot=SimpleNamespace(set_my_commands=AsyncMock()))
    run(handlers.post_init(application))
    commands = application.bot.set_my_commands.await_args.args[0]
    assert {command.command for command in commands} >= {"start", "hash", "verify"}
