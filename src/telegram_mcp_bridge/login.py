from __future__ import annotations

from telethon.sync import TelegramClient

from .config import get_settings


def main() -> None:
    settings = get_settings()
    settings.session_path.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(
        str(settings.session_path),
        settings.api_id,
        settings.api_hash,
    )
    try:
        client.start(phone=settings.phone)
        me = client.get_me()
        username = f"@{me.username}" if me.username else str(me.id)
        print(f"Authorized Telegram session for {username}")
        print(f"Session stored at {settings.session_path.with_suffix('.session')}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
