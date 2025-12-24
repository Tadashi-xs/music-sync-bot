import os
from types import SimpleNamespace
import importlib

import pytest

@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_REDIRECT_URI", raising=False)
    yield

def test_load_config_success(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok:test")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "cid")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost:8080/callback")
    from app.config.settings import load_config
    cfg = load_config()
    assert cfg.telegram.token == "tok:test"
    assert cfg.spotify.client_id == "cid"
    assert "playlist-modify-public" in cfg.spotify.scopes

def test_load_config_missing(monkeypatch):
    from app.config.settings import load_config
    with pytest.raises(RuntimeError):
        load_config()
