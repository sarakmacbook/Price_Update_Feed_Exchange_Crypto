"""End-to-end check of the Vercel handler: status page, health, auth, cron.

The HTTP server runs in a thread exactly like the deployed function; Telegram is
never contacted (auto mode is off, so the cron tick is a no-op).
"""

import importlib.util
import json
import sys
import threading
import types
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def api():
    spec = importlib.util.spec_from_file_location("vercel_api_http", ROOT / "api" / "index.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["vercel_api_http"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def server(api):
    httpd = HTTPServer(("127.0.0.1", 0), api.handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:                            # 401/405/503 …
        return e.code, e.read().decode()


def _post(url, payload=None, headers=None):
    body = json.dumps(payload or {}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_root_serves_a_status_page(server, api):
    status, body = _get(server + "/")
    assert status == 200
    assert api.get_bot() is not None          # credentials are provided by conftest
    assert "p2p-price-bot" in body or "P2P price bot" in body


def test_health_endpoint_is_json(server, api):
    status, body = _get(server + "/api/health")
    payload = json.loads(body)
    assert status == 200 and payload["ok"] is True
    assert payload["mode"] == "serverless (webhook)"
    assert payload["merchants"] == len(api.get_bot().state["merchants"])


def test_cron_requires_the_secret(server):
    status, body = _get(server + "/api/cron")
    assert status == 401 and json.loads(body)["ok"] is False


def test_setup_requires_the_secret(server):
    status, _ = _get(server + "/api/setup?key=wrong")
    assert status == 401


def test_cron_tick_with_secret_runs_offline(server, api, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "topsecret")
    api._app = types.SimpleNamespace(bot=object())                 # skip PTB initialisation
    status, body = _get(server + "/api/cron?key=topsecret")
    payload = json.loads(body)
    assert status == 200 and payload["ok"] is True
    assert payload["posted"] is False and payload["deleted"] is False


def test_telegram_webhook_checks_the_secret_token(server, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "hooksecret")
    status, body = _post(server + "/api/telegram", {"update_id": 1},
                         headers={"X-Telegram-Bot-Api-Secret-Token": "nope"})
    assert status == 401 and json.loads(body)["ok"] is False


def test_telegram_webhook_rejects_get(server):
    status, _ = _get(server + "/api/telegram")
    assert status == 405
