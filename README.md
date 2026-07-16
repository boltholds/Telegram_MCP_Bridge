# Telegram MCP Bridge

> Самый простой вариант установки теперь — Docker Compose: он запускает мост,
> локальную веб-панель Telegram и официальный OpenAI `tunnel-client` sidecar.

## Установка через Docker Compose

Нужны Docker Desktop, Telegram `api_id`/`api_hash`, OpenAI Tunnel ID и Runtime API key.

1. Создайте приложение на <https://my.telegram.org> и сохраните `api_id` и `api_hash`.
2. В [OpenAI Platform → Tunnels](https://platform.openai.com/settings/organization/tunnels)
   создайте туннель и скопируйте значение вида `tunnel_...`.
3. В [OpenAI Platform → API keys](https://platform.openai.com/settings/organization/api-keys)
   создайте **Runtime API key** для туннеля. Admin key для запуска не нужен.
4. Скопируйте `.env.example` в `.env` и заполните:

```dotenv
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=use_a_long_random_password
TUNNEL_ID=tunnel_your_id
CONTROL_PLANE_API_KEY=sk-your_runtime_key
```

5. Запустите сервисы:

```powershell
docker compose up --build -d
docker compose logs -f
```

Во время сборки sidecar сам скачивает официальный `tunnel-client` `v0.0.10` для
архитектуры Docker (`amd64` или `arm64`) и проверяет SHA-256. В рантайме он читает
`TUNNEL_ID` и `CONTROL_PLANE_API_KEY` из `.env`, создаёт профиль и подключает
внутренний MCP endpoint `http://telegram-bridge:8765/mcp/`.

Откройте <http://127.0.0.1:8765>, введите `ADMIN_USERNAME`/`ADMIN_PASSWORD`, затем:

1. укажите номер Telegram в международном формате;
2. введите код, пришедший от Telegram;
3. если включена двухэтапная аутентификация, введите пароль 2FA.

Код подтверждения и пароль 2FA не сохраняются. Telegram-сессия лежит в именованном
Docker volume `telegram-session`, поэтому повторно входить после перезапуска не нужно.

Проверьте состояние:

```powershell
docker compose ps
curl http://127.0.0.1:8080/readyz
```

После этого создайте или обновите коннектор в
[ChatGPT → Настройки → Коннекторы](https://chatgpt.com/#settings/Connectors), пока оба
контейнера запущены. Внешний URL вручную придумывать не требуется: коннектор связан
с созданным Tunnel ID.

Остановка и обновление:

```powershell
docker compose down
docker compose pull
docker compose up --build -d
```

Не используйте `docker compose down -v`, если хотите сохранить Telegram-сессию.
Файл `.env` уже исключён из Git; никогда не коммитьте Runtime API key или session-файлы.

### Настройки Docker

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `TUNNEL_ID` | ID Secure MCP Tunnel | обязательна |
| `CONTROL_PLANE_API_KEY` | Runtime API key | обязательна |
| `ADMIN_USERNAME` | логин веб-панели | `admin` |
| `ADMIN_PASSWORD` | пароль веб-панели | обязательна для панели |
| `WEB_PANEL_PORT` | локальный порт панели/MCP | `8765` |
| `TUNNEL_HEALTH_PORT` | локальный health-порт tunnel-client | `8080` |
| `TUNNEL_CLIENT_VERSION` | закреплённая версия образа | `0.0.10` |

Порты публикуются только на `127.0.0.1`. Не выставляйте веб-панель напрямую в
интернет. Для production предпочтительнее Docker secrets вместо `.env`.

### Диагностика Docker

#### `exec /usr/local/bin/tunnel-entrypoint: no such file or directory`

На Windows эта ошибка обычно означает, что shell-скрипт попал в образ с окончаниями
строк CRLF, и Linux пытается найти интерпретатор с именем `/bin/sh\r`. Это не означает,
что сам файл действительно отсутствует.

В актуальной версии проекта проблема исправлена двумя уровнями защиты:

- `.gitattributes` сохраняет все `*.sh` с окончаниями LF;
- Dockerfile дополнительно удаляет `CR` при сборке образа.

Получите исправление и полностью пересоберите только tunnel-контейнер:

```powershell
git pull
docker compose down
docker compose build --no-cache tunnel-client
docker compose up -d
docker compose logs -f tunnel-client
```

Удалять volumes не требуется: авторизованная Telegram-сессия останется на месте.
Не запускайте `docker compose down -v`, иначе volume с сессией будет удалён.

#### Проверка состояния

```powershell
docker compose ps
docker compose logs --tail=100 telegram-bridge
docker compose logs --tail=100 tunnel-client
curl.exe http://127.0.0.1:8765/readyz
curl.exe http://127.0.0.1:8080/readyz
```

Оба контейнера должны иметь состояние `running`/`healthy`. В логах моста ожидаются
`Application startup complete` и `StreamableHTTP session manager started`. В логах
туннеля не должно быть циклического перезапуска или ошибок `401 Unauthorized`.

#### `401 Unauthorized` от control plane

Проверьте, что `CONTROL_PLANE_API_KEY` является именно Runtime API key, а не Admin
key, и что ключ и `TUNNEL_ID` созданы в одной OpenAI Platform organization. После
изменения `.env` пересоздайте контейнер:

```powershell
docker compose up -d --force-recreate tunnel-client
docker compose logs -f tunnel-client
```

#### Веб-панель возвращает `401 Unauthorized`

Это ожидаемый HTTP Basic challenge. Браузер должен показать окно входа — используйте
`ADMIN_USERNAME` и `ADMIN_PASSWORD` из `.env`. Запись `GET / 401` перед последующим
`GET / 200` в логах означает нормальный успешный вход.

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
