import pytest
from unittest.mock import patch, MagicMock

import app.spotify.client as sc

class FakeResp:
    def __init__(self, status=200, data=None, headers=None):
        self.status_code = status
        self._data = data or {}
        self.text = "" if data is None else "ok"
        self.headers = headers or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

def test_search_track_full(monkeypatch):
    fake = {"tracks": {"items": [{"id": "t1", "name": "Name", "artists": [{"name":"A"}], "album": {"images": []}}]}}
    def fake_req(method, url, headers=None, timeout=None, **kwargs):
        return FakeResp(200, fake)
    monkeypatch.setattr("requests.request", fake_req)
    client = sc.SpotifyUserClient("token")
    res = client.search_track_full("query")
    assert res["id"] == "t1"

def test_is_track_saved(monkeypatch):
    def fake_req(method, url, headers=None, timeout=None, **kwargs):
        return FakeResp(200, [True])
    monkeypatch.setattr("requests.request", fake_req)
    client = sc.SpotifyUserClient("token")
    assert client.is_track_saved("t1") is True

def test_save_and_remove_tracks_calls(monkeypatch):
    recorded = []
    def fake_req(method, url, headers=None, timeout=None, **kwargs):
        recorded.append((method, url, kwargs))
        return FakeResp(200, {})
    monkeypatch.setattr("requests.request", fake_req)
    client = sc.SpotifyUserClient("token")
    client.save_tracks(["a","b","c"])
    client.remove_saved_tracks(["a","b","c"])
    assert any(call[0] == "PUT" for call in recorded)
    assert any(call[0] == "DELETE" for call in recorded)

def test_get_saved_tracks(monkeypatch):
    page = {"items": [{"track": {"id":"t1","name":"t","artists":[{"name":"A"}],"album":{"images":[]}}}], "total": 1}
    def fake_req(method, url, headers=None, timeout=None, **kwargs):
        return FakeResp(200, page)
    monkeypatch.setattr("requests.request", fake_req)
    client = sc.SpotifyUserClient("token")
    res = client.get_saved_tracks(limit=1, offset=0)
    assert "items" in res
