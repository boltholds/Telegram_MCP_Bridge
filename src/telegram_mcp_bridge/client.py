from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from telethon import TelegramClient

from .config import Settings
from .models import display_name, serialize_dialog, serialize_message


class TelegramReadClient:
    """Lazy, read-only facade around a Telegram user session."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.session_path.parent.mkdir(parents=True, exist_ok=True)
        self._client = TelegramClient(
            str(self.settings.session_path),
            self.settings.api_id,
            self.settings.api_hash,
        )
        self._connect_lock = asyncio.Lock()

    async def ensure_connected(self) -> TelegramClient:
        async with self._connect_lock:
            if not self._client.is_connected():
                await self._client.connect()
            if not await self._client.is_user_authorized():
                raise RuntimeError(
                    "Telegram session is not authorized. Run telegram-mcp-login first."
                )
        return self._client

    @staticmethod
    def _bounded(value: int, maximum: int, name: str = "limit") -> int:
        if value < 1:
            raise ValueError(f"{name} must be positive")
        return min(value, maximum)

    async def list_chats(self, limit: int = 50, archived: bool = False) -> list[dict[str, Any]]:
        client = await self.ensure_connected()
        limit = self._bounded(limit, self.settings.max_messages_per_request)
        folder = 1 if archived else 0
        result: list[dict[str, Any]] = []
        async for dialog in client.iter_dialogs(limit=limit, folder=folder):
            if self.settings.allows_chat(int(dialog.id)):
                result.append(serialize_dialog(dialog))
        return result

    async def get_messages(
        self,
        chat_id: int,
        limit: int = 50,
        before_message_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self.settings.require_chat(chat_id)
        client = await self.ensure_connected()
        limit = self._bounded(limit, self.settings.max_messages_per_request)
        messages: list[dict[str, Any]] = []
        async for message in client.iter_messages(
            chat_id,
            limit=limit,
            max_id=before_message_id or 0,
        ):
            messages.append(await serialize_message(message))
        return messages

    async def search_messages(
        self,
        query: str,
        limit: int = 50,
        chat_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        if chat_id is not None:
            self.settings.require_chat(chat_id)
        client = await self.ensure_connected()
        limit = self._bounded(limit, self.settings.max_search_results)
        messages: list[dict[str, Any]] = []
        async for message in client.iter_messages(chat_id, search=query, limit=limit):
            message_chat_id = int(message.chat_id) if message.chat_id is not None else None
            if message_chat_id is not None and self.settings.allows_chat(message_chat_id):
                messages.append(await serialize_message(message))
        return messages

    async def get_message_context(
        self,
        chat_id: int,
        message_id: int,
        before: int = 10,
        after: int = 10,
    ) -> dict[str, Any]:
        self.settings.require_chat(chat_id)
        before = self._bounded(before, self.settings.max_messages_per_request, "before")
        after = self._bounded(after, self.settings.max_messages_per_request, "after")
        client = await self.ensure_connected()
        target = await client.get_messages(chat_id, ids=message_id)
        if target is None:
            raise LookupError(f"Message {message_id} was not found in chat {chat_id}")

        older = [
            message
            async for message in client.iter_messages(
                chat_id, limit=before, max_id=message_id
            )
        ]
        newer = [
            message
            async for message in client.iter_messages(
                chat_id, limit=after, min_id=message_id, reverse=True
            )
        ]
        ordered = [*reversed(older), target, *newer]
        return {
            "chat_id": chat_id,
            "target_message_id": message_id,
            "messages": [await serialize_message(message) for message in ordered],
        }

    async def get_chat_info(self, chat_id: int) -> dict[str, Any]:
        self.settings.require_chat(chat_id)
        client = await self.ensure_connected()
        entity = await client.get_entity(chat_id)
        return {
            "chat_id": chat_id,
            "title": display_name(entity),
            "username": getattr(entity, "username", None),
            "type": entity.__class__.__name__,
            "participants_count": getattr(entity, "participants_count", None),
            "verified": bool(getattr(entity, "verified", False)),
            "scam": bool(getattr(entity, "scam", False)),
            "fake": bool(getattr(entity, "fake", False)),
        }


def session_file(path: Path) -> Path:
    return path if path.suffix == ".session" else path.with_suffix(".session")
