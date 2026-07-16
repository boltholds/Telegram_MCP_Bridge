from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from .config import get_settings
from .server import bridge, mcp

security = HTTPBasic(auto_error=False)


def require_admin(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> str:
    settings = get_settings()
    if not settings.admin_password:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Set ADMIN_PASSWORD before using the web panel",
        )
    valid = credentials is not None and secrets.compare_digest(
        credentials.username.encode(), settings.admin_username.encode()
    ) and secrets.compare_digest(
        credentials.password.encode(), settings.admin_password.encode()
    )
    if not valid:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return settings.admin_username


class PhoneRequest(BaseModel):
    phone: str


class CodeRequest(BaseModel):
    code: str


class PasswordRequest(BaseModel):
    password: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Telegram MCP Bridge", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def ready() -> dict[str, str]:
    get_settings()
    return {"status": "ready"}


@app.get("/api/status", dependencies=[Depends(require_admin)])
async def telegram_status() -> dict[str, Any]:
    return await bridge().authorization_status()


@app.post("/api/auth/phone", dependencies=[Depends(require_admin)])
async def request_code(payload: PhoneRequest) -> dict[str, str]:
    return await bridge().send_login_code(payload.phone)


@app.post("/api/auth/code", dependencies=[Depends(require_admin)])
async def submit_code(payload: CodeRequest) -> dict[str, str]:
    return await bridge().submit_login_code(payload.code)


@app.post("/api/auth/password", dependencies=[Depends(require_admin)])
async def submit_password(payload: PasswordRequest) -> dict[str, str]:
    return await bridge().submit_password(payload.password)


@app.post("/api/auth/logout", dependencies=[Depends(require_admin)])
async def logout() -> dict[str, str]:
    return await bridge().logout()


@app.exception_handler(Exception)
async def api_error(request: Request, exc: Exception):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": str(exc)}, status_code=400)
    raise exc


PANEL = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Telegram MCP Bridge</title><style>
body{font:16px system-ui;background:#10131a;color:#eef2ff;max-width:760px;margin:40px auto;padding:0 20px}
.card{background:#1b2130;border:1px solid #303a50;border-radius:14px;padding:22px;margin:16px 0}
input,button{font:inherit;padding:11px;border-radius:8px;border:1px solid #526079;margin:5px}
input{background:#111725;color:white}button{cursor:pointer;background:#2aabee;color:#071018;font-weight:700}
.danger{background:#e45b65}code{color:#8bd5ff}#message{white-space:pre-wrap;color:#ffd580}
</style></head><body><h1>Telegram MCP Bridge</h1>
<div class="card"><h2>Статус</h2><div id="status">Проверяю…</div></div>
<div class="card"><h2>1. Получить код</h2><input id="phone" placeholder="+79991234567"><button onclick="sendPhone()">Отправить код</button></div>
<div class="card"><h2>2. Ввести код</h2><input id="code" autocomplete="one-time-code" placeholder="12345"><button onclick="sendCode()">Войти</button></div>
<div class="card"><h2>3. Если включена 2FA</h2><input id="password" type="password" autocomplete="current-password" placeholder="Пароль 2FA"><button onclick="sendPassword()">Подтвердить</button></div>
<div class="card"><button class="danger" onclick="logout()">Выйти из Telegram</button><p id="message"></p></div>
<p>MCP endpoint: <code>/mcp</code>. Код и пароль существуют только во время запроса и не записываются.</p>
<script>
const msg=document.querySelector('#message');
async function call(path,body){msg.textContent='';const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw Error(j.detail||r.statusText);msg.textContent=JSON.stringify(j);await load();}
async function load(){try{const r=await fetch('/api/status');const j=await r.json();document.querySelector('#status').textContent=j.authorized?`Авторизован: ${j.name||''} @${j.username||''} (${j.id})`:'Не авторизован';}catch(e){msg.textContent=e.message}}
function sendPhone(){call('/api/auth/phone',{phone:phone.value}).catch(e=>msg.textContent=e.message)}
function sendCode(){call('/api/auth/code',{code:code.value}).catch(e=>msg.textContent=e.message)}
function sendPassword(){call('/api/auth/password',{password:password.value}).catch(e=>msg.textContent=e.message)}
function logout(){call('/api/auth/logout').catch(e=>msg.textContent=e.message)}load();
</script></body></html>"""


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def panel() -> str:
    return PANEL


app.mount("/mcp", mcp.streamable_http_app())


def main() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.web_host, port=settings.web_port)


if __name__ == "__main__":
    main()
