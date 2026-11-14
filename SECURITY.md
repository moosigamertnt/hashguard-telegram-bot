# Security policy

HashGuard is a developer utility, not a password manager. Telegram messages pass through
Telegram's infrastructure before the bot can delete them. Do not send production credentials,
recovery codes, private keys, or other high-value secrets to this bot.

## Safe deployment

- Keep `.env` out of version control.
- Restrict access with `ALLOWED_USER_IDS`.
- Keep `DELETE_INPUT_MESSAGES=true`.
- Disable group access for the bot through BotFather.
- Rotate the bot token immediately if it is exposed.
- Hash production passwords inside the application backend, close to the authentication flow.

## Reporting a vulnerability

Please open a private GitHub security advisory instead of a public issue. Include the affected
version, reproduction steps, and impact. Do not include real credentials or personal data.

