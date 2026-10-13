"""
Session pipeline: raw events -> sessions -> daily playtime.

    events (append-only, written by session_log.py)
      -> sessions        one row per continuous play session
      -> daily_playtime  seconds per game per local calendar day

Derived tables are rebuilt from scratch on every run, so the transform is
idempotent and fixing a rule here repairs all history. Run it directly to
rebuild and print a summary:

    python pipeline.py              # rebuild + summary
    python pipeline.py --csv out/   # also export the derived tables as CSV
"""
import argparse
import csv
import os
import time
from datetime import datetime, timedelta

import session_log

# A liveness gap longer than this (sleep, hang, killed process) ends the session
# at the last sign of life instead of counting the gap as playtime.
MAX_GAP_SECONDS = session_log.HEARTBEAT_SECONDS * 3
# Sessions shorter than this are mis-clicks or quick switches, not play.
MIN_SESSION_SECONDS = 60


def build_sessions(events, now=None, current_run=None, max_gap=MAX_GAP_SECONDS,
                   min_seconds=MIN_SESSION_SECONDS):
    """Pair start/stop events into sessions.

    Args:
        events: iterable of (ts, kind, game, console, reason, run_id) in insert order.
        now: current unix time; a still-open session from `current_run` ends here.
        current_run: run_id of the running app, if any.

    Returns:
        list of dicts with start, end, seconds, game, console, end_reason, is_open.
    """
    now = int(now if now is not None else time.time())
    sessions = []
    current = None  # the open session: dict with start, last_seen, game, console, run_id

    def close(end, reason, is_open=False):
        nonlocal current
        end = max(end, current["start"])
        if end - current["start"] >= min_seconds:
            sessions.append({
                "start": current["start"], "end": end, "seconds": end - current["start"],
                "game": current["game"], "console": current["console"],
                "end_reason": reason, "is_open": int(is_open),
            })
        current = None

    for ts, kind, game, console, reason, run_id in events:
        if current and run_id != current["run_id"]:
            # The previous app run never logged a stop (crash / killed)
            close(current["last_seen"], "unclean_exit")
        if current and ts - current["last_seen"] > max_gap and kind != "stop":
            # App was asleep or frozen: end at the last sign of life, then carry on
            game_now, console_now = current["game"], current["console"]
            close(current["last_seen"], "gap")
            if kind == "heartbeat":
                current = {"start": ts, "last_seen": ts, "game": game_now,
                           "console": console_now, "run_id": run_id}
                continue

        if kind == "start":
            if current:
                close(ts, "switch")
            current = {"start": ts, "last_seen": ts, "game": game,
                       "console": console, "run_id": run_id}
        elif kind == "heartbeat":
            if current:
                current["last_seen"] = max(current["last_seen"], ts)
        elif kind == "stop":
            if current:
                if ts - current["last_seen"] > max_gap:
                    close(current["last_seen"], "gap")
                else:
                    close(ts, reason or "stop")

    if current:
        if current["run_id"] == current_run and now - current["last_seen"] <= max_gap:
            close(now, "open", is_open=True)
        else:
            close(current["last_seen"], "unclean_exit")
    return sessions


def split_by_day(sessions):
    """Split sessions at local midnight and total seconds per (day, game, console)."""
    totals = {}
    for s in sessions:
        cursor = datetime.fromtimestamp(s["start"])
        end = datetime.fromtimestamp(s["end"])
        while cursor < end:
            next_midnight = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time())
            chunk_end = min(end, next_midnight)
            key = (cursor.date().isoformat(), s["game"], s["console"] or "")
            totals[key] = totals.get(key, 0) + int((chunk_end - cursor).total_seconds())
            cursor = chunk_end
    return [{"day": d, "game": g, "console": c, "seconds": sec}
            for (d, g, c), sec in sorted(totals.items())]


def run(db_path=None, now=None, current_run=None):
    """Rebuild the derived tables. Returns (sessions, daily rows)."""
    conn = session_log.connect(db_path)
    try:
        events = conn.execute(
            "SELECT ts, kind, game, console, reason, run_id FROM events ORDER BY id").fetchall()
        sessions = build_sessions(events, now=now, current_run=current_run)
        daily = split_by_day(sessions)
        with conn:
            conn.execute("DROP TABLE IF EXISTS sessions")
            conn.execute("""
                CREATE TABLE sessions (
                    start INTEGER, "end" INTEGER, seconds INTEGER,
                    game TEXT, console TEXT, end_reason TEXT, is_open INTEGER
                )""")
            conn.executemany(
                'INSERT INTO sessions VALUES (:start, :end, :seconds, :game, :console, :end_reason, :is_open)',
                sessions)
            conn.execute("DROP TABLE IF EXISTS daily_playtime")
            conn.execute("CREATE TABLE daily_playtime (day TEXT, game TEXT, console TEXT, seconds INTEGER)")
            conn.executemany("INSERT INTO daily_playtime VALUES (:day, :game, :console, :seconds)", daily)
        return sessions, daily
    finally:
        conn.close()


def export_csv(out_dir, sessions, daily):
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in (("sessions", sessions), ("daily_playtime", daily)):
        if not rows:
            continue
        with open(os.path.join(out_dir, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", help="Path to sessions.db (default: app-data folder)")
    parser.add_argument("--csv", metavar="DIR", help="Export derived tables as CSV to DIR")
    args = parser.parse_args()

    db_path = args.db or session_log.default_db_path()
    sessions, daily = run(db_path)
    print(f"Database: {db_path}")
    print(f"{len(sessions)} sessions, {len(daily)} game-days, "
          f"{sum(s['seconds'] for s in sessions) / 3600:.1f} hours total")
    if args.csv:
        export_csv(args.csv, sessions, daily)
        print(f"Exported CSV to {args.csv}")


if __name__ == "__main__":
    main()
