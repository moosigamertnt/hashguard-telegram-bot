"""Telegram update handlers and conversation flows."""

from __future__ import annotations

import asyncio
import html
import logging
import warnings
from typing import cast

from telegram import BotCommand, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction, ChatType, ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.warnings import PTBUserWarning

from hash_bot import keyboards, texts
from hash_bot.config import Settings
from hash_bot.hashing import (
    hash_password,
    is_argon2_hash,
    sha256_digest,
    verify_password,
)

logger = logging.getLogger(__name__)
ARGON_INPUT, SHA_INPUT, VERIFY_HASH_INPUT, VERIFY_PASSWORD_INPUT = range(4)
HASH_WORKERS = asyncio.Semaphore(2)
PENDING_HASH_KEY = "pending_argon_hash"


def _settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return cast(Settings, context.application.bot_data["settings"])


def _user_data(context: ContextTypes.DEFAULT_TYPE) -> dict[str, object]:
    if context.user_data is None:
        raise RuntimeError("Per-user context storage is unavailable.")
    return cast(dict[str, object], context.user_data)


def _message_text(update: Update) -> str:
    message = update.effective_message
    return message.text or "" if message is not None else ""


def _is_private(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type == ChatType.PRIVATE)


def _is_allowed(update: Update, settings: Settings) -> bool:
    user = update.effective_user
    return bool(user and user.id in settings.allowed_user_ids)


async def _delete_user_message(update: Update, settings: Settings) -> None:
    """Delete a user-authored message without ever logging its contents."""
    if not settings.delete_input_messages or update.callback_query is not None:
        return
    message = update.effective_message
    if message is None:
        return
    try:
        await message.delete()
    except (BadRequest, Forbidden):
        logger.warning("Could not delete an incoming message; its content was not logged.")


