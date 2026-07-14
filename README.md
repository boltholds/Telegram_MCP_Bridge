# Telegram MCP Bridge

A local, read-only MCP bridge for accessing your own Telegram account through a user session. It uses [Telethon](https://docs.telethon.dev/) (MTProto), not the Telegram Bot API.

## Current tools

- `telegram_list_chats`
- `telegram_get_messages`
- `telegram_search_messages`
- `telegram_get_message_context`
- `telegram_get_chat_info`

The first version cannot send, edit, delete, forward, or mark messages as read.

## Requirements

- Python 3.11+
- Telegram `api_id` and `api_hash` from <https://my.telegram.org>
- An MCP host that supports stdio servers

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env
```

Fill in `.env`, then create the Telegram user session interactively:

```bash
telegram-mcp-login
```

Start the MCP server:

```bash
telegram-mcp
```

Example MCP configuration:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "/absolute/path/to/.venv/bin/telegram-mcp",
      "env": {
        "TELEGRAM_API_ID": "123456",
        "TELEGRAM_API_HASH": "replace_me",
        "TELEGRAM_SESSION_PATH": "/absolute/path/to/private/telegram_mcp"
      }
    }
  }
}
```

On Windows, point `command` to `.venv\\Scripts\\telegram-mcp.exe`.

## Access policy

Set `TELEGRAM_ALLOWED_CHAT_IDS` to a comma-separated allowlist. When it is empty, all ordinary cloud chats visible to the account are accessible. For safer use, begin with one or two chat IDs returned by `telegram_list_chats`.

Limits are controlled with:

- `TELEGRAM_MAX_MESSAGES_PER_REQUEST` (default: 100)
- `TELEGRAM_MAX_SEARCH_RESULTS` (default: 100)

Media is not downloaded in this version.

## Security

The `.session` file grants access to the Telegram account. Never commit or share it. Keep the bridge local, use an allowlist, and review every MCP host that can invoke it.
