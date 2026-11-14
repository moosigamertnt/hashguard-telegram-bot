"""Persian user-facing copy kept outside the handlers."""

from __future__ import annotations

WELCOME = """🔐 <b>HashGuard</b>
<blockquote>ابزار شخصی ساخت و بررسی هش، بدون ذخیره‌کردن ورودی‌ها</blockquote>

یکی از ابزارهای زیر را انتخاب کن. برای استفاده‌ی سریع هم می‌توانی هر متن عادی را
مستقیم بفرستی تا با Argon2id هش شود.

🔒 پیام ورودی بعد از پردازش حذف می‌شود."""

LOCKED = """🔒 <b>دسترسی محدود است</b>

این ربات فقط برای مالک‌های ثبت‌شده فعال می‌شود.
Telegram ID شما: <code>{user_id}</code>

شناسه را در متغیر <code>ALLOWED_USER_IDS</code> قرار بده و ربات را دوباره اجرا کن."""

ARGON_PROMPT = """🔐 <b>ساخت هش امن پسورد</b>

پسورد یا متن موردنظر را در پیام بعدی بفرست.

<i>از Argon2id با salt تصادفی استفاده می‌شود؛ بنابراین دو خروجی برای یک ورودی عمداً متفاوت‌اند.</i>"""

SHA_PROMPT = """#️⃣ <b>ساخت SHA-256</b>

متن موردنظر را در پیام بعدی بفرست.

⚠️ SHA-256 برای checksum و تشخیص تغییر داده مناسب است، نه برای ذخیره‌ی پسورد."""

VERIFY_HASH_PROMPT = """🧪 <b>بررسی هش Argon2id</b>

ابتدا هش کامل ذخیره‌شده را بفرست؛ باید با <code>$argon2</code> شروع شود."""

VERIFY_PASSWORD_PROMPT = """🧪 <b>مرحله‌ی دوم</b>

حالا پسوردی را که می‌خواهی با هش مقایسه شود بفرست.
هر دو ورودی بعد از نتیجه از حافظه‌ی موقت پاک می‌شوند."""

SECURITY = """🛡 <b>راهنمای انتخاب الگوریتم</b>

<b>Argon2id</b>
برای ذخیره‌ی پسورد در دیتابیس. کند و memory-hard طراحی شده و salt را داخل خروجی نگه می‌دارد.

<b>SHA-256</b>
برای checksum فایل یا داده و تشخیص تغییر. سریع و قطعی است، پس برای پسورد مناسب نیست.

⚠️ برای داده‌ی واقعی production، هش‌کردن را در backend خود برنامه انجام بده؛
هیچ پسورد حساسی را از پیام‌رسان عبور نده."""

INVALID_ARGON_HASH = """❌ این رشته یک هش معتبر Argon2 نیست.

هش کامل را بدون کوتاه‌کردن بفرست؛ نمونه‌ی معتبر با <code>$argon2id$</code> شروع می‌شود."""

INPUT_TOO_LONG = "⚠️ ورودی بیش از حد طولانی است. حداکثر طول مجاز <code>{limit}</code> کاراکتر است."

EMPTY_INPUT = "متن خالی قابل پردازش نیست. دوباره یک مقدار بفرست."


def status_text(*, allowed_users: int, delete_enabled: bool, max_length: int) -> str:
    deletion = "فعال ✅" if delete_enabled else "غیرفعال ⚠️"
    return f"""📊 <b>وضعیت سرویس</b>

• حالت اجرا: Polling
• الگوریتم پسورد: Argon2id
• الگوریتم checksum: SHA-256
• حذف پیام ورودی: {deletion}
• کاربران مجاز: <code>{allowed_users}</code>
• سقف ورودی: <code>{max_length}</code> کاراکتر

🟢 سرویس آماده است."""


def hash_result(*, label: str, value: str) -> str:
    return f"""✅ <b>خروجی آماده است</b>

الگوریتم: <b>{label}</b>
<code>{value}</code>

با دکمه‌ی زیر خروجی را کپی کن."""


def verification_result(*, matches: bool, needs_rehash: bool = False) -> str:
    if not matches:
        return """❌ <b>عدم تطابق</b>

این پسورد با هش ارسال‌شده مطابقت ندارد."""

    rehash_note = (
        "\n\n⚠️ پارامترهای هش قدیمی‌اند و بهتر است بعد از ورود موفق دوباره هش شود."
        if needs_rehash
        else ""
    )
    return f"""✅ <b>تطابق تأیید شد</b>

پسورد با هش Argon2id ارسال‌شده مطابقت دارد.{rehash_note}"""
