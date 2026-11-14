from hash_bot import keyboards, texts


def test_main_menu_exposes_all_primary_tools() -> None:
    callbacks = {
        button.callback_data for row in keyboards.main_menu().inline_keyboard for button in row
    }
    assert callbacks == {
        keyboards.ARGON,
        keyboards.SHA256,
        keyboards.VERIFY,
        keyboards.SECURITY,
        keyboards.STATUS,
    }


def test_result_keyboard_contains_copy_payload() -> None:
    markup = keyboards.result_actions("digest-value", again_callback=keyboards.ARGON)
    copy_button = markup.inline_keyboard[0][0]
    assert copy_button.copy_text is not None
    assert copy_button.copy_text.text == "digest-value"


def test_status_card_reflects_runtime_settings() -> None:
    card = texts.status_text(allowed_users=2, delete_enabled=True, max_length=4096)
    assert "2" in card
    assert "فعال" in card
    assert "4096" in card
