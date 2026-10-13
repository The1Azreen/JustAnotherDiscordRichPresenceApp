"""Tests for the session pipeline. Run with: python -m unittest discover tests"""
import os
import sys
import tempfile
import unittest
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pipeline  # noqa: E402
import session_log  # noqa: E402
import stats  # noqa: E402

T0 = int(datetime(2026, 10, 1, 20, 0).timestamp())  # 8pm local


def ev(offset, kind, game="Hades", reason=None, run="r1", console="PC"):
    return (T0 + offset, kind, game, console, reason, run)


def beats(start, end, game="Hades", run="r1"):
    return [ev(t, "heartbeat", game, run=run) for t in range(start, end + 1, 60)]


class BuildSessionsTest(unittest.TestCase):
    def test_start_stop(self):
        events = [ev(0, "start"), *beats(60, 3540), ev(3600, "stop", reason="clear")]
        [s] = pipeline.build_sessions(events, now=T0 + 9999)
        self.assertEqual((s["seconds"], s["end_reason"]), (3600, "clear"))

    def test_switch_closes_previous(self):
        events = [ev(0, "start"), *beats(60, 600), ev(600, "stop", reason="switch"),
                  ev(600, "start", "Celeste"), *beats(660, 1200, "Celeste"),
                  ev(1200, "stop", "Celeste", reason="clear")]
        sessions = pipeline.build_sessions(events, now=T0 + 9999)
        self.assertEqual([(s["game"], s["seconds"]) for s in sessions], [("Hades", 600), ("Celeste", 600)])

    def test_crash_ends_at_last_heartbeat(self):
        events = [ev(0, "start"), *beats(60, 1800), ev(5000, "start", "Celeste", run="r2")]
        first = pipeline.build_sessions(events, now=T0 + 5000, current_run="r2")[0]
        self.assertEqual((first["seconds"], first["end_reason"]), (1800, "unclean_exit"))

    def test_sleep_gap_is_not_playtime(self):
        # Heartbeats stop for 2 hours (PC asleep), then resume
        events = [ev(0, "start"), *beats(60, 600), *beats(7800, 8400), ev(8400, "stop", reason="clear")]
        sessions = pipeline.build_sessions(events, now=T0 + 9999)
        self.assertEqual([(s["seconds"], s["end_reason"]) for s in sessions], [(600, "gap"), (600, "clear")])

    def test_idle_stop_is_backdated_and_resume_starts_new(self):
        # Last input at +900s; the 15 min idle threshold trips at +1800s
        events = [ev(0, "start"), *beats(60, 1740), ev(900, "stop", reason="idle"),
                  ev(3000, "start", reason="resume"), *beats(3060, 3600), ev(3600, "stop", reason="exit")]
        sessions = pipeline.build_sessions(events, now=T0 + 9999)
        self.assertEqual([s["seconds"] for s in sessions], [900, 600])

    def test_open_session_runs_to_now_only_for_current_run(self):
        events = [ev(0, "start"), *beats(60, 600)]
        [live] = pipeline.build_sessions(events, now=T0 + 630, current_run="r1")
        self.assertEqual((live["seconds"], live["is_open"]), (630, 1))
        [old] = pipeline.build_sessions(events, now=T0 + 630, current_run="other")
        self.assertEqual((old["seconds"], old["is_open"]), (600, 0))

    def test_short_sessions_dropped(self):
        events = [ev(0, "start"), ev(20, "stop", reason="switch")]
        self.assertEqual(pipeline.build_sessions(events, now=T0 + 100), [])


class SplitByDayTest(unittest.TestCase):
    def test_session_across_midnight(self):
        start = int(datetime(2026, 10, 1, 23, 0).timestamp())
        end = int(datetime(2026, 10, 2, 1, 30).timestamp())
        rows = pipeline.split_by_day([{"start": start, "end": end, "game": "Hades", "console": "PC"}])
        self.assertEqual([(r["day"], r["seconds"]) for r in rows],
                         [("2026-10-01", 3600), ("2026-10-02", 5400)])


class EndToEndTest(unittest.TestCase):
    def test_run_and_summarize(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "sessions.db")
            with session_log.connect(db) as conn:
                conn.executemany(
                    "INSERT INTO events (ts, kind, game, console, reason, run_id) VALUES (?, ?, ?, ?, ?, ?)",
                    [ev(0, "start"), *beats(60, 7200), ev(7200, "stop", reason="clear")])
            conn.close()
            pipeline.run(db, now=T0 + 9999)
            summary = stats.summarize("This month", db, today=date(2026, 10, 13))
            self.assertEqual(summary["total"], 7200)
            self.assertEqual(summary["headline"], "You played 2h 00m of Hades this month.")
            self.assertEqual(len(summary["buckets"]), 13)


if __name__ == "__main__":
    unittest.main()
