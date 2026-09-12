"""State backends and the serverless entry point."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

import storage

ROOT = Path(__file__).resolve().parent.parent


# ── storage ────────────────────────────────────────────────────────────────
def test_file_store_roundtrip(tmp_path):
    store = storage.FileStore(tmp_path / "data.json")
    assert store.load() is None
    store.save({"group": -100123, "settings": {"price_links": True}})
    assert store.load()["group"] == -100123
    assert json.loads((tmp_path / "data.json").read_text())["group"] == -100123


def test_file_store_survives_broken_json(tmp_path):
    p = tmp_path / "data.json"
    p.write_text("{not json")
    assert storage.FileStore(p).load() is None


def test_file_store_never_raises_on_unwritable_path(tmp_path):
    store = storage.FileStore(tmp_path / "data.json")
    store.path = tmp_path / "missing" / "\0bad" / "data.json"     # cannot be created
    store.save({"a": 1})                                          # must not raise


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_redis_store_uses_rest_commands(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None, headers=None):
        calls.append((url, json, headers))
        if json[0] == "GET":
            return _FakeResponse({"result": '{"group": -42}'})
        return _FakeResponse({"result": "OK"})

    monkeypatch.setattr("httpx.post", fake_post, raising=True)
    store = storage.RedisStore("https://redis.example", "tok", key="k")

    assert store.load() == {"group": -42}
    store.save({"group": -42})
    assert calls[0][1] == ["GET", "k"]
    assert calls[1][1][0] == "SET" and calls[1][1][1] == "k"
    assert calls[1][2]["Authorization"] == "Bearer tok"
    assert "redis.example" in store.describe()


def test_redis_store_swallows_errors(monkeypatch):
    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr("httpx.post", boom, raising=True)
    store = storage.RedisStore("https://redis.example", "tok")
    assert store.load() is None
    store.save({"x": 1})                                          # must not raise


def test_redis_is_preferred_over_file(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_REST_API_URL", "https://kv.example")
    monkeypatch.setenv("KV_REST_API_TOKEN", "tok")
    store = storage.build_store(tmp_path)
    assert store.backend == "redis"
    assert store.key == storage.DEFAULT_KEY


def test_readonly_dir_falls_back_to_tmp(tmp_path, monkeypatch):
    monkeypatch.delenv("P2P_DATA_DIR", raising=False)
    readonly = tmp_path / "ro"
    store = storage.build_store(readonly)
    if store.backend == "file" and store.path.parent == readonly:
        pytest.skip("directory is writable in this environment")
    assert store.backend in ("file", "none")


# ── serverless entry point ────────────────────────────────────────────────
@pytest.fixture(scope="module")
def api():
    spec = importlib.util.spec_from_file_location("vercel_api", ROOT / "api" / "index.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["vercel_api"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path,expected", [
    ("/api/telegram", "telegram"),
    ("/telegram", "telegram"),
    ("/api/index.py", "root"),
    ("/", "root"),
    ("", "root"),
    ("/api/cron/", "cron"),
    ("/api/health", "health"),
    ("/api/setup", "setup"),
])
def test_route_matching(api, path, expected):
    assert api.route_for(path) == expected


def test_landing_page_explains_missing_configuration(api):
    html = api.landing_html(None, "ConfigError: No configuration found")
    assert "BOT_TOKEN" in html and "ADMIN_IDS" in html and "ConfigError" in html


def test_status_payload_reports_the_bot(api):
    import bot
    payload = api.status_payload(bot)
    assert payload["ok"] is True
    assert payload["pair"] == f"{bot.ASSET}/{bot.FIAT}"
    assert payload["link_mode"] == "ad"
    assert "storage" in payload


def test_authorized_requires_the_secret(api, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    assert api.authorized({"key": ["s3cret"]}, {}) is True
    assert api.authorized({}, {"Authorization": "Bearer s3cret"}) is True
    assert api.authorized({"key": ["nope"]}, {}) is False
    assert api.authorized({}, {}) is False

    monkeypatch.delenv("CRON_SECRET", raising=False)
    monkeypatch.setenv("BOT_TOKEN", "123456:TEST-TOKEN")
    assert api.authorized({"key": ["123456:TEST-TOKEN"]}, {}) is True
