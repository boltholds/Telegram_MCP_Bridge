import pytest

from telegram_mcp_bridge.client import TelegramReadClient


def test_bounded_caps_limit() -> None:
    assert TelegramReadClient._bounded(250, 100) == 100


def test_bounded_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        TelegramReadClient._bounded(0, 100)
