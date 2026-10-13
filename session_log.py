"""
Session logging: records play sessions as raw events in a local SQLite file.

The database lives in the user's app-data folder (never inside the repo), so
play history is not committed or shared by accident. Events are append-only;
`pipeline.py` turns them into sessions and daily rollups.
"""
import os
import sqlite3
import sys
import time
import uuid

APP_DIR_NAME = "JustAnotherDiscordRichPresenceApp"
HEARTBEAT_SECONDS = 60


def default_data_dir():
    """Per-user data folder: %APPDATA% on Windows, XDG data dir elsewhere.

    Set JADRPA_DATA_DIR to override (handy for demos and tests).
    """
    override = os.environ.get("JADRPA_DATA_DIR")
    if override:
        return override
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, APP_DIR_NAME)


def default_db_path():
    return os.path.join(default_data_dir(), "sessions.db")


def connect(db_path=None):
    """Open the database, creating the folder and raw events table if needed."""
    db_path = db_path or default_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      INTEGER NOT NULL,   -- unix seconds (UTC)
            kind    TEXT    NOT NULL,   -- start | stop | heartbeat
            game    TEXT,
            console TEXT,
            reason  TEXT,               -- why a session stopped
            run_id  TEXT    NOT NULL    -- one per app launch
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
    return conn


def seconds_since_last_input():
    """Seconds since the last keyboard/mouse input (Windows only, else 0)."""
    if sys.platform != "win32":
        return 0
    try:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0
        millis = (ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
        return millis // 1000
    except Exception:
        return 0


class SessionLogger:
    """Tracks the game currently shown on Discord and logs session boundaries.

    A session starts when presence is set for a game, and ends when the game
    changes, presence is cleared, Discord disconnects, the app closes, or the
    PC has been idle longer than `idle_minutes` (0 disables idle detection).
    An idle-ended session resumes automatically when input returns.
    """

    def __init__(self, db_path=None, idle_minutes=15):
        self.db_path = db_path or default_db_path()
        self.idle_seconds = max(0, int(idle_minutes)) * 60
        self.run_id = uuid.uuid4().hex
        self.game = None
        self.console = None
        self.paused_for_idle = False
        self.enabled = True
        try:
            connect(self.db_path).close()
        except Exception as e:
            print(f"Session logging disabled: {e}")
            self.enabled = False

    def _write(self, kind, ts=None, reason=None):
        if not self.enabled:
            return
        try:
            with connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO events (ts, kind, game, console, reason, run_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (int(ts or time.time()), kind, self.game, self.console, reason, self.run_id))
        except Exception as e:
            print(f"Failed to log session event: {e}")

    @property
    def active(self):
        return self.game is not None and not self.paused_for_idle

    def start(self, game, console=None):
        """Begin a session, ending the previous one if the game changed."""
        game = (game or "").strip()
        if not game:
            return
        if self.active and game == self.game and console == self.console:
            return  # same game, e.g. only the state text changed
        if self.active:
            self._write("stop", reason="switch")
        self.game, self.console = game, console
        self.paused_for_idle = False
        self._write("start")

    def stop(self, reason):
        """End the current session, if any."""
        if self.active:
            self._write("stop", reason=reason)
        self.game = self.console = None
        self.paused_for_idle = False

    def heartbeat(self):
        """Call about once a minute: records liveness and handles idle."""
        if self.game is None:
            return
        idle = seconds_since_last_input()
        if self.idle_seconds and idle >= self.idle_seconds:
            if not self.paused_for_idle:
                # Back-date the stop to when input actually stopped
                self._write("stop", ts=time.time() - idle, reason="idle")
                self.paused_for_idle = True
        elif self.paused_for_idle:
            self.paused_for_idle = False
            self._write("start", reason="resume")
        else:
            self._write("heartbeat")
