"""
Stats queries over the derived tables built by pipeline.py.
"""
from datetime import date, datetime, timedelta

import session_log

PERIODS = ("7 days", "30 days", "This month", "All time")
PERIOD_PHRASES = {
    "7 days": "in the last 7 days",
    "30 days": "in the last 30 days",
    "This month": "this month",
    "All time": "in total",
}


def period_range(period, today):
    """(first_day, last_day) for a period, or (None, today) for all time."""
    if period == "7 days":
        return today - timedelta(days=6), today
    if period == "30 days":
        return today - timedelta(days=29), today
    if period == "This month":
        return today.replace(day=1), today
    return None, today


def format_duration(seconds):
    """Compact duration: 45m, 3h 20m, 41h."""
    minutes = int(seconds) // 60
    hours, minutes = divmod(minutes, 60)
    if hours >= 10:
        return f"{hours}h"
    if hours:
        return f"{hours}h {minutes:02}m"
    return f"{minutes}m"


def summarize(period, db_path=None, today=None):
    """Everything the Stats tab shows for one period, as plain Python data."""
    today = today or date.today()
    first, last = period_range(period, today)
    conn = session_log.connect(db_path)
    try:
        has_tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name IN ('sessions', 'daily_playtime')").fetchone()[0] == 2
        if not has_tables:
            daily, sessions = [], []
        else:
            daily = conn.execute(
                "SELECT day, game, console, seconds FROM daily_playtime WHERE day >= ? AND day <= ?",
                ((first or date.min).isoformat(), last.isoformat())).fetchall()
            sessions = conn.execute(
                'SELECT start, "end", seconds, game, console, is_open FROM sessions ORDER BY start DESC').fetchall()
    finally:
        conn.close()

    sessions = [s for s in sessions
                if (first is None or datetime.fromtimestamp(s[0]).date() >= first)
                and datetime.fromtimestamp(s[0]).date() <= last]

    by_game = {}
    by_day = {}
    for day, game, console, seconds in daily:
        key = (game, console)
        by_game[key] = by_game.get(key, 0) + seconds
        by_day[day] = by_day.get(day, 0) + seconds
    top_games = sorted(((g, c, sec) for (g, c), sec in by_game.items()), key=lambda r: -r[2])

    total = sum(by_day.values())
    headline = None
    if top_games:
        game, _, seconds = top_games[0]
        headline = f"You played {format_duration(seconds)} of {game} {PERIOD_PHRASES[period]}."

    return {
        "total": total,
        "session_count": len(sessions),
        "avg_session": total / len(sessions) if sessions else 0,
        "active_days": len(by_day),
        "headline": headline,
        "top_games": top_games,
        "buckets": _buckets(period, first, last, by_day),
        "recent": sessions[:8],
    }


def _buckets(period, first, last, by_day):
    """Chart bars: one per day, or one per month for all time.

    Returns a list of (axis label, seconds, tooltip label).
    """
    if period != "All time":
        days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
        return [(d.strftime("%a")[0] if period == "7 days" else str(d.day),
                 by_day.get(d.isoformat(), 0),
                 d.strftime("%a %d %b"))
                for d in days]

    by_month = {}
    for day, seconds in by_day.items():
        by_month[day[:7]] = by_month.get(day[:7], 0) + seconds
    if not by_month:
        return []
    year, month = map(int, min(by_month).split("-"))
    buckets = []
    while (year, month) <= (last.year, last.month):
        d = date(year, month, 1)
        buckets.append((d.strftime("%b"), by_month.get(f"{year:04}-{month:02}", 0), d.strftime("%b %Y")))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return buckets[-24:]
