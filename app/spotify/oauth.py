import base64
import time
import requests
import asyncio
from urllib.parse import quote
from aiohttp import web
from aiogram import Bot
from typing import Callable, Optional, Dict, Any
try:
    from app.config import load_config
except Exception:
    load_config = None
try:
    from app.storage import memory as storage
except Exception:
    try:
        import app.storage.memory as storage  # type: ignore
    except Exception:
        storage = None  # type: ignore

_LOCAL_STORE: Dict[str, Dict[str, Any]] = {}

_on_token_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None


def set_token_callback(func: Callable[[str, Dict[str, Any]], None]) -> None:
    """Register callback to persist token data. Signature: func(telegram_id, token_dict)."""
    global _on_token_callback
    _on_token_callback = func


def _store_token_local(tg: str, token_data: Dict[str, Any]) -> None:
    """Default local store: put token into storage.USER_SPOTIFY if available, else local dict."""
    token_data = dict(token_data)
    if "expires_at" not in token_data and token_data.get("expires_in"):
        token_data["expires_at"] = int(time.time()) + int(token_data.get("expires_in", 3600))
    if storage is not None and hasattr(storage, "USER_SPOTIFY"):
        storage.USER_SPOTIFY[str(tg)] = token_data
    else:
        _LOCAL_STORE[str(tg)] = token_data


if _on_token_callback is None:
    set_token_callback(_store_token_local)


def save_token(tg_user_id: str, token_data: Dict[str, Any]) -> None:
    """Synchronous save to storage (and call callback)."""
    tg = str(tg_user_id)
    _store_token_local(tg, token_data)
    if _on_token_callback:
        try:
            _on_token_callback(tg, token_data)
        except Exception:
            pass


def get_token(tg_user_id: str) -> Optional[Dict[str, Any]]:
    tg = str(tg_user_id)
    if storage is not None and hasattr(storage, "USER_SPOTIFY"):
        return storage.USER_SPOTIFY.get(tg)
    return _LOCAL_STORE.get(tg)


def _load_config_or_raise():
    if load_config is None:
        raise RuntimeError("Config loader not available (app.config.load_config). Ensure app/config exists.")
    return load_config()


def _basic_auth_header(cfg) -> Dict[str, str]:
    s = f"{cfg.spotify.client_id}:{cfg.spotify.client_secret}"
    token = base64.b64encode(s.encode()).decode()
    return {"Authorization": f"Basic {token}"}


def get_auth_url(telegram_user_id: str) -> str:
    cfg = _load_config_or_raise()
    redirect = quote(cfg.spotify.redirect_uri, safe="")
    scope = quote(cfg.spotify.scopes, safe="")
    return (
        "https://accounts.spotify.com/authorize"
        f"?client_id={cfg.spotify.client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect}"
        f"&scope={scope}"
        f"&state={telegram_user_id}"
        f"&show_dialog=true"
    )


def exchange_code(code: str) -> Dict[str, Any]:
    cfg = _load_config_or_raise()
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={**_basic_auth_header(cfg), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": cfg.spotify.redirect_uri},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    data["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
    return data


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    cfg = _load_config_or_raise()
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={**_basic_auth_header(cfg), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    data["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
    return data


async def _callback(request: web.Request) -> web.Response:
    cfg = request.app.get("config")
    if cfg is None:
        cfg = _load_config_or_raise()

    params = request.rel_url.query
    code = params.get("code")
    telegram_user_id = params.get("state")
    if not code or not telegram_user_id:
        return web.Response(text="Missing code or state", status=400)

    try:
        token = await asyncio.to_thread(exchange_code, code)

        access_token = token.get("access_token")
        refresh_token = token.get("refresh_token")
        expires_at = token.get("expires_at")

        r = requests.get("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        r.raise_for_status()
        me = r.json()
        spotify_user_id = me.get("id")

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "spotify_user_id": spotify_user_id,
            "scope": token.get("scope"),
            "expires_in": token.get("expires_in"),
            "expires_at": expires_at,
        }

        if _on_token_callback:
            try:
                _on_token_callback(str(telegram_user_id), token_data)
            except Exception:
                pass

        try:
            if cfg and getattr(cfg, "telegram", None) and getattr(cfg.telegram, "token", None):
                async with Bot(token=cfg.telegram.token) as bot:
                    try:
                        await bot.send_message(int(telegram_user_id), "✅ Spotify успешно подключён. Вернись в бота.")
                    except Exception:
                        pass
        except Exception:
            pass

        return web.Response(text="✅ Spotify connected. You can return to the bot.")
    except Exception as exc:
        return web.Response(text=f"OAuth error: {exc}", status=500)


async def start_oauth_server(host: Optional[str] = None, port: Optional[int] = None):
    cfg = _load_config_or_raise()
    host = host or cfg.oauth.host
    port = int(port or cfg.oauth.port)

    app = web.Application()
    app["config"] = cfg
    app.router.add_get("/callback", _callback)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"✅ Spotify OAuth server running on http://{host}:{port}/callback")


async def ensure_token(tg_user_id: str) -> str:
    tg = str(tg_user_id)
    token = get_token(tg)
    if not token:
        raise RuntimeError("Spotify not connected")

    now = time.time()
    if now > token.get("expires_at", 0) - 30:
        refresh = token.get("refresh_token")
        if not refresh:
            raise RuntimeError("No refresh_token, reauthorize")

        new = await asyncio.to_thread(refresh_access_token, refresh)
        token["access_token"] = new.get("access_token")
        token["expires_at"] = new.get("expires_at", int(time.time()) + int(new.get("expires_in", 3600)))
        if new.get("refresh_token"):
            token["refresh_token"] = new.get("refresh_token")

        save_token(tg, token)

    return token["access_token"]


def get_token_sync(tg_user_id: str) -> Optional[Dict[str, Any]]:
    return get_token(tg_user_id)


__all__ = [
    "get_auth_url",
    "exchange_code",
    "refresh_access_token",
    "start_oauth_server",
    "set_token_callback",
    "ensure_token",
    "save_token",
    "get_token_sync",
]
