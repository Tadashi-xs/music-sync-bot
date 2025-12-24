import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import app.spotify.oauth as oauth

@pytest.fixture
def fake_config(monkeypatch):
    cfg = SimpleNamespace()
    cfg.spotify = SimpleNamespace(client_id="cid", client_secret="csec", redirect_uri="http://localhost/cb", scopes="s1 s2")
    cfg.oauth = SimpleNamespace(host="127.0.0.1", port=8081)
    cfg.telegram = SimpleNamespace(token="telegramtoken")
    monkeypatch.setattr("app.spotify.oauth._load_config_or_raise", lambda: cfg)
    return cfg

def test_get_auth_url(fake_config):
    url = oauth.get_auth_url("123")
    assert "client_id=cid" in url
    assert "state=123" in url

def test_exchange_and_refresh(monkeypatch, fake_config):
    class FakeResp:
        def __init__(self, data):
            self._data = data
            self.status_code = 200
            self.text = "ok"
        def json(self):
            return self._data
        def raise_for_status(self): pass

    def fake_post(url, headers=None, data=None, timeout=None):
        if data.get("grant_type") == "authorization_code":
            return FakeResp({"access_token":"a","refresh_token":"r","expires_in":3600})
        else:
            return FakeResp({"access_token":"a2","expires_in":3600})
    monkeypatch.setattr("requests.post", fake_post)
    tok = oauth.exchange_code("code")
    assert tok["access_token"] == "a"
    ref = oauth.refresh_access_token("r")
    assert ref["access_token"] == "a2"

@pytest.mark.asyncio
async def test_ensure_token_refresh(monkeypatch, fake_config):
    tg = "999"
    oauth.save_token(tg, {"access_token":"old","refresh_token":"r","expires_at":1})
    monkeypatch.setattr("app.spotify.oauth.refresh_access_token", lambda refresh: {"access_token":"new","expires_at":9999999})
    tok = await oauth.ensure_token(tg)
    assert tok == "new"
