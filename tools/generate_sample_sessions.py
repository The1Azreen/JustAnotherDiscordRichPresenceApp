"""
Fill a sessions database with ~3 months of fake play history for demos.

Writes to a separate folder by default so your real history is untouched:

    python tools/generate_sample_sessions.py
    set JADRPA_DATA_DIR=sample_data && python main.py      (Windows cmd)
"""
import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import session_log  # noqa: E402

GAMES = [("Persona 5 Royal", "PS5", 5), ("Hades", "PC", 3), ("Elden Ring", "PS5", 3),
         ("Stardew Valley", "Switch", 2), ("Celeste", "PC", 1)]


def generate(db_path, days=90, seed=7):
    rng = random.Random(seed)
    now = int(time.time())
    weights = [w for _, _, w in GAMES]
    rows = []
    for day in range(days, 0, -1):
        if rng.random() < 0.35:
            continue  # day off
        cursor = now - day * 86400 + rng.randint(17, 21) * 3600 - 86400 // 2
        for _ in range(rng.choice((1, 1, 2, 3))):
            game, console, _ = rng.choices(GAMES, weights)[0]
            length = rng.randint(20, 180) * 60
            run = f"sample-{day}"
            rows.append((cursor, "start", game, console, None, run))
            rows += [(t, "heartbeat", game, console, None, run)
                     for t in range(cursor + 60, cursor + length, 60)]
            rows.append((cursor + length, "stop", game, console, "clear", run))
            cursor += length + rng.randint(5, 60) * 60
    with session_log.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO events (ts, kind, game, console, reason, run_id) VALUES (?, ?, ?, ?, ?, ?)", rows)
    conn.close()
    return sum(1 for r in rows if r[1] == "start")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="sample_data", help="Folder for sessions.db (default: sample_data)")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()
    db_path = os.path.join(args.out, "sessions.db")
    if os.path.exists(db_path):
        sys.exit(f"{db_path} already exists; delete it or pick another --out folder.")
    count = generate(db_path, args.days)
    print(f"Wrote {count} sample sessions to {db_path}")


if __name__ == "__main__":
    main()
