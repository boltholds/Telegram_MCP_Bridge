from pathlib import Path

import pytest

from telegram_mcp_bridge.config import Settings, _chat_ids


def test_chat_ids_parses_allowlist() -> None:
    assert _chat_ids("10, -10020, 30") == frozenset({10, -10020, 30})


def test_chat_ids_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="comma-separated integers"):
        _chat_ids("10,not-an-id")


def test_settings_enforces_allowlist() -> None:
    settings = Settings(
        api_id=1,
        api_hash="hash",
        phone=None,
        session_path=Path("test"),
        allowed_chat_ids=frozenset({42}),
        max_messages_per_request=100,
        max_search_results=100,
    )

    settings.require_chat(42)
    with pytest.raises(PermissionError):
        settings.require_chat(43)


def test_empty_allowlist_allows_any_chat() -> None:
    settings = Settings(
        api_id=1,
        api_hash="hash",
        phone=None,
        session_path=Path("test"),
        allowed_chat_ids=frozenset(),
        max_messages_per_request=100,
        max_search_results=100,
    )

    assert settings.allows_chat(-100123)
