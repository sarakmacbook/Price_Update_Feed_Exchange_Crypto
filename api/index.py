"""Vercel entry point for the P2P price bot.

Vercel runs serverless functions, so the bot works here in **webhook** mode
instead of long polling:

======================  =======================================================
``POST /api/telegram``  Telegram webhook → ``Application.process_update``
``GET  /api/cron``      scheduler tick: auto-post prices + housekeeping.
                        Point Vercel Cron (Pro) or any external pinger here
``GET  /api/setup``     registers the webhook with Telegram (run it once after
                        deploying / after changing the domain)
``GET  /api/health``    JSON status — pair, storage backend, group, merchants
``GET  /``              small status page (open it right after deploying)
======================  =======================================================

Auth: ``/api/cron`` and ``/api/setup`` require the secret from the
``CRON_SECRET`` env var (falls back to ``BOT_TOKEN`` when it is not set),
either as ``?key=…`` or as an ``Authorization: Bearer …`` header — which is
exactly what Vercel Cron sends.

Required environment variables: ``BOT_TOKEN``, ``ADMIN_IDS``.
Recommended: ``KV_REST_API_URL`` + ``KV_REST_API_TOKEN`` (Vercel KV / Upstash)
so state survives cold starts, ``CRON_SECRET``, ``WEBHOOK_SECRET``.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import time
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# a single event loop per function instance: httpx connections (Telegram API)
# stay usable across warm invocations
try:
    _LOOP = asyncio.get_event_loop_policy().get_event_loop()
    if _LOOP.is_closed():
        raise RuntimeError("closed")
except Exception:                                                 # pragma: no cover
    _LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)

_bot_module = None
_bot_error = None
_app = None


def get_bot():
    """Import the bot module lazily so the status page also works when the
    environment (BOT_TOKEN / ADMIN_IDS) is not configured yet."""
    global _bot_module, _bot_error
    if _bot_module is None and _bot_error is None:
        try:
            import bot as _b
            _bot_module = _b
        except (Exception, SystemExit) as e:   # SystemExit: bot.py calls sys.exit()
            _bot_error = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            traceback.print_exc()
    return _bot_module


def run_async(coro):
    return _LOOP.run_until_complete(coro)


async def ensure_app(bot):
    """Initialise the PTB Application once per function instance."""
    global _app
    if _app is None:
        _app = bot.build_application(webhook=True)
        await _app.initialize()
        try:
            me = await _app.bot.get_me()
            bot.BOT_USERNAME = me.username
        except Exception:                                         # pragma: no cover
            pass
    return _app


# ── routes ──────────────────────────────────────────────────────────────────
def route_for(path: str) -> str:
    """Route by suffix so it works no matter how Vercel rewrites the path
    (``/api/telegram``, ``/telegram`` or ``/api/index.py``)."""
    p = (path or "/").split("?")[0].rstrip("/").lower()
    for name in ("telegram", "cron", "setup", "health"):
        if p.endswith("/" + name) or p == "/" + name:
            return name
    return "root"


def secret_value() -> str:
    return (os.getenv("CRON_SECRET") or os.getenv("BOT_TOKEN") or "").strip()


def authorized(query: dict, headers) -> bool:
    """?key=…, x-cron-secret: … or `Authorization: Bearer …` (what Vercel Cron sends)."""
    expected = secret_value()
    if not expected:
        return False
    provided = query.get("key", [""])[0] or header(headers, "x-cron-secret")
    auth = header(headers, "authorization")
    if not provided and auth.lower().startswith("bearer "):
        provided = auth[7:].strip()
    return bool(provided) and hmac.compare_digest(provided, expected)


def header(headers, name: str, default: str = "") -> str:
    return headers.get(name) or headers.get(name.title()) or default


# ── async handlers ──────────────────────────────────────────────────────────
async def handle_update(bot, payload: dict) -> None:
    from telegram import Update
    app = await ensure_app(bot)
    bot.reload_state()
    update = Update.de_json(payload, app.bot)
    if update is not None:
        await app.process_update(update)


async def handle_cron(bot, force: bool) -> dict:
    app = await ensure_app(bot)
    return await bot.run_scheduled(app.bot, force=force)


async def handle_setup(bot, base_url: str) -> dict:
    app = await ensure_app(bot)
    webhook_secret = (os.getenv("WEBHOOK_SECRET") or "").strip() or None
    url = f"{base_url.rstrip('/')}/api/telegram"
    await app.bot.set_webhook(url=url, secret_token=webhook_secret,
                              drop_pending_updates=True, allowed_updates=["message",
                                                                          "callback_query",
                                                                          "my_chat_member",
                                                                          "chat_member"])
    try:
        await app.bot.set_my_commands([
            ("start", "Open the control panel"),
            ("preview", "Preview the group post"),
            ("setgroup", "Use this group for price updates"),
            ("cancel", "Cancel the current edit"),
        ])
    except Exception:                                             # pragma: no cover
        pass
    info = await app.bot.get_webhook_info()
    return {"webhook_url": info.url, "pending_updates": info.pending_update_count,
            "secret_token_set": bool(webhook_secret),
            "bot": bot.BOT_USERNAME}


# ── presentation ────────────────────────────────────────────────────────────
def status_payload(bot=None, bot_error: str | None = None) -> dict:
    payload = {
        "ok": bot is not None,
        "service": "p2p-price-bot",
        "mode": "serverless (webhook)",
        "time": int(time.time()),
    }
    if bot is None:
        payload["error"] = bot_error or "bot not configured"
        payload["hint"] = ("Set BOT_TOKEN and ADMIN_IDS in your Vercel project "
                           "(Settings ▸ Environment Variables), then redeploy "
                           "and open /api/setup?key=YOUR_CRON_SECRET")
        return payload
    state = bot.state
    payload.update({
        "pair": f"{bot.ASSET}/{bot.FIAT}",
        "interval": bot.INTERVAL,
        "storage": bot.STORE.describe(),
        "group": state.get("group"),
        "group_title": state.get("group_title"),
        "merchants": len(state.get("merchants") or {}),
        "auto": bool(state.get("auto")),
        "last_post": state.get("last_msg_time"),
        "link_mode": bot.link_mode(),
        "bot_username": bot.BOT_USERNAME,
        "cron_secret_set": bool(os.getenv("CRON_SECRET")),
    })
    return payload


def landing_html(bot=None, bot_error: str | None = None) -> str:
    payload = status_payload(bot, bot_error)
    if bot is None:
        body = f"""
        <h1>⚠️ Almost there</h1>
        <p class="err">{payload['error']}</p>
        <p>Add these environment variables to the Vercel project and redeploy:</p>
        <table>
          <tr><td><code>BOT_TOKEN</code></td><td>token from @BotFather</td></tr>
          <tr><td><code>ADMIN_IDS</code></td><td>your Telegram user id (from @userinfobot)</td></tr>
          <tr><td><code>ASSET</code> / <code>FIAT</code></td><td>e.g. USDT / USD</td></tr>
          <tr><td><code>INTERVAL</code></td><td>price check interval in seconds</td></tr>
          <tr><td><code>CRON_SECRET</code></td><td>any random string, protects <code>/api/cron</code></td></tr>
          <tr><td><code>KV_REST_API_URL</code> + <code>KV_REST_API_TOKEN</code></td>
              <td>Upstash/Redis store so state survives restarts (recommended)</td></tr>
        </table>"""
    else:
        rows = "".join(f"<tr><td>{k}</td><td><code>{v}</code></td></tr>"
                       for k, v in payload.items() if k not in ("ok", "service"))
        body = f"""
        <h1>🤖 P2P price bot is live</h1>
        <p>Telegram webhook mode · pair <b>{payload['pair']}</b> · every {payload['interval']}s</p>
        <table>{rows}</table>
        <p>Finish the setup:</p>
        <ol>
          <li>Set the env vars (<code>BOT_TOKEN</code>, <code>ADMIN_IDS</code>, a store, <code>CRON_SECRET</code>).</li>
          <li>Open <code>/api/setup?key=YOUR_CRON_SECRET</code> once to register the webhook.</li>
          <li>Ping <code>/api/cron?key=YOUR_CRON_SECRET</code> every {payload['interval']}s
              (Vercel Cron on Pro, or cron-job.org / GitHub Actions on Hobby).</li>
          <li>Open the bot in Telegram, send <code>/start</code>, add merchants, set the group.</li>
        </ol>"""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>P2P price bot</title>
<style>
 body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0f1115; color:#e8eaf0;
        margin:0; padding:40px 20px; }}
 .wrap {{ max-width: 780px; margin: 0 auto; }}
 h1 {{ font-size: 1.5rem; }}
 table {{ border-collapse: collapse; width:100%; margin: 16px 0; }}
 td {{ border-bottom:1px solid #262a33; padding:8px 6px; vertical-align:top; font-size:.95rem; }}
 code {{ background:#1b1f27; padding:2px 6px; border-radius:4px; }}
 .err {{ color:#ff8080; }}
 </style></head>
<body><div class="wrap">{body}
<p style="color:#8b93a7;font-size:.85rem">p2p-price-bot · serverless build · {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</p>
</div></body></html>"""


class handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "p2p-price-bot"

    def log_message(self, *args):                                 # keep the noise down
        pass

    # -- plumbing ----------------------------------------------------------
    def _send(self, code: int, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, payload: dict):
        self._send(code, json.dumps(payload, ensure_ascii=False, indent=1).encode(), "application/json")

    def _send_html(self, code: int, html: str):
        self._send(code, html.encode(), "text/html; charset=utf-8")

    _cached_body: bytes | None = None

    def _body(self) -> bytes:
        """Read (and cache) the request body — sniffing and handling share it."""
        if self._cached_body is not None:
            return self._cached_body
        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            length = 0
        self._cached_body = self.rfile.read(length) if length else b""
        return self._cached_body

    # -- routing -----------------------------------------------------------
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_HEAD(self):
        self._dispatch("GET", head_only=True)

    def _dispatch(self, method: str, head_only: bool = False):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        route = route_for(parsed.path)
        if query.get("route"):
            route = (query["route"][0] or "root").lower()
        bot = get_bot()
        try:
            # If a rewrite ever hides the sub-path, fall back to sniffing the
            # request itself: Telegram updates carry update_id, Vercel Cron
            # announces itself in the user-agent.
            if route == "root":
                if method == "POST":
                    try:
                        if "update_id" in json.loads(self._body() or b"{}"):
                            return self._telegram(bot, method)
                    except Exception:
                        pass
                if "vercel-cron" in (header(self.headers, "user-agent").lower()):
                    return self._cron(bot, query)
            if route == "telegram":
                return self._telegram(bot, method)
            if route == "cron":
                return self._cron(bot, query)
            if route == "setup":
                return self._setup(bot, query)
            if route == "health":
                return self._send_json(200, status_payload(bot, _bot_error))
            if head_only:
                return self._send(200, b"", "text/html; charset=utf-8")
            return self._send_html(200, landing_html(bot, _bot_error))
        except Exception as e:                                    # pragma: no cover
            traceback.print_exc()
            return self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

    # -- endpoints ---------------------------------------------------------
    def _telegram(self, bot, method: str):
        if method != "POST":
            return self._send_json(405, {"ok": False, "error": "POST only"})
        if bot is None:
            return self._send_json(503, {"ok": False, "error": _bot_error or "bot not configured"})
        expected = (os.getenv("WEBHOOK_SECRET") or "").strip()
        if expected and header(self.headers, "x-telegram-bot-api-secret-token") != expected:
            return self._send_json(401, {"ok": False, "error": "bad secret token"})
        raw = self._body()
        try:
            payload = json.loads(raw or b"{}")
        except Exception as e:
            return self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
        try:
            run_async(handle_update(bot, payload))
        except Exception as e:
            # always answer 200 so Telegram does not retry the same update forever
            traceback.print_exc()
            return self._send_json(200, {"ok": False, "error": f"{type(e).__name__}: {e}"})
        return self._send_json(200, {"ok": True})

    def _cron(self, bot, query: dict):
        if bot is None:
            return self._send_json(503, {"ok": False, "error": _bot_error or "bot not configured"})
        if not authorized(query, self.headers):
            return self._send_json(401, {"ok": False,
                                         "error": "unauthorized — pass ?key=CRON_SECRET or "
                                                  "Authorization: Bearer CRON_SECRET"})
        force = (query.get("force", ["0"])[0] or "").lower() in ("1", "true", "yes")
        summary = run_async(handle_cron(bot, force))
        return self._send_json(200, {"ok": True, "force": force, **summary})

    def _setup(self, bot, query: dict):
        if bot is None:
            return self._send_json(503, {"ok": False, "error": _bot_error or "bot not configured"})
        if not authorized(query, self.headers):
            return self._send_json(401, {"ok": False,
                                         "error": "unauthorized — pass ?key=CRON_SECRET"})
        base = (query.get("url", [""])[0]
                or (os.getenv("PUBLIC_URL") or "").strip()
                or (("https://" + os.getenv("VERCEL_URL")) if os.getenv("VERCEL_URL") else "")
                or ("https://" + header(self.headers, "x-forwarded-host", header(self.headers, "host"))))
        info = run_async(handle_setup(bot, base))
        return self._send_json(200, {"ok": True, **info,
                                     "hint": "Ping /api/cron every INTERVAL seconds "
                                             "(Vercel Cron on Pro, or an external pinger)."})
