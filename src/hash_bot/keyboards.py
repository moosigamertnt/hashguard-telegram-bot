"""Inline keyboards and callback identifiers."""

from __future__ import annotations

from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

ARGON = "tool:argon2"
SHA256 = "tool:sha256"
VERIFY = "tool:verify"
SECURITY = "page:security"
STATUS = "page:status"
HOME = "page:home"


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔐 هش پسورد", callback_data=ARGON),
                InlineKeyboardButton("#️⃣ SHA-256", callback_data=SHA256),
            ],
            [InlineKeyboardButton("🧪 بررسی پسورد و هش", callback_data=VERIFY)],
            [
                InlineKeyboardButton("🛡 راهنمای امنیت", callback_data=SECURITY),
                InlineKeyboardButton("📊 وضعیت", callback_data=STATUS),
            ],
        ]
    )


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ بازگشت به منو", callback_data=HOME)]])


def result_actions(value: str, *, again_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 کپی خروجی", copy_text=CopyTextButton(value))],
            [
                InlineKeyboardButton("🔄 دوباره", callback_data=again_callback),
                InlineKeyboardButton("🏠 منوی اصلی", callback_data=HOME),
            ],
        ]
    )


def verification_actions() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧪 بررسی دوباره", callback_data=VERIFY)],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data=HOME)],
        ]
    )