async def _show_card(
    update: Update,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> Message | None:
    """Edit an inline card when possible, otherwise send a fresh one."""
    query = update.callback_query
    if query is not None:
        await query.answer()
        try:
            result = await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            return result if isinstance(result, Message) else None
        except BadRequest:
            logger.debug("Could not edit the existing card; sending a new one.")

    chat = update.effective_chat
    if chat is None:
        return None
    return await chat.send_message(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def _guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Enforce private-chat and allowlist access for every tool."""
    settings = _settings(context)
    if not _is_private(update):
        if update.callback_query is not None:
            await update.callback_query.answer(
                "برای حفظ حریم خصوصی، ربات فقط در چت خصوصی فعال است.",
                show_alert=True,
            )
        elif update.effective_message is not None:
            await update.effective_message.reply_text(
                "برای حفظ حریم خصوصی، ربات را در چت خصوصی باز کن."
            )
        return False

    if _is_allowed(update, settings):
        return True

    if update.callback_query is not None:
        await update.callback_query.answer("دسترسی شما ثبت نشده است.", show_alert=True)
    else:
        await _delete_user_message(update, settings)

    user = update.effective_user
    if user is not None:
        await _show_card(update, texts.LOCKED.format(user_id=user.id))
    return False


def _command_value(update: Update) -> str:
    message = update.effective_message
    if message is None or not message.text:
        return ""
    parts = message.text.split(maxsplit=1)
    return parts[1] if len(parts) == 2 else ""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        if update.effective_message is not None:
            await update.effective_message.reply_text("لطفاً ربات را در چت خصوصی باز کن.")
        return

    settings = _settings(context)
    if not _is_allowed(update, settings):
        user = update.effective_user
        if user is not None:
            await _show_card(update, texts.LOCKED.format(user_id=user.id))
        return

    _user_data(context).pop(PENDING_HASH_KEY, None)
    await _show_card(update, texts.WELCOME, keyboards.main_menu())


async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not _is_private(update) or update.effective_user is None:
        return
    await _show_card(
        update,
        f"🪪 Telegram ID شما: <code>{update.effective_user.id}</code>",
    )


async def _hash_and_respond(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    value: str,
    algorithm: str,
) -> bool:
    if not await _guard(update, context):
        return False

    settings = _settings(context)
    await _delete_user_message(update, settings)
    if not value:
        await _show_card(update, texts.EMPTY_INPUT, keyboards.back_to_menu())
        return False
    if len(value) > settings.max_input_length:
        await _show_card(
            update,
            texts.INPUT_TOO_LONG.format(limit=settings.max_input_length),
            keyboards.back_to_menu(),
        )
        return False

    chat = update.effective_chat
    if chat is not None:
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)

    async with HASH_WORKERS:
        if algorithm == "argon2id":
            result = await asyncio.to_thread(hash_password, value)
            label = "Argon2id"
            again_callback = keyboards.ARGON
        else:
            result = await asyncio.to_thread(sha256_digest, value)
            label = "SHA-256"
            again_callback = keyboards.SHA256

    await _show_card(
        update,
        texts.hash_result(label=label, value=html.escape(result)),
        keyboards.result_actions(result, again_callback=again_callback),
    )
    return True


async def begin_argon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = "" if update.callback_query else _command_value(update)
    if value:
        await _hash_and_respond(update, context, value=value, algorithm="argon2id")
        return ConversationHandler.END
    if not await _guard(update, context):
        return ConversationHandler.END
    await _show_card(update, texts.ARGON_PROMPT, keyboards.back_to_menu())
    return ARGON_INPUT


async def receive_argon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _message_text(update)
    success = await _hash_and_respond(update, context, value=value, algorithm="argon2id")
    return ConversationHandler.END if success else ARGON_INPUT


async def begin_sha256(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = "" if update.callback_query else _command_value(update)
    if value:
        await _hash_and_respond(update, context, value=value, algorithm="sha256")
        return ConversationHandler.END
    if not await _guard(update, context):
        return ConversationHandler.END
    await _show_card(update, texts.SHA_PROMPT, keyboards.back_to_menu())
    return SHA_INPUT


async def receive_sha256(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _message_text(update)
    success = await _hash_and_respond(update, context, value=value, algorithm="sha256")
    return ConversationHandler.END if success else SHA_INPUT


async def begin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _guard(update, context):
        return ConversationHandler.END
    _user_data(context).pop(PENDING_HASH_KEY, None)
    await _show_card(update, texts.VERIFY_HASH_PROMPT, keyboards.back_to_menu())
    return VERIFY_HASH_INPUT


async def receive_verify_hash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _guard(update, context):
        return ConversationHandler.END

    settings = _settings(context)
    encoded_hash = _message_text(update)
    await _delete_user_message(update, settings)

    if len(encoded_hash) > settings.max_input_length or not is_argon2_hash(encoded_hash):
        await _show_card(update, texts.INVALID_ARGON_HASH, keyboards.back_to_menu())
        return VERIFY_HASH_INPUT

    _user_data(context)[PENDING_HASH_KEY] = encoded_hash
    await _show_card(update, texts.VERIFY_PASSWORD_PROMPT, keyboards.back_to_menu())
    return VERIFY_PASSWORD_INPUT


async def receive_verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _guard(update, context):
        _user_data(context).pop(PENDING_HASH_KEY, None)
        return ConversationHandler.END

    settings = _settings(context)
    password = _message_text(update)
    encoded_hash = _user_data(context).pop(PENDING_HASH_KEY, None)
    await _delete_user_message(update, settings)

    if not isinstance(encoded_hash, str) or not encoded_hash or not password:
        await _show_card(update, texts.EMPTY_INPUT, keyboards.back_to_menu())
        return ConversationHandler.END

    async with HASH_WORKERS:
        result = await asyncio.to_thread(verify_password, encoded_hash, password)

    await _show_card(
        update,
        texts.verification_result(
            matches=result.matches,
            needs_rehash=result.needs_rehash,
        ),
        keyboards.verification_actions(),
    )
    return ConversationHandler.END


async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _guard(update, context):
        return ConversationHandler.END
    _user_data(context).pop(PENDING_HASH_KEY, None)
    await _show_card(update, texts.WELCOME, keyboards.main_menu())
    return ConversationHandler.END


async def show_security(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update, context):
        await _show_card(update, texts.SECURITY, keyboards.back_to_menu())


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update, context):
        return
    settings = _settings(context)
    await _show_card(
        update,
        texts.status_text(
            allowed_users=len(settings.allowed_user_ids),
            delete_enabled=settings.delete_input_messages,
            max_length=settings.max_input_length,
        ),
        keyboards.back_to_menu(),
    )


async def hash_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    value = _message_text(update)
    await _hash_and_respond(update, context, value=value, algorithm="argon2id")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update, context):
        await _show_card(
            update,
            "این دستور را نمی‌شناسم؛ از منوی زیر استفاده کن.",
            keyboards.main_menu(),
        )


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "بازکردن منوی اصلی"),
            BotCommand("hash", "ساخت هش امن Argon2id"),
            BotCommand("sha256", "ساخت checksum با SHA-256"),
            BotCommand("verify", "بررسی پسورد با هش Argon2id"),
            BotCommand("id", "نمایش Telegram ID"),
            BotCommand("cancel", "لغو عملیات فعلی"),
        ]
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    del update
    logger.error(
        "Unhandled update error: %s",
        type(context.error).__name__,
        exc_info=context.error,
    )


def _build_conversation() -> ConversationHandler:
    """Build a per-user flow that intentionally spans multiple messages."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(begin_argon, pattern=f"^{keyboards.ARGON}$"),
            CallbackQueryHandler(begin_sha256, pattern=f"^{keyboards.SHA256}$"),
            CallbackQueryHandler(begin_verify, pattern=f"^{keyboards.VERIFY}$"),
            CommandHandler("hash", begin_argon),
            CommandHandler("sha256", begin_sha256),
            CommandHandler("verify", begin_verify),
        ],
        states={
            ARGON_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_argon)],
            SHA_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sha256)],
            VERIFY_HASH_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_verify_hash)
            ],
            VERIFY_PASSWORD_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_verify_password)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(show_home, pattern=f"^{keyboards.HOME}$"),
            CommandHandler("cancel", show_home),
        ],
        allow_reentry=True,
    )


def register_handlers(application: Application) -> None:
    """Register handlers in precedence order."""
    # This flow intentionally tracks one conversation per chat/user, not per message.
    # PTB warns because it also contains callback buttons, so suppress that exact warning.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="If 'per_message=False'.*",
            category=PTBUserWarning,
        )
        conversation = _build_conversation()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("id", show_id))
    application.add_handler(conversation)
    application.add_handler(CallbackQueryHandler(show_home, pattern=f"^{keyboards.HOME}$"))
    application.add_handler(CallbackQueryHandler(show_security, pattern=f"^{keyboards.SECURITY}$"))
    application.add_handler(CallbackQueryHandler(show_status, pattern=f"^{keyboards.STATUS}$"))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hash_plain_text))
    application.add_error_handler(error_handler)
