from datetime import datetime
from typing import Optional


def human_time(dt: Optional[datetime]) -> str:
    """
    Convert datetime to human-readable string.
    """
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M:%S")
