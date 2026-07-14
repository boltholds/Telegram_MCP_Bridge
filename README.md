# Telegram MCP Bridge

A local, read-only MCP bridge for accessing your own Telegram account through a user session. It uses [Telethon](https://docs.telethon.dev/) (MTProto), not the Telegram Bot API.

## Current tools

- `telegram_list_chats`
- `telegram_get_messages`
- `telegram_search_messages`
- `telegram_get_message_context`
- `telegram_get_chat_info`
- `telegram_get_image`

The first version cannot send, edit, delete, forward, or mark messages as read.

## Requirements

- Python 3.11+
- Poetry
- Telegram `api_id` and `api_hash` from <https://my.telegram.org>
- An OpenAI Platform organization with Secure MCP Tunnel access
- ChatGPT developer mode / custom plugins enabled
- `tunnel-client.exe` for Windows

## Windows installation with Poetry

Clone and install the project:

```cmd
cd C:\Users\YOUR_USER\Documents\Code
git clone https://github.com/boltholds/Telegram_MCP_Bridge.git
cd Telegram_MCP_Bridge
poetry install
```

Create the local configuration:

```cmd
copy .env.example .env
notepad .env
```

### Telegram API credentials

1. Sign in at <https://my.telegram.org>.
2. Open **API development tools**.
3. Create an application and copy its `api_id` and `api_hash`.
4. Fill in `.env`:

```dotenv
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=replace_me
TELEGRAM_PHONE=+79990000000
TELEGRAM_SESSION_PATH=./sessions/telegram_mcp
TELEGRAM_ALLOWED_CHAT_IDS=
TELEGRAM_MAX_MESSAGES_PER_REQUEST=100
TELEGRAM_MAX_SEARCH_RESULTS=100
TELEGRAM_MAX_MEDIA_BYTES=10485760
```

Authorize the Telegram user session:

```cmd
poetry run telegram-mcp-login
```

Telegram sends the code to an already authorized Telegram client. Enter the 2FA
password when requested. A successful login creates
`sessions/telegram_mcp.session`; this file grants access to the account and must
never be shared or committed.

Test the stdio MCP server:

```cmd
poetry run telegram-mcp
```

The command normally stays silent and waits for MCP requests. Stop it with
`Ctrl+C`.

## Connect ChatGPT through Secure MCP Tunnel

ChatGPT cannot invoke a local stdio process directly from a cloud conversation.
[Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
runs next to the bridge and opens an outbound-only HTTPS connection to OpenAI.
The Telegram MCP server remains local and does not require an inbound port.

### 1. Create a tunnel and copy its ID

1. Open [OpenAI Platform tunnel settings](https://platform.openai.com/settings/organization/tunnels).
2. Select the same Platform organization used by the target ChatGPT account.
3. Create a tunnel, for example `telegram-mcp`.
4. Associate it with the target personal ChatGPT workspace (or the required
   Business/Enterprise workspace).
5. Copy the tunnel ID, which looks like `tunnel_...`.

The account needs `Tunnels Read + Use` to run and select a tunnel. Creating or
editing one additionally requires `Tunnels Read + Manage`.

### 2. Create the runtime API key

Create a runtime key at
[Platform organization API keys](https://platform.openai.com/settings/organization/api-keys).
The key and tunnel must belong to the same Platform organization. Do not use an
Admin API key and never put the key into the repository or `.env`.

Set it only in the current `cmd.exe` window:

```cmd
set "CONTROL_PLANE_API_KEY=sk-REPLACE_ME"
```

Verify that the variable exists without printing the secret:

```cmd
if defined CONTROL_PLANE_API_KEY (echo API key is set) else (echo API key is missing)
```

The variable disappears when the terminal closes. Set it again before future
`doctor` or `run` commands, or provide it through an appropriate local secret
manager.

### 3. Install tunnel-client.exe

Download the Windows tunnel client using the instructions in the
[Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
and place it somewhere local, for example:

```text
C:\Users\YOUR_USER\Downloads\tunnel-client.exe
```

Check the binary:

```cmd
C:\Users\YOUR_USER\Downloads\tunnel-client.exe --version
C:\Users\YOUR_USER\Downloads\tunnel-client.exe --help
```

### 4. Find the Poetry Python executable

From the repository directory, run:

```cmd
poetry env info --path
```

For example:

```text
C:\Users\YOUR_USER\AppData\Local\pypoetry\Cache\virtualenvs\telegram-mcp-bridge-xxxx-py3.13
```

The Python executable is therefore:

```text
C:/Users/YOUR_USER/AppData/Local/pypoetry/Cache/virtualenvs/telegram-mcp-bridge-xxxx-py3.13/Scripts/python.exe
```

Use forward slashes inside the tunnel profile command. Backslashes may be
treated as escape characters and produce a broken path such as
`C:UsersYOUR_USER...`.

Verify the module before creating the profile:

```cmd
C:/Users/YOUR_USER/AppData/Local/pypoetry/Cache/virtualenvs/telegram-mcp-bridge-xxxx-py3.13/Scripts/python.exe -c "import telegram_mcp_bridge; print('OK')"
```

### 5. Create the tunnel-client profile

Run from the repository directory so the child MCP process can find `.env`:

```cmd
cd C:\Users\YOUR_USER\Documents\Code\Telegram_MCP_Bridge
C:\Users\YOUR_USER\Downloads\tunnel-client.exe init --profile telegram-mcp --tunnel-id tunnel_REPLACE_ME --mcp-command "C:/Users/YOUR_USER/AppData/Local/pypoetry/Cache/virtualenvs/telegram-mcp-bridge-xxxx-py3.13/Scripts/python.exe -m telegram_mcp_bridge.server" --open-web-ui
```

Use one pair of double quotes around the complete `--mcp-command`. Unix single
quotes (`'''...'''`) do not group arguments in Windows `cmd.exe`. If a broken
profile already exists, add `--force`:

```cmd
C:\Users\YOUR_USER\Downloads\tunnel-client.exe init --force --profile telegram-mcp --tunnel-id tunnel_REPLACE_ME --mcp-command "C:/Users/YOUR_USER/AppData/Local/pypoetry/Cache/virtualenvs/telegram-mcp-bridge-xxxx-py3.13/Scripts/python.exe -m telegram_mcp_bridge.server" --open-web-ui
```

Profiles are normally stored at:

```text
C:\Users\YOUR_USER\AppData\Roaming\tunnel-client\telegram-mcp.yaml
```

### 6. Diagnose and run the tunnel

In the same terminal containing `CONTROL_PLANE_API_KEY`:

```cmd
cd C:\Users\YOUR_USER\Documents\Code\Telegram_MCP_Bridge
C:\Users\YOUR_USER\Downloads\tunnel-client.exe doctor --profile telegram-mcp
C:\Users\YOUR_USER\Downloads\tunnel-client.exe run --profile telegram-mcp
```

Keep `run` open for connector discovery and every later MCP call. With
`--open-web-ui`, the local admin UI opens automatically. A healthy setup shows
the `main` channel as `enabled`, server `external`, and transport `stdio`.

### 7. Create the ChatGPT plugin

While `tunnel-client run` is active:

1. Open **ChatGPT Settings -> Plugins -> New plugin**.
2. Enter a name such as `Telegram MCP Bridge`.
3. Select **Tunnel**, not **Server URL**.
4. Select the tunnel ID created above.
5. No separate OAuth configuration is required by this local bridge.
6. Confirm the custom MCP warning and create the plugin.
7. Start a new chat with the plugin enabled and ask it to list Telegram chats.

When the MCP tool schema changes, update/reconnect the plugin and start a new
conversation. Existing conversations may retain the older tool list.

## Update and restart

```cmd
cd C:\Users\YOUR_USER\Documents\Code\Telegram_MCP_Bridge
git pull
poetry install
```

Stop the running tunnel with `Ctrl+C`, set `CONTROL_PLANE_API_KEY` in the new
terminal, and run it again:

```cmd
set "CONTROL_PLANE_API_KEY=sk-REPLACE_ME"
cd C:\Users\YOUR_USER\Documents\Code\Telegram_MCP_Bridge
C:\Users\YOUR_USER\Downloads\tunnel-client.exe run --profile telegram-mcp
```

## Troubleshooting

### `401 Unauthorized` in tunnel-client logs

The control-plane key is missing, invalid, revoked, or belongs to a different
Platform organization. Stop the daemon, set a valid runtime key in the same
`cmd.exe` window, and restart it. Confirm the tunnel and key belong to the same
organization and the account has `Tunnels Read + Use`.

### `unknown shorthand flag: 'm' in -m`

The MCP command was not enclosed in Windows double quotes. Use:

```cmd
--mcp-command "C:/absolute/path/to/python.exe -m telegram_mcp_bridge.server"
```

### Executable path becomes `C:Users...`

Backslashes were consumed as escapes. Recreate the profile with `--force` and
forward slashes in `--mcp-command`.

### `Telegram session is not authorized`

Stop the tunnel, authorize from the repository, then restart it:

```cmd
cd C:\Users\YOUR_USER\Documents\Code\Telegram_MCP_Bridge
poetry run telegram-mcp-login
```

### Connector creation returns `Something went wrong`

Keep the tunnel daemon running and inspect its local **Logs** page while trying
again. If no connector request reaches the daemon, verify the tunnel-to-ChatGPT
workspace association. If a request arrives and fails, run `doctor` and inspect
the MCP subprocess error.

## Generic stdio MCP configuration

For a local MCP host that supports direct stdio processes, start the server with:

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

`telegram_get_image` returns JPEG, PNG, GIF, and WebP attachments directly as MCP
image content. Downloads stay in memory and are capped by
`TELEGRAM_MAX_MEDIA_BYTES` (default: 10 MiB).

## Security

The `.session` file grants access to the Telegram account. Never commit or share it. Keep the bridge local, use an allowlist, and review every MCP host that can invoke it.
