from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from .client import TelegramReadClient
from .config import get_settings

mcp = FastMCP("Telegram MCP Bridge")
_bridge: TelegramReadClient | None = None


def bridge() -> TelegramReadClient:
    global _bridge
    if _bridge is None:
        _bridge = TelegramReadClient(get_settings())
    return _bridge


@mcp.tool()
async def telegram_list_chats(
    limit: int = 50,
    archived: bool = False,
) -> list[dict[str, Any]]:
    """List Telegram cloud chats allowed by the local access policy."""
    return await bridge().list_chats(limit=limit, archived=archived)


@mcp.tool()
async def telegram_get_messages(
    chat_id: int,
    limit: int = 50,
    before_message_id: int | None = None,
) -> list[dict[str, Any]]:
    """Read messages from one allowed chat, newest first, without marking them read."""
    return await bridge().get_messages(
        chat_id=chat_id,
        limit=limit,
        before_message_id=before_message_id,
    )


@mcp.tool()
async def telegram_search_messages(
    query: str,
    limit: int = 50,
    chat_id: int | None = None,
) -> list[dict[str, Any]]:
    """Search text globally or inside one allowed Telegram chat."""
    return await bridge().search_messages(query=query, limit=limit, chat_id=chat_id)


@mcp.tool()
async def telegram_get_message_context(
    chat_id: int,
    message_id: int,
    before: int = 10,
    after: int = 10,
) -> dict[str, Any]:
    """Read a target message together with nearby messages in chronological order."""
    return await bridge().get_message_context(
        chat_id=chat_id,
        message_id=message_id,
        before=before,
        after=after,
    )


@mcp.tool()
async def telegram_get_chat_info(chat_id: int) -> dict[str, Any]:
    """Return basic metadata for one allowed chat."""
    return await bridge().get_chat_info(chat_id)


@mcp.tool()
async def telegram_get_image(chat_id: int, message_id: int) -> Image:
    """Return a JPEG, PNG, GIF, or WebP image attached to an allowed message."""
    data, mime_type = await bridge().get_image(chat_id, message_id)
    image_format = mime_type.split("/", maxsplit=1)[1]
    return Image(data=data, format=image_format)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
