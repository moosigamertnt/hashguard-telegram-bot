import pytest

from hash_bot.config import (
    ConfigError,
    parse_bool,
    parse_max_input_length,
    parse_user_ids,
)


def test_empty_allowlist_is_locked() -> None:
    assert parse_user_ids("") == frozenset()


def test_parse_multiple_ids_and_remove_duplicates() -> None:
    assert parse_user_ids("123, 456,123") == frozenset({123, 456})


@pytest.mark.parametrize("value", ["abc", "12,x", "-1", "0"])
def test_invalid_user_ids_are_rejected(value: str) -> None:
    with pytest.raises(ConfigError):
        parse_user_ids(value)


@pytest.mark.parametrize("value", ["true", "YES", "1", "on"])
def test_parse_bool_accepts_truthy_values(value: str) -> None:
    assert parse_bool(value, name="OPTION") is True


@pytest.mark.parametrize("value", ["false", "NO", "0", "off"])
def test_parse_bool_accepts_falsy_values(value: str) -> None:
    assert parse_bool(value, name="OPTION") is False


def test_parse_bool_rejects_unknown_value() -> None:
    with pytest.raises(ConfigError):
        parse_bool("maybe", name="OPTION")


@pytest.mark.parametrize("value", ["0", "4097", "not-a-number"])
def test_max_input_length_is_bounded(value: str) -> None:
    with pytest.raises(ConfigError):
        parse_max_input_length(value)
