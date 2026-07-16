from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

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
        self._auth_lock = asyncio.Lock()
        self._pending_phone: str | None = None
        self._phone_code_hash: str | None = None

    async def connect(self) -> TelegramClient:
        async with self._connect_lock:
            if not self._client.is_connected():
                await self._client.connect()
        return self._client

    async def authorization_status(self) -> dict[str, Any]:
        client = await self.connect()
        authorized = await client.is_user_authorized()
        result: dict[str, Any] = {"authorized": authorized}
        if authorized:
            me = await client.get_me()
            result.update(
                id=getattr(me, "id", None),
                username=getattr(me, "username", None),
                phone=getattr(me, "phone", None),
                name=display_name(me),
            )
        return result

    async def send_login_code(self, phone: str) -> dict[str, str]:
        phone = phone.strip()
        if not phone:
            raise ValueError("Phone number is required")
        async with self._auth_lock:
            client = await self.connect()
            sent = await client.send_code_request(phone)
            self._pending_phone = phone
            self._phone_code_hash = sent.phone_code_hash
        return {"state": "code_required"}

    async def submit_login_code(self, code: str) -> dict[str, str]:
        if not self._pending_phone or not self._phone_code_hash:
            raise RuntimeError("Request a login code first")
        async with self._auth_lock:
            try:
                await self._client.sign_in(
                    phone=self._pending_phone,
                    code=code.strip(),
                    phone_code_hash=self._phone_code_hash,
                )
            except SessionPasswordNeededError:
                return {"state": "password_required"}
            self._clear_pending_login()
        return {"state": "authorized"}

    async def submit_password(self, password: str) -> dict[str, str]:
        async with self._auth_lock:
            await self._client.sign_in(password=password)
            self._clear_pending_login()
        return {"state": "authorized"}

    async def logout(self) -> dict[str, str]:
        async with self._auth_lock:
            client = await self.connect()
            await client.log_out()
            self._clear_pending_login()
        return {"state": "logged_out"}

    def _clear_pending_login(self) -> None:
        self._pending_phone = None
        self._phone_code_hash = None

    async def ensure_connected(self) -> TelegramClient:
        client = await self.connect()
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authorized. Open the local web panel or run "
                "telegram-mcp-login first."
            )
        return client

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

    async def get_image(self, chat_id: int, message_id: int) -> tuple[bytes, str]:
        """Download an image attachment into memory without persisting it."""
        self.settings.require_chat(chat_id)
        client = await self.ensure_connected()
        message = await client.get_messages(chat_id, ids=message_id)
        if message is None:
            raise LookupError(f"Message {message_id} was not found in chat {chat_id}")
        if message.media is None:
            raise ValueError(f"Message {message_id} has no media attachment")

        mime_type = getattr(message.file, "mime_type", None)
        if message.photo is not None:
            mime_type = "image/jpeg"
        if mime_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
            raise ValueError(
                f"Message {message_id} does not contain a supported image "
                f"(mime type: {mime_type or 'unknown'})"
            )

        declared_size = getattr(message.file, "size", None)
        if declared_size and declared_size > self.settings.max_media_bytes:
            raise ValueError(
                f"Image is too large ({declared_size} bytes); "
                f"limit is {self.settings.max_media_bytes} bytes"
            )

        data = await client.download_media(message, file=bytes)
        if not isinstance(data, bytes):
            raise RuntimeError("Telegram did not return image bytes")
        if len(data) > self.settings.max_media_bytes:
            raise ValueError(
                f"Image is too large ({len(data)} bytes); "
                f"limit is {self.settings.max_media_bytes} bytes"
            )
        return data, mime_type


def session_file(path: Path) -> Path:
    return path if path.suffix == ".session" else path.with_suffix(".session")
