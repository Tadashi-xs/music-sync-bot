import importlib

def test_storage_dicts_exist():
    m = importlib.import_module("app.storage.memory")
    assert isinstance(m.USER_SPOTIFY, dict)
    assert isinstance(m.LAST_SHOWN, dict)
    assert isinstance(m.STATS, dict)
    assert isinstance(m.ARTIST_COUNTER, dict)

def test_storage_write_read(tmp_path):
    m = importlib.import_module("app.storage.memory")
    tg = "42"
    m.USER_SPOTIFY[tg] = {"access_token": "a", "expires_at": 999999999}
    assert m.USER_SPOTIFY["42"]["access_token"] == "a"
    m.STATS[tg] = {"added": 1, "deleted": 0}
    assert m.STATS["42"]["added"] == 1
