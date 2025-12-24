from datetime import datetime
from app.utils.time import human_time
from app.bot.keyboards import main_kb

def test_human_time_none():
    assert human_time(None) == "—"

def test_human_time_format():
    dt = datetime(2023, 1, 2, 3, 4, 5)
    assert human_time(dt) == "02.01.2023 03:04:05"

def test_main_kb_structure():
    kb = main_kb()
    assert hasattr(kb, "keyboard")
    assert len(kb.keyboard) >= 1
