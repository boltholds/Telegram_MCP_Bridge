from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def _chat_ids(raw: str | None) -> frozenset[int]:
    if not raw:
        return frozenset()
    try:
        return frozenset(int(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError("TELEGRAM_ALLOWED_CHAT_IDS must contain comma-separated integers") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    api_id: int
    api_hash: str
    phone: str | None
    session_path: Path
    allowed_chat_ids: frozenset[int]
    max_messages_per_request: int
    max_search_results: int
    max_media_bytes: int
    web_host: str = "127.0.0.1"
    web_port: int = 8765
    admin_username: str = "admin"
    admin_password: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        api_id_raw = os.getenv("TELEGRAM_API_ID", "").strip()
        api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
        if not api_id_raw or not api_hash:
            raise RuntimeError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH are required. "
                "Create them at https://my.telegram.org"
            )
        try:
            api_id = int(api_id_raw)
        except ValueError as exc:
            raise ValueError("TELEGRAM_API_ID must be an integer") from exc

        session_path = Path(
            os.getenv("TELEGRAM_SESSION_PATH", "./sessions/telegram_mcp")
        ).expanduser()
        return cls(
            api_id=api_id,
            api_hash=api_hash,
            phone=os.getenv("TELEGRAM_PHONE") or None,
            session_path=session_path,
            allowed_chat_ids=_chat_ids(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS")),
            max_messages_per_request=_positive_int(
                "TELEGRAM_MAX_MESSAGES_PER_REQUEST", 100
            ),
            max_search_results=_positive_int("TELEGRAM_MAX_SEARCH_RESULTS", 100),
            max_media_bytes=_positive_int("TELEGRAM_MAX_MEDIA_BYTES", 10 * 1024 * 1024),
            web_host=os.getenv("WEB_HOST", "127.0.0.1"),
            web_port=_positive_int("WEB_PORT", 8765),
            admin_username=os.getenv("ADMIN_USERNAME", "admin"),
            admin_password=os.getenv("ADMIN_PASSWORD", "").strip(),
        )

    def allows_chat(self, chat_id: int) -> bool:
        return not self.allowed_chat_ids or chat_id in self.allowed_chat_ids

    def require_chat(self, chat_id: int) -> None:
        if not self.allows_chat(chat_id):
            raise PermissionError(
                f"Chat {chat_id} is not included in TELEGRAM_ALLOWED_CHAT_IDS"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
