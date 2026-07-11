"""每日微语库 —— 按天循环选取，每天不同。"""

import json
import os

_QUOTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quotes.json")


def _load_quotes():
    with open(_QUOTES_PATH, encoding="utf-8") as f:
        return json.load(f)


DAILY_QUOTES = _load_quotes()


def get_daily_quote():
    """按天选一条微语，同一天返回同一条。"""
    from datetime import datetime

    day_of_year = datetime.now().timetuple().tm_yday
    return DAILY_QUOTES[day_of_year % len(DAILY_QUOTES)]
