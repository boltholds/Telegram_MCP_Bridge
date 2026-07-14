from __future__ import annotations

from datetime import datetime
from typing import Any


def iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def display_name(entity: Any) -> str | None:
    if entity is None:
        return None
    title = getattr(entity, "title", None)
    if title:
        return str(title)
    parts = [
        getattr(entity, "first_name", None),
        getattr(entity, "last_name", None),
    ]
    name = " ".join(str(part) for part in parts if part)
    return name or getattr(entity, "username", None)


def serialize_dialog(dialog: Any) -> dict[str, Any]:
    return {
        "chat_id": int(dialog.id),
        "title": dialog.name or display_name(dialog.entity),
        "unread_count": int(dialog.unread_count or 0),
        "is_user": bool(dialog.is_user),
        "is_group": bool(dialog.is_group),
        "is_channel": bool(dialog.is_channel),
        "pinned": bool(dialog.pinned),
        "archived": bool(dialog.archived),
    }


async def serialize_message(message: Any) -> dict[str, Any]:
    sender = await message.get_sender()
    reply_to_message_id = None
    if message.reply_to:
        reply_to_message_id = getattr(message.reply_to, "reply_to_msg_id", None)
    return {
        "message_id": int(message.id),
        "chat_id": int(message.chat_id) if message.chat_id is not None else None,
        "date": iso_datetime(message.date),
        "edit_date": iso_datetime(message.edit_date),
        "sender_id": int(message.sender_id) if message.sender_id is not None else None,
        "sender_name": display_name(sender),
        "text": message.raw_text or "",
        "outgoing": bool(message.out),
        "reply_to_message_id": reply_to_message_id,
        "has_media": message.media is not None,
    }
