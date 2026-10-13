"""
Main GUI application for Discord Rich Presence Game Selector.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import base64
import configparser
import os
import threading
import urllib.request
from database import GameDatabase
from discord_rpc import DiscordRPC
from session_log import SessionLogger, HEARTBEAT_SECONDS
import pipeline
import stats
import theme
import time
from datetime import datetime


TAB_NAMES = ("Presence", "Images", "Stats", "Settings", "Log")


class DiscordRPCApp:
    """Main application window for Discord Rich Presence."""

    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Discord Rich Presence - Game Selector")
        self.root.geometry("560x760")
        self.root.minsize(480, 560)

        # Initialize variables
        self.client_id = None
        self.rpc = None
        self.connected = False
        self.field_vars = []
        self.db = None
        self.start_time = None
        self.use_google_sheets = False
        self.google_sheet_url = ""
        self.credentials_path = ""
        self.idle_minutes = 15
        self.keep_timer = False
        self.current_tab = None
        self.game_titles = []      # all titles for the selected console
        self.loaded_game = None    # database row of the selected game
        self.applied = None        # snapshot of the fields last sent to Discord
        self.reset_buttons = []    # (entry, database column, button)
        self.stats_period = "This month"
        
        # Load configuration
        self.load_config()

        # Play sessions are logged to the user's app-data folder, not the repo
        self.session_logger = SessionLogger(idle_minutes=self.idle_minutes)
        
        # Initialize database based on config
        self.init_database()
        
        # Create UI
        self.create_widgets()
        
        # Auto-connect if enabled
        if hasattr(self, 'auto_connect') and self.auto_connect:
            self.root.after(1000, self.connect_discord)
    
    def load_config(self):
        """Load configuration from config.ini file."""
        config = configparser.ConfigParser()
        
        # Check if config.ini exists, otherwise use example
        if os.path.exists('config.ini'):
            config.read('config.ini')
        elif os.path.exists('config.ini.example'):
            print("config.ini not found, using config.ini.example")
            config.read('config.ini.example')
        else:
            print("No configuration file found")
            return
        
        # Load Discord settings
        try:
            self.client_id = config.get('Discord', 'CLIENT_ID')
            if self.client_id == "YOUR_CLIENT_ID_HERE":
                self.client_id = None
                print("Please set your Discord Client ID in config.ini")
        except:
            self.client_id = None
        
        # Load general settings
        try:
            self.auto_connect = config.getboolean('Settings', 'AUTO_CONNECT')
        except:
            self.auto_connect = False
        try:
            self.keep_timer = config.getboolean('Settings', 'KEEP_TIMER_ON_SWITCH', fallback=False)
        except ValueError:
            self.keep_timer = False
        try:
            self.idle_minutes = config.getint('Stats', 'IDLE_MINUTES', fallback=15)
        except ValueError:
            self.idle_minutes = 15
        
        # Load Google Sheets settings
        try:
            self.use_google_sheets = config.getboolean('GoogleSheets', 'USE_GOOGLE_SHEETS')
            self.google_sheet_url = config.get('GoogleSheets', 'SHEET_URL', fallback='')
            self.credentials_path = config.get('GoogleSheets', 'CREDENTIALS_PATH', fallback='credentials.json')
        except:
            self.use_google_sheets = False
            self.google_sheet_url = ''
            self.credentials_path = 'credentials.json'
    
    def init_database(self):
        """Initialize the database based on configuration."""
        try:
            if self.use_google_sheets and self.google_sheet_url:
                self.db = GameDatabase(
                    use_google_sheets=True,
                    google_sheet_url=self.google_sheet_url,
                    credentials_path=self.credentials_path
                )
            else:
                self.db = GameDatabase()
        except Exception as e:
            print(f"Error initializing database: {e}")
            # Fallback to local database
            self.db = GameDatabase()
            self.use_google_sheets = False
    
    def create_widgets(self):
        """Create all GUI widgets."""
        theme.apply_theme(self.root)
        theme.route_mousewheel(self.root)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        self.build_header()
        self.build_tab_bar()

        self.tab_container = tk.Frame(self.root, bg=theme.BG)
        self.tab_container.grid(row=2, column=0, sticky="nsew")
        self.tab_container.columnconfigure(0, weight=1)
        self.tab_container.rowconfigure(0, weight=1)
        self.tabs = {}
        self.build_presence_tab()
        self.build_images_tab()
        self.build_stats_tab()
        self.build_settings_tab()
        self.build_log_tab()

        self.build_footer()

        self.show_tab("Presence")
        self.set_connected(False)
        self.tick()
        self.root.after(HEARTBEAT_SECONDS * 1000, self.session_heartbeat)

        # Initial log message
        self.log_message("Application started. Please connect to Discord.")
        if not self.client_id:
            self.log_message("WARNING: Client ID not configured. Please enter your Discord Client ID.")

    def build_header(self):
        """Top bar with avatar, connection status and shortcut icons."""
        header = tk.Frame(self.root, bg=theme.BG_SECONDARY, padx=16, pady=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        self.avatar = tk.Canvas(header, width=42, height=42, bg=theme.BG_SECONDARY,
                                highlightthickness=0)
        self.avatar_photo = None
        self.draw_avatar()
        self.avatar.grid(row=0, column=0, rowspan=2, padx=(0, 10))

        self.header_title = tk.Label(header, text="Rich Presence Manager", bg=theme.BG_SECONDARY,
                                     fg=theme.TEXT_STRONG, font=theme.FONT_TITLE)
        self.header_title.grid(row=0, column=1, sticky="sw")
        self.connection_status = tk.Label(header, text="Disconnected", bg=theme.BG_SECONDARY,
                                          fg=theme.TEXT_MUTED, font=theme.FONT_SMALL)
        self.connection_status.grid(row=1, column=1, sticky="nw")

        theme.FlatButton(header, text="?", variant="ghost", padx=10, pady=2,
                         font=theme.FONT_TITLE,
                         command=self.show_google_sheets_help).grid(row=0, column=2, rowspan=2)
        theme.FlatButton(header, text="⚙", variant="ghost", padx=8, pady=2,
                         font=(theme.SYMBOL, 14),
                         command=lambda: self.show_tab("Settings")).grid(row=0, column=3, rowspan=2, padx=(4, 0))

    def draw_avatar(self, initial=None):
        """Round avatar with a status dot: the Discord user's picture once known."""
        c = self.avatar
        c.delete("all")
        if self.avatar_photo:
            c.create_image(19, 19, image=self.avatar_photo)
            # Mask the square corners with a ring in the header colour
            c.create_oval(-1.5, -1.5, 39.5, 39.5, outline=theme.BG_SECONDARY, width=7)
        else:
            c.create_oval(3, 3, 35, 35, fill=theme.BLURPLE, outline="")
            c.create_text(19, 19, text=initial or "▶", fill="#FFFFFF", font=theme.FONT_TITLE)
        self.status_dot = c.create_oval(26, 26, 41, 41, outline=theme.BG_SECONDARY, width=3,
                                        fill=theme.GREEN if self.connected else theme.OFFLINE)

    def show_discord_user(self, user):
        """Show the connected Discord account in the header, like the Discord client."""
        self.avatar_photo = None
        if not user:
            self.header_title.config(text="Rich Presence Manager")
            self.draw_avatar()
            return
        name = user.get("global_name") or user.get("username") or "Discord user"
        self.header_title.config(text=theme.ellipsize(name, 20))
        self.draw_avatar(initial=name[:1].upper())
        if user.get("avatar") and user.get("id"):
            url = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png?size=32"
            threading.Thread(target=self.fetch_avatar, args=(url,), daemon=True).start()

    def fetch_avatar(self, url):
        """Download the avatar off the UI thread, then hand it back to Tk."""
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = base64.b64encode(response.read())
        except Exception as e:
            print(f"Could not load Discord avatar: {e}")
            return
        self.root.after(0, self.set_avatar, data)

    def set_avatar(self, data):
        if not self.connected:
            return
        try:
            self.avatar_photo = tk.PhotoImage(data=data)
        except tk.TclError:
            return
        self.draw_avatar()

    def build_tab_bar(self):
        """Segmented tab buttons under the header."""
        bar = tk.Frame(self.root, bg=theme.BG_SECONDARY, padx=16)
        bar.grid(row=1, column=0, sticky="ew")
        self.tab_buttons = {}
        for i, name in enumerate(TAB_NAMES):
            bar.columnconfigure(i, weight=1, uniform="tabs")
            button = theme.FlatButton(bar, text=name, variant="tab", font=theme.FONT_BUTTON, padx=8,
                                      command=lambda n=name: self.show_tab(n))
            button.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0), pady=(0, 12))
            self.tab_buttons[name] = button

    def show_tab(self, name):
        """Raise the given tab and highlight its button."""
        self.current_tab = name
        self.tabs[name].tkraise()
        for tab_name, button in self.tab_buttons.items():
            button.config(variant="tab_active" if tab_name == name else "tab")
        if name == "Stats":
            self.refresh_stats()

    def add_tab(self, name):
        """Create a scrollable tab page and return a Form to fill it."""
        page = theme.ScrollFrame(self.tab_container)
        page.grid(row=0, column=0, sticky="nsew")
        page.inner.configure(padx=24, pady=20)
        self.tabs[name] = page
        return theme.Form(page.inner)

    def add_field(self, form, label, hint=None, live_preview=True, reset_key=None):
        """Add a labelled text input to a form and return the entry.

        With reset_key, a button beside the input restores the value from the
        game database after it has been edited.
        """
        var = tk.StringVar()
        self.field_vars.append(var)
        if live_preview:
            var.trace_add("write", self.update_preview)
        form.add(theme.section_label(form.body, label), pady=(0, 6))
        row = tk.Frame(form.body, bg=theme.BG)
        row.columnconfigure(0, weight=1)
        box, entry = theme.make_entry(row, textvariable=var)
        box.grid(row=0, column=0, sticky="ew")
        if reset_key:
            button = self.icon_button(row, "⟲", command=lambda: self.reset_field(entry, reset_key))
            button.grid(row=0, column=1, sticky="ns", padx=(8, 0))
            self.reset_buttons.append((entry, reset_key, button))
        form.add(row, pady=(0, 0 if hint else 16))
        if hint:
            form.add(theme.hint_label(form.body, hint), pady=(6, 16))
        return entry

    @staticmethod
    def icon_button(parent, glyph, command=None, variant="icon"):
        """Small square button holding a single symbol."""
        return theme.FlatButton(parent, text=glyph, variant=variant, padx=10, pady=0,
                                font=(theme.SYMBOL, 11), command=command)

    def reset_field(self, entry, key):
        """Restore a field to the value stored in the game database."""
        if self.loaded_game:
            entry.delete(0, tk.END)
            entry.insert(0, self.loaded_game.get(key, ''))

    def build_presence_tab(self):
        """Game picker, presence text and a live Discord-style preview."""
        form = self.add_tab("Presence")
        form.add(self.build_preview_card(form.body), pady=(0, 20))

        # Console dropdown
        form.add(theme.section_label(form.body, "Console"), pady=(0, 6))
        self.console_combo = ttk.Combobox(form.body, state='readonly', font=theme.FONT_BODY)
        form.add(self.console_combo, pady=(0, 16))
        self.console_combo.bind('<<ComboboxSelected>>', self.on_console_selected)
        # Populate consoles if available
        try:
            consoles = self.db.get_consoles() if self.db else []
            self.console_combo['values'] = consoles
            if consoles:
                self.console_combo.set(consoles[0])
        except Exception:
            self.console_combo['values'] = []

        # Game box: pick from the list, or type to filter it
        form.add(theme.section_label(form.body, "Game"), pady=(0, 6))
        row = tk.Frame(form.body, bg=theme.BG)
        row.columnconfigure(0, weight=1)
        self.game_combo = ttk.Combobox(row, font=theme.FONT_BODY)
        self.game_combo.grid(row=0, column=0, sticky="ew")
        self.game_check = tk.Label(row, text="✔", bg=theme.BG, fg=theme.BG, font=(theme.SYMBOL, 12))
        self.game_check.grid(row=0, column=1, padx=(8, 0))
        form.add(row)
        self.game_hint = theme.hint_label(form.body, "")
        form.add(self.game_hint, pady=(6, 0))
        # Initialize games based on selected console
        initial_console = self.console_combo.get()
        try:
            if initial_console:
                titles = self.db.get_all_game_titles_by_console(initial_console)
            else:
                titles = self.db.get_all_game_titles()
        except Exception:
            titles = []
        self.set_game_titles(titles)
        self.game_combo.bind('<<ComboboxSelected>>', self.on_game_selected)
        self.game_combo.bind('<KeyRelease>', self.on_game_typed)
        self.game_combo.bind('<Return>', self.on_game_selected)
        self.game_combo.bind('<FocusOut>', self.on_game_selected)

        form.add(theme.divider(form.body), pady=20)

        self.details_entry = self.add_field(form, "Details", "The first line shown under the game name.",
                                            reset_key='Details')
        self.state_entry = self.add_field(form, "State", "The second line, e.g. what you're doing in game.",
                                          reset_key='State')

        # Party size: "(1 of 4)" after the state line
        form.add(theme.section_label(form.body, "Party size"), pady=(0, 6))
        row = tk.Frame(form.body, bg=theme.BG)
        self.party_vars = []
        for i in range(2):
            var = tk.StringVar()
            var.trace_add("write", self.update_preview)
            self.party_vars.append(var)
            box, entry = theme.make_entry(row, textvariable=var)
            entry.config(width=5, justify="center")
            box.grid(row=0, column=i * 2)
        tk.Label(row, text="of", bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_BODY).grid(
            row=0, column=1, padx=10)
        form.add(row, sticky="w")
        form.add(theme.hint_label(form.body, "Optional, e.g. 1 of 4. Leave empty to hide. Shown "
                                             "after the state line."), pady=(6, 16))

        form.add(theme.divider(form.body), pady=(4, 20))

        # Show elapsed time toggle
        row = tk.Frame(form.body, bg=theme.BG)
        row.columnconfigure(0, weight=1)
        tk.Label(row, text="Show elapsed time", bg=theme.BG, fg=theme.TEXT_STRONG,
                 font=theme.FONT_BODY).grid(row=0, column=0, sticky="w")
        self.show_time_var = tk.BooleanVar(value=True)
        self.show_time_var.trace_add("write", self.update_preview)
        theme.Toggle(row, variable=self.show_time_var).grid(row=0, column=1, sticky="e")
        form.add(row)
        form.add(theme.hint_label(form.body, "Displays a timer that starts when you apply your status. "
                                             "Also toggled by the ⌛ button below."), pady=(6, 0))

    def build_preview_card(self, parent):
        """Card mimicking the 'Playing' activity on a Discord profile."""
        card = tk.Frame(parent, bg=theme.CARD, padx=16, pady=14)
        card.columnconfigure(1, weight=1)
        tk.Label(card, text="Playing", bg=theme.CARD, fg=theme.TEXT,
                 font=theme.FONT_HEADING).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.preview_art = tk.Canvas(card, width=72, height=72, bg=theme.CARD, highlightthickness=0)
        theme.round_rect(self.preview_art, 0, 0, 64, 64, 10, fill=theme.BLURPLE)
        self.preview_initials = self.preview_art.create_text(32, 32, text="?", fill="#FFFFFF",
                                                             font=theme.FONT_DISPLAY)
        self.preview_small = self.preview_art.create_oval(46, 46, 70, 70, fill=theme.BG_TERTIARY,
                                                          outline=theme.CARD, width=3)
        self.preview_art.grid(row=1, column=0, sticky="nw", padx=(0, 10))

        text = tk.Frame(card, bg=theme.CARD)
        text.grid(row=1, column=1, sticky="nsew")
        self.preview_title = tk.Label(text, bg=theme.CARD, fg=theme.TEXT_STRONG, anchor="w",
                                      font=theme.FONT_BODY_LARGE)
        self.preview_details = tk.Label(text, bg=theme.CARD, fg=theme.TEXT, anchor="w",
                                        font=theme.FONT_BODY)
        self.preview_state = tk.Label(text, bg=theme.CARD, fg=theme.TEXT, anchor="w",
                                      font=theme.FONT_BODY)
        self.preview_timer = tk.Label(text, bg=theme.CARD, fg=theme.GREEN, anchor="w",
                                      font=theme.FONT_BUTTON)
        for row, label in enumerate((self.preview_title, self.preview_details,
                                     self.preview_state, self.preview_timer)):
            label.grid(row=row, column=0, sticky="w")
        return card

    def build_images_tab(self):
        """Asset key and hover text inputs."""
        form = self.add_tab("Images")
        form.add(theme.hint_label(form.body,
                                  "Discord only shows images uploaded as Art Assets under Rich Presence "
                                  "in the Developer Portal. Enter the asset key (its name), not a URL."),
                 pady=(0, 20))
        self.large_image_entry = self.add_field(form, "Large image (asset key)", reset_key='Large Image')
        self.large_text_entry = self.add_field(form, "Large image text",
                                               "Shown when hovering over the large image.",
                                               reset_key='Large Image Text')
        form.add(theme.divider(form.body), pady=(4, 20))
        self.small_image_entry = self.add_field(form, "Small image (asset key)",
                                                "Shown as a badge in the corner of the large image.",
                                                reset_key='Small Image')
        self.small_text_entry = self.add_field(form, "Small image text",
                                               "Shown when hovering over the small image.",
                                               reset_key='Small Image Text')

    def build_stats_tab(self):
        """Playtime dashboard built from the logged sessions."""
        form = self.add_tab("Stats")

        segment = tk.Frame(form.body, bg=theme.BG)
        self.period_buttons = {}
        for i, period in enumerate(stats.PERIODS):
            segment.columnconfigure(i, weight=1, uniform="period")
            button = theme.FlatButton(segment, text=period, variant="tab", font=theme.FONT_BUTTON, padx=6,
                                      command=lambda p=period: self.select_stats_period(p))
            button.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            self.period_buttons[period] = button
        form.add(segment, pady=(0, 20))

        self.stats_headline = tk.Label(form.body, bg=theme.BG, fg=theme.TEXT_STRONG, anchor="w",
                                       justify="left", font=theme.FONT_BODY_LARGE, wraplength=470)
        form.add(self.stats_headline, pady=(0, 16))

        tiles = tk.Frame(form.body, bg=theme.BG)
        self.stat_values = {}
        for i, name in enumerate(("Total", "Sessions", "Avg session")):
            tiles.columnconfigure(i, weight=1, uniform="tiles")
            tile = tk.Frame(tiles, bg=theme.CARD, padx=12, pady=10)
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            theme.section_label(tile, name, bg=theme.CARD).pack(anchor="w")
            value = tk.Label(tile, bg=theme.CARD, fg=theme.TEXT_STRONG, font=theme.FONT_TITLE, anchor="w")
            value.pack(anchor="w", pady=(8, 0))
            self.stat_values[name] = value
        form.add(tiles, pady=(0, 24))

        self.chart_title = theme.section_label(form.body, "Playtime per day")
        form.add(self.chart_title, pady=(0, 8))
        self.chart = tk.Canvas(form.body, height=170, bg=theme.BG, highlightthickness=0)
        form.add(self.chart, pady=(0, 24))
        self.chart_buckets = []
        self.chart_geometry = None
        self.chart.bind("<Configure>", lambda e: self.draw_chart())
        self.chart.bind("<Motion>", self.on_chart_hover)
        self.chart.bind("<Leave>", lambda e: self.draw_chart())

        form.add(theme.section_label(form.body, "Top games"), pady=(0, 8))
        self.top_games_frame = tk.Frame(form.body, bg=theme.BG)
        self.top_games_frame.columnconfigure(0, weight=1)
        form.add(self.top_games_frame, pady=(0, 24))

        form.add(theme.section_label(form.body, "Recent sessions"), pady=(0, 8))
        self.recent_frame = tk.Frame(form.body, bg=theme.BG)
        self.recent_frame.columnconfigure(0, weight=1)
        form.add(self.recent_frame, pady=(0, 20))

        form.add(theme.divider(form.body), pady=(0, 16))
        idle = (f"pause after {self.idle_minutes} minutes without keyboard or mouse input"
                if self.idle_minutes else "do not pause when idle")
        form.add(theme.hint_label(form.body,
                                  f"Sessions are logged automatically while your presence is set, and {idle}. "
                                  f"Stored locally at {self.session_logger.db_path}"))
        self.refresh_period_buttons()

    def select_stats_period(self, period):
        self.stats_period = period
        self.refresh_period_buttons()
        self.refresh_stats()

    def refresh_period_buttons(self):
        for period, button in self.period_buttons.items():
            button.config(variant="tab_active" if period == self.stats_period else "tab")

    def session_heartbeat(self):
        """Once a minute: keep the session log alive and the Stats tab fresh."""
        was_active = self.session_logger.active
        self.session_logger.heartbeat()
        if was_active and not self.session_logger.active:
            self.log_message(f"Session paused: idle for {self.idle_minutes}+ minutes")
        elif not was_active and self.session_logger.active:
            self.log_message("Session resumed")
        if self.current_tab == "Stats":
            self.refresh_stats()
        self.root.after(HEARTBEAT_SECONDS * 1000, self.session_heartbeat)

    def refresh_stats(self):
        """Rebuild the derived tables and redraw the Stats tab."""
        try:
            pipeline.run(self.session_logger.db_path, current_run=self.session_logger.run_id)
            summary = stats.summarize(self.stats_period, self.session_logger.db_path)
        except Exception as e:
            self.log_message(f"ERROR: Failed to load stats - {e}")
            return

        self.stats_headline.config(text=summary["headline"] or
                                   "No sessions yet. Set your presence for a game and your playtime "
                                   "will show up here.")
        self.stat_values["Total"].config(text=stats.format_duration(summary["total"]))
        self.stat_values["Sessions"].config(text=str(summary["session_count"]))
        self.stat_values["Avg session"].config(text=stats.format_duration(summary["avg_session"]))

        self.chart_title.config(text="PLAYTIME PER MONTH" if self.stats_period == "All time"
                                else "PLAYTIME PER DAY")
        self.chart_buckets = summary["buckets"]
        self.draw_chart()
        self.fill_top_games(summary["top_games"][:5])
        self.fill_recent(summary["recent"])

    def draw_chart(self, hover=None):
        """Column chart of playtime per bucket, drawn on a canvas."""
        c = self.chart
        c.delete("all")
        width, height = c.winfo_width(), int(c.cget("height"))
        buckets = self.chart_buckets
        if width < 50 or not buckets or not any(s for _, s, _ in buckets):
            self.chart_geometry = None
            c.create_text(width / 2, height / 2, text="Nothing to chart yet", fill=theme.TEXT_MUTED,
                          font=theme.FONT_SMALL)
            return

        left, top, bottom = 34, 18, height - 22
        peak_hours = max(s for _, s, _ in buckets) / 3600
        step = next((n for n in (0.5, 1, 2, 4, 5, 10, 20, 25, 50, 100) if peak_hours / n <= 3), 200)
        ticks = max(1, -int(-peak_hours // step))
        scale_max = ticks * step * 3600

        # Recessive hairline grid with hour labels
        for i in range(ticks + 1):
            y = bottom - (bottom - top) * i / ticks
            c.create_line(left, y, width, y, fill=theme.DIVIDER)
            c.create_text(left - 6, y, text=f"{step * i:g}h", anchor="e", fill=theme.TEXT_MUTED,
                          font=theme.FONT_SMALL)

        n = len(buckets)
        slot = (width - left) / n
        bar = max(2, min(24, slot - 2))
        label_every = 1 if n <= 12 else 5
        peak_index = max(range(n), key=lambda i: buckets[i][1])
        self.chart_geometry = (left, slot)
        for i, (axis_label, seconds, _) in enumerate(buckets):
            cx = left + slot * i + slot / 2
            x1, x2 = cx - bar / 2, cx + bar / 2
            if seconds > 0:
                # Rounded data-end, square at the baseline
                y = bottom - (bottom - top) * seconds / scale_max
                fill = theme.BLURPLE_HOVER if i == hover else theme.BLURPLE
                radius = min(4, bar / 2)
                if bottom - y > radius * 2:
                    theme.round_rect(c, x1, y, x2, bottom, radius, fill=fill)
                    c.create_rectangle(x1, y + radius, x2, bottom, fill=fill, outline="")
                else:
                    c.create_rectangle(x1, min(y, bottom - 1), x2, bottom, fill=fill, outline="")
                if i == peak_index and hover is None:
                    c.create_text(cx, y - 4, text=stats.format_duration(seconds), anchor="s",
                                  fill=theme.TEXT, font=theme.FONT_SMALL)
            if i % label_every == 0 or (i == n - 1 and (n - 1) % label_every >= 3):
                c.create_text(cx, bottom + 4, text=axis_label, anchor="n", fill=theme.TEXT_MUTED,
                              font=theme.FONT_SMALL)

        if hover is not None:
            _, seconds, tooltip = buckets[hover]
            text = f"{tooltip}  {stats.format_duration(seconds) if seconds else 'no play'}"
            cx = left + slot * hover + slot / 2
            item = c.create_text(0, 0, text=text, anchor="n", fill=theme.TEXT_STRONG, font=theme.FONT_BODY)
            x1, _, x2, _ = c.bbox(item)
            half = (x2 - x1) / 2
            c.coords(item, min(max(cx, left + half + 8), width - half - 8), 0)
            x1, y1, x2, y2 = c.bbox(item)
            box = c.create_rectangle(x1 - 8, y1, x2 + 8, y2, fill=theme.BG_TERTIARY, outline="")
            c.tag_raise(item, box)

    def on_chart_hover(self, event):
        if not self.chart_geometry:
            return
        left, slot = self.chart_geometry
        index = int((event.x - left) // slot)
        self.draw_chart(hover=index if 0 <= index < len(self.chart_buckets) else None)

    def fill_top_games(self, games):
        """Ranked list of the most played games with proportional bars."""
        for child in self.top_games_frame.winfo_children():
            child.destroy()
        if not games:
            theme.hint_label(self.top_games_frame, "No games played in this period.").grid(sticky="w")
            return
        peak = games[0][2] or 1
        for row, (game, console, seconds) in enumerate(games):
            name = theme.ellipsize(game, 30) + (f"  ·  {console}" if console else "")
            tk.Label(self.top_games_frame, text=name, bg=theme.BG, fg=theme.TEXT, anchor="w",
                     font=theme.FONT_BODY).grid(row=row * 2, column=0, sticky="w")
            tk.Label(self.top_games_frame, text=stats.format_duration(seconds), bg=theme.BG,
                     fg=theme.TEXT_STRONG, font=theme.FONT_BODY).grid(row=row * 2, column=1, sticky="e")
            track = tk.Canvas(self.top_games_frame, height=6, bg=theme.BG, highlightthickness=0)
            track.grid(row=row * 2 + 1, column=0, columnspan=2, sticky="ew", pady=(2, 10))
            track.bind("<Configure>", lambda e, t=track, f=seconds / peak: self.draw_track(t, f))

    @staticmethod
    def draw_track(canvas, fraction):
        canvas.delete("all")
        width = canvas.winfo_width()
        theme.round_rect(canvas, 0, 0, width, 6, 3, fill=theme.BG_TERTIARY)
        theme.round_rect(canvas, 0, 0, max(6, width * fraction), 6, 3, fill=theme.BLURPLE)

    def fill_recent(self, sessions):
        """Latest sessions in this period, newest first."""
        for child in self.recent_frame.winfo_children():
            child.destroy()
        if not sessions:
            theme.hint_label(self.recent_frame, "No sessions in this period.").grid(sticky="w")
            return
        for row, (start, _end, seconds, game, console, is_open) in enumerate(sessions):
            card = tk.Frame(self.recent_frame, bg=theme.CARD, padx=12, pady=6)
            card.grid(row=row, column=0, sticky="ew", pady=(0, 6))
            card.columnconfigure(0, weight=1)
            tk.Label(card, text=theme.ellipsize(game, 34), bg=theme.CARD, fg=theme.TEXT_STRONG,
                     anchor="w", font=theme.FONT_BODY).grid(row=0, column=0, sticky="w")
            when = datetime.fromtimestamp(start).strftime("%a %d %b, %H:%M")
            tk.Label(card, text=when + (f"  ·  {console}" if console else ""), bg=theme.CARD,
                     fg=theme.TEXT_MUTED, anchor="w", font=theme.FONT_SMALL).grid(row=1, column=0, sticky="w")
            duration = stats.format_duration(seconds) + ("  ● now" if is_open else "")
            tk.Label(card, text=duration, bg=theme.CARD, fg=theme.GREEN if is_open else theme.TEXT,
                     font=theme.FONT_BODY).grid(row=0, column=1, rowspan=2, sticky="e")

    def build_settings_tab(self):
        """Client ID and database source settings."""
        form = self.add_tab("Settings")

        self.client_id_entry = self.add_field(form, "Discord Client ID",
                                              "Your Application ID from the Discord Developer Portal.",
                                              live_preview=False)
        if self.client_id:
            self.client_id_entry.insert(0, self.client_id)

        form.add(theme.divider(form.body), pady=(4, 20))

        row = tk.Frame(form.body, bg=theme.BG)
        row.columnconfigure(0, weight=1)
        tk.Label(row, text="Keep timer when switching games", bg=theme.BG, fg=theme.TEXT_STRONG,
                 font=theme.FONT_BODY).grid(row=0, column=0, sticky="w")
        self.keep_timer_var = tk.BooleanVar(value=self.keep_timer)
        theme.Toggle(row, variable=self.keep_timer_var).grid(row=0, column=1, sticky="e")
        form.add(row)
        form.add(theme.hint_label(form.body, "Your elapsed time won't reset when you apply a different game."),
                 pady=(6, 0))

        form.add(theme.divider(form.body), pady=20)

        # Database source segmented control
        form.add(theme.section_label(form.body, "Database source"), pady=(0, 6))
        self.db_source_var = tk.StringVar(value="Google Sheets" if self.use_google_sheets else "Local File")
        segment = tk.Frame(form.body, bg=theme.BG)
        self.source_buttons = {}
        for i, value in enumerate(("Local File", "Google Sheets")):
            segment.columnconfigure(i, weight=1, uniform="source")
            button = theme.FlatButton(segment, text=value, variant="tab", font=theme.FONT_BUTTON,
                                      command=lambda v=value: self.select_db_source(v))
            button.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            self.source_buttons[value] = button
        form.add(segment, pady=(0, 16))
        self.db_source_var.trace_add("write", self.refresh_source_buttons)
        self.refresh_source_buttons()

        holder = tk.Frame(form.body, bg=theme.BG)
        holder.columnconfigure(0, weight=1)
        form.add(holder)

        # Local file selection
        self.local_file_frame = tk.Frame(holder, bg=theme.BG)
        self.local_file_frame.grid(row=0, column=0, sticky="ew")
        self.local_file_frame.columnconfigure(0, weight=1)
        theme.section_label(self.local_file_frame, "Database file").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        box, self.local_file_entry = theme.make_entry(self.local_file_frame)
        box.grid(row=1, column=0, sticky="ew")
        # Prefill default if exists
        default_local = 'games_database.xlsx'
        if os.path.exists(default_local):
            self.local_file_entry.insert(0, default_local)
        self.browse_file_button = theme.FlatButton(self.local_file_frame, text="Browse", variant="secondary",
                                                   command=self.browse_local_file)
        self.browse_file_button.grid(row=1, column=1, sticky="ns", padx=(8, 0))
        self.load_local_button = theme.FlatButton(self.local_file_frame, text="Load",
                                                  command=self.load_local_file)
        self.load_local_button.grid(row=1, column=2, sticky="ns", padx=(8, 0))
        theme.hint_label(self.local_file_frame, "Excel (.xlsx) or CSV file with your games.").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # Google Sheets URL entry
        self.sheets_url_frame = tk.Frame(holder, bg=theme.BG)
        self.sheets_url_frame.grid(row=0, column=0, sticky="ew")
        self.sheets_url_frame.columnconfigure(0, weight=1)
        theme.section_label(self.sheets_url_frame, "Google Sheets URL").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        box, self.sheets_url_entry = theme.make_entry(self.sheets_url_frame)
        box.grid(row=1, column=0, sticky="ew")
        if self.google_sheet_url:
            self.sheets_url_entry.insert(0, self.google_sheet_url)
        self.load_sheets_button = theme.FlatButton(self.sheets_url_frame, text="Load",
                                                   command=self.load_google_sheets)
        self.load_sheets_button.grid(row=1, column=1, sticky="ns", padx=(8, 0))
        help_link = tk.Label(self.sheets_url_frame, text="How do I set up Google Sheets?",
                             bg=theme.BG, fg=theme.LINK, font=theme.FONT_SMALL, cursor="hand2")
        help_link.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        help_link.bind("<Button-1>", lambda e: self.show_google_sheets_help())

        # Update state based on current source
        if self.use_google_sheets:
            self.local_file_frame.grid_remove()
        else:
            self.sheets_url_entry.config(state=tk.DISABLED)
            self.load_sheets_button.config(state=tk.DISABLED)
            self.sheets_url_frame.grid_remove()

        form.add(theme.divider(form.body), pady=20)

        form.add(theme.FlatButton(form.body, text="Reload Database", variant="secondary",
                                  command=self.reload_database), sticky="w")
        form.add(theme.hint_label(form.body, "Re-read the current source after editing your games."),
                 pady=(6, 0))

    def build_log_tab(self):
        """Activity log page."""
        page = tk.Frame(self.tab_container, bg=theme.BG, padx=24, pady=20)
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        self.tabs["Log"] = page

        theme.section_label(page, "Activity log").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.log_text = tk.Text(page, bg=theme.BG_TERTIARY, fg=theme.TEXT, font=theme.FONT_BODY,
                                relief="flat", bd=0, highlightthickness=0, padx=10, pady=8,
                                wrap=tk.WORD, state=tk.DISABLED, selectbackground=theme.BLURPLE)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(page, orient="vertical", style="Dark.Vertical.TScrollbar",
                                  command=self.log_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.tag_configure("time", foreground=theme.TEXT_MUTED)
        self.log_text.tag_configure("error", foreground=theme.RED)
        self.log_text.tag_configure("warning", foreground=theme.YELLOW)

    def build_footer(self):
        """Bottom bar with the main action, timer and secondary actions."""
        footer = tk.Frame(self.root, bg=theme.BG_SECONDARY, padx=16, pady=12)
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        self.primary_button = theme.FlatButton(footer, pady=8)
        self.primary_button.grid(row=0, column=0, sticky="ew")
        self.time_button = self.icon_button(footer, "⌛",
                                            command=lambda: self.show_time_var.set(not self.show_time_var.get()))
        self.time_button.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.timer_label = tk.Label(footer, bg=theme.BG_TERTIARY, fg=theme.TEXT_MUTED,
                                    font=theme.FONT_BUTTON, padx=10, width=8)
        self.timer_label.grid(row=0, column=2, sticky="ns", padx=(4, 0))
        self.clear_button = theme.FlatButton(footer, text="Clear", variant="secondary", pady=8,
                                             command=self.clear_presence)
        self.clear_button.grid(row=0, column=3, sticky="ns", padx=(8, 0))
        self.disconnect_button = theme.FlatButton(footer, text="Disconnect", variant="danger", pady=8,
                                                  command=self.disconnect_discord)
        self.disconnect_button.grid(row=0, column=4, sticky="ns", padx=(8, 0))

    def set_connected(self, connected):
        """Reflect the Discord connection state across the UI."""
        self.connected = connected
        state = tk.NORMAL if connected else tk.DISABLED
        self.clear_button.config(state=state)
        self.disconnect_button.config(state=state)
        if not connected:
            self.applied = None
        self.show_discord_user(self.rpc.user if (connected and self.rpc) else None)
        if connected:
            self.connection_status.config(text="Connected", fg=theme.GREEN)
        else:
            self.connection_status.config(text="Disconnected", fg=theme.TEXT_MUTED)
        self.refresh_primary_button()

    def presence_fields(self):
        """Everything that ends up in the Discord status, for change detection."""
        return (self.game_combo.get().strip(),
                *(e.get().strip() for e in (self.details_entry, self.state_entry,
                                             self.large_image_entry, self.large_text_entry,
                                             self.small_image_entry, self.small_text_entry)),
                self.show_time_var.get(), tuple(self.party_size() or ()))

    def party_size(self):
        """[current, max] from the party inputs, or None when empty or invalid."""
        try:
            current, maximum = (int(v.get()) for v in self.party_vars)
        except ValueError:
            return None
        return [current, maximum] if 0 < current <= maximum else None

    def refresh_primary_button(self):
        """Connect -> Apply status -> No pending changes, like a save button."""
        if not self.connected:
            self.primary_button.config(text="Connect to Discord", variant="success",
                                       state=tk.NORMAL, command=self.connect_discord)
        elif self.presence_fields() != self.applied:
            self.primary_button.config(text="Apply status", variant="primary",
                                       state=tk.NORMAL, command=self.update_presence)
        else:
            self.primary_button.config(text="No pending changes", variant="primary",
                                       state=tk.DISABLED)

    def select_db_source(self, source):
        """Handle a click on the database source segmented control."""
        if self.db_source_var.get() != source:
            self.db_source_var.set(source)
            self.on_db_source_change()

    def refresh_source_buttons(self, *_):
        """Highlight the active database source."""
        for value, button in self.source_buttons.items():
            button.config(variant="tab_active" if value == self.db_source_var.get() else "tab")

    def elapsed_text(self):
        """Elapsed time of the current presence as h:mm:ss / m:ss."""
        seconds = int(time.time()) - self.start_time if (self.connected and self.start_time) else 0
        hours, rest = divmod(max(seconds, 0), 3600)
        minutes, seconds = divmod(rest, 60)
        return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"

    def update_preview(self, *_):
        """Refresh the 'Playing' preview card from the current inputs."""
        title = self.game_combo.get().strip()
        words = [w for w in title.split() if w[0].isalnum()]
        initials = "".join(w[0] for w in words[:2]).upper() or "?"
        self.preview_art.itemconfig(self.preview_initials, text=initials)
        self.preview_title.config(text=theme.ellipsize(title or "No game selected", 32))

        party = self.party_size()
        state_text = self.state_entry.get().strip()
        if party:
            state_text = f"{state_text} ({party[0]} of {party[1]})".strip()
        for label, value in ((self.preview_details, self.details_entry.get().strip()),
                             (self.preview_state, state_text)):
            label.config(text=theme.ellipsize(value, 40))
            if value:
                label.grid()
            else:
                label.grid_remove()

        has_small = bool(getattr(self, "small_image_entry", None) and self.small_image_entry.get().strip())
        self.preview_art.itemconfig(self.preview_small, state="normal" if has_small else "hidden")

        if self.show_time_var.get():
            self.preview_timer.config(text=f"▶ {self.elapsed_text()}")
            self.preview_timer.grid()
        else:
            self.preview_timer.grid_remove()

        if hasattr(self, "primary_button"):
            self.refresh_controls()

    def refresh_controls(self):
        """Sync buttons and markers that depend on the current inputs."""
        self.refresh_primary_button()
        self.time_button.config(variant="icon_active" if self.show_time_var.get() else "icon")
        known = self.game_combo.get().strip() in self.game_titles
        self.game_check.config(fg=theme.GREEN if known else theme.BG)
        for entry, key, button in self.reset_buttons:
            changed = bool(self.loaded_game) and entry.get() != str(self.loaded_game.get(key, ''))
            button.config(state=tk.NORMAL if changed else tk.DISABLED)

    def tick(self):
        """Once-a-second refresh of timers."""
        self.update_preview()
        running = self.connected and self.start_time
        self.timer_label.config(text=self.elapsed_text(),
                                fg=theme.TEXT if running else theme.TEXT_MUTED)
        self.root.after(1000, self.tick)

    def log_message(self, message):
        """Add a message to the activity log."""
        if message.startswith("ERROR"):
            tag = "error"
        elif message.startswith("WARNING"):
            tag = "warning"
        else:
            tag = ()
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] ", "time")
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def connect_discord(self):
        """Connect to Discord Rich Presence."""
        # Get client ID from entry if not loaded from config
        client_id = self.client_id_entry.get().strip()
        
        if not client_id or client_id == "YOUR_CLIENT_ID_HERE":
            messagebox.showerror("Error", "Please enter a valid Discord Client ID.\n\n"
                               "Get one from: https://discord.com/developers/applications")
            self.log_message("ERROR: Invalid Client ID")
            return
        
        self.client_id = client_id
        self.rpc = DiscordRPC(self.client_id)
        
        if self.rpc.connect():
            self.set_connected(True)
            self.log_message("Successfully connected to Discord")
        else:
            messagebox.showerror("Connection Error", 
                               "Failed to connect to Discord.\n\n"
                               "Make sure Discord is running and the Client ID is correct.")
            self.log_message("ERROR: Failed to connect to Discord")
    
    def disconnect_discord(self):
        """Disconnect from Discord Rich Presence."""
        if self.rpc:
            self.rpc.disconnect()
            self.session_logger.stop("disconnect")
            self.set_connected(False)
            self.log_message("Disconnected from Discord")
    
    def reload_database(self):
        """Reload the game database."""
        try:
            self.db.reload_database()
            # Refresh consoles list
            consoles = self.db.get_consoles()
            self.console_combo['values'] = consoles
            if consoles and (self.console_combo.get() not in consoles):
                self.console_combo.set(consoles[0])

            # Refresh games based on selected console
            current_console = self.console_combo.get() if consoles else None
            titles = self.db.get_all_game_titles_by_console(current_console) if current_console else []
            self.set_game_titles(titles)
            self.log_message(f"Database reloaded. {sum(len(self.db.get_all_game_titles_by_console(c)) for c in consoles)} games across {len(consoles)} consoles.")
            messagebox.showinfo("Success", "Database reloaded successfully!")
        except Exception as e:
            self.log_message(f"ERROR: Failed to reload database - {e}")
            messagebox.showerror("Error", f"Failed to reload database:\n{e}")

    def on_console_selected(self, event):
        """Update games list when console changes."""
        try:
            console = self.console_combo.get()
            titles = self.db.get_all_game_titles_by_console(console)
            self.set_game_titles(titles)
            if titles:
                self.game_combo.set(titles[0])
            self.log_message(f"Console selected: {console} ({len(titles)} games)")
        except Exception as e:
            self.log_message(f"ERROR: Failed to update games for console - {e}")
    
    def on_db_source_change(self):
        """Handle database source radio button change."""
        source = self.db_source_var.get()
        
        if source == "Google Sheets":
            # Show Sheets frame and enable widgets
            try:
                self.sheets_url_frame.grid()
            except Exception:
                pass
            self.sheets_url_entry.config(state=tk.NORMAL)
            self.load_sheets_button.config(state=tk.NORMAL)
            # Hide Local frame
            try:
                self.local_file_frame.grid_remove()
            except Exception:
                pass
            self.log_message("Switched to Google Sheets mode")
        else:
            # Hide Sheets frame and disable widgets
            self.sheets_url_entry.config(state=tk.DISABLED)
            self.load_sheets_button.config(state=tk.DISABLED)
            try:
                self.sheets_url_frame.grid_remove()
            except Exception:
                pass
            # Show Local frame
            try:
                self.local_file_frame.grid()
            except Exception:
                pass
            # Switch back to local file using default path if provided
            try:
                path = self.local_file_entry.get().strip()
                if self.db:
                    self.db.switch_to_local_file(db_path=path if path else None)
                else:
                    self.db = GameDatabase()
                # Refresh dropdowns
                consoles = self.db.get_consoles()
                self.console_combo['values'] = consoles
                if consoles:
                    self.console_combo.set(consoles[0])
                    titles = self.db.get_all_game_titles_by_console(consoles[0])
                else:
                    titles = []
                self.set_game_titles(titles)
                self.log_message("Switched to local file mode")
            except Exception as e:
                self.log_message(f"ERROR: Failed to switch to local file - {e}")

    def browse_local_file(self):
        """Open a file dialog to select a local database file."""
        filetypes = (
            ("Excel files", "*.xlsx *.xls"),
            ("CSV files", "*.csv"),
            ("All files", "*.*"),
        )
        filename = filedialog.askopenfilename(title="Select database file", filetypes=filetypes)
        if filename:
            self.local_file_entry.delete(0, tk.END)
            self.local_file_entry.insert(0, filename)
            self.log_message(f"Selected local file: {os.path.basename(filename)}")

    def load_local_file(self):
        """Load the selected local database file and refresh UI."""
        path = self.local_file_entry.get().strip()
        if not path:
            messagebox.showwarning("No file selected", "Please choose a local database file.")
            return
        if not os.path.exists(path):
            messagebox.showerror("File not found", f"The file does not exist:\n{path}")
            return
        try:
            # Switch database to selected local file
            if self.db:
                self.db.switch_to_local_file(db_path=path)
            else:
                self.db = GameDatabase()
            # Refresh consoles and games
            consoles = self.db.get_consoles()
            self.console_combo['values'] = consoles
            if consoles:
                self.console_combo.set(consoles[0])
                titles = self.db.get_all_game_titles_by_console(consoles[0])
            else:
                titles = []
            self.set_game_titles(titles)
            games_count = sum(len(self.db.get_all_game_titles_by_console(c)) for c in consoles)
            self.log_message(f"Loaded {games_count} games from local file across {len(consoles)} consoles")
            messagebox.showinfo("Success", "Local database loaded successfully!")
            self.use_google_sheets = False
        except Exception as e:
            self.log_message(f"ERROR: Failed to load local file - {e}")
            messagebox.showerror("Error", f"Failed to load local file:\n{e}")
    
    def load_google_sheets(self):
        """Load database from Google Sheets URL."""
        sheets_url = self.sheets_url_entry.get().strip()
        
        if not sheets_url:
            messagebox.showwarning("Missing URL", "Please enter a Google Sheets URL")
            return
        
        # Check for credentials file
        creds_path = self.credentials_path if self.credentials_path else "credentials.json"
        
        if not os.path.exists(creds_path):
            result = messagebox.askyesno(
                "Credentials Not Found",
                f"Credentials file '{creds_path}' not found.\n\n"
                "You need a Google Service Account credentials JSON file.\n\n"
                "Do you want to see instructions on how to create one?",
                icon='warning'
            )
            if result:
                self.show_google_sheets_help()
            return
        
        try:
            self.log_message(f"Loading Google Sheet: {sheets_url[:50]}...")
            
            # Update database to use Google Sheets
            if self.db:
                success = self.db.switch_to_google_sheets(sheets_url, creds_path)
            else:
                self.db = GameDatabase(
                    use_google_sheets=True,
                    google_sheet_url=sheets_url,
                    credentials_path=creds_path
                )
                success = True
            
            if success:
                # Refresh consoles and games from Sheets
                consoles = self.db.get_consoles()
                self.console_combo['values'] = consoles
                if consoles:
                    self.console_combo.set(consoles[0])
                    titles = self.db.get_all_game_titles_by_console(consoles[0])
                else:
                    titles = []
                self.set_game_titles(titles)
                games_count = sum(len(self.db.get_all_game_titles_by_console(c)) for c in consoles)
                self.log_message(f"Successfully loaded {games_count} games from Google Sheets across {len(consoles)} consoles")
                messagebox.showinfo("Success", 
                                  f"Loaded {games_count} games from Google Sheets!")
                self.use_google_sheets = True
                self.google_sheet_url = sheets_url
            else:
                raise Exception("Failed to load Google Sheet")
                
        except Exception as e:
            self.log_message(f"ERROR: Failed to load Google Sheets - {e}")
            messagebox.showerror("Error", 
                               f"Failed to load Google Sheet:\n\n{str(e)}\n\n"
                               "Make sure:\n"
                               "1. The sheet URL is correct\n"
                               "2. The sheet is shared with your service account email\n"
                               "3. Your credentials file is valid")
    
    def show_google_sheets_help(self):
        """Show instructions for setting up Google Sheets API."""
        help_window = tk.Toplevel(self.root)
        help_window.title("Google Sheets Setup Instructions")
        help_window.geometry("600x500")
        help_window.configure(bg=theme.BG)
        theme.apply_dark_title_bar(help_window)

        close_button = theme.FlatButton(help_window, text="Close", command=help_window.destroy)
        close_button.pack(side=tk.BOTTOM, anchor=tk.E, padx=16, pady=12)

        text = tk.Text(help_window, wrap=tk.WORD, padx=16, pady=12, bg=theme.BG_TERTIARY,
                       fg=theme.TEXT, font=theme.FONT_BODY, relief="flat", bd=0,
                       highlightthickness=0, selectbackground=theme.BLURPLE)
        scrollbar = ttk.Scrollbar(help_window, orient="vertical", style="Dark.Vertical.TScrollbar",
                                  command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(16, 0), padx=(0, 8))
        text.pack(fill=tk.BOTH, expand=True, padx=(16, 0), pady=(16, 0))
        
        instructions = """Google Sheets API Setup Instructions

1. Create a Google Cloud Project:
   - Go to https://console.cloud.google.com/
   - Create a new project (or select existing one)

2. Enable Google Sheets API:
   - In the Google Cloud Console, go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click on it and click "Enable"

3. Create Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details and click "Create"
   - Skip the optional permissions and click "Done"

4. Create and Download Key:
   - Click on the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Choose "JSON" format
   - The key file will download automatically

5. Save the Credentials File:
   - Rename the downloaded file to "credentials.json"
   - Place it in the same folder as this application
   - Or update config.ini with the path to your credentials file

6. Share Your Google Sheet:
   - Open your Google Sheet
   - Click "Share" button
   - Find the "client_email" in your credentials.json file
   - Share the sheet with that email address (viewer or editor access)
   - Example: my-service-account@my-project.iam.gserviceaccount.com

7. Get the Sheet URL:
   - Copy the full URL from your browser
   - Example: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
   - Paste it into the Google Sheets URL field in this app

That's it! Click "Load" to import your games from Google Sheets.
"""
        
        text.insert(tk.END, instructions)
        text.config(state=tk.DISABLED)
    
    def set_game_titles(self, titles):
        """Replace the game list (for a console) and clear any search filter."""
        self.game_titles = list(titles)
        self.game_combo['values'] = self.game_titles
        count = len(self.game_titles)
        if hasattr(self, "game_hint"):
            self.game_hint.config(text=f"{count} game{'s' if count != 1 else ''}. Type to search, or enter any name."
                                  if count
                                  else "Type a game name, or load a database in Settings.")

    def on_game_typed(self, event):
        """Filter the dropdown to titles containing what has been typed."""
        if event.keysym in ("Return", "Up", "Down", "Escape", "Tab"):
            return
        text = self.game_combo.get().strip().lower()
        matches = [t for t in self.game_titles if text in t.lower()] if text else self.game_titles
        self.game_combo['values'] = matches
        self.update_preview()

    def on_game_selected(self, event):
        """Load the database row when the game box holds a known title."""
        game_title = self.game_combo.get().strip()
        if game_title not in self.game_titles:
            self.loaded_game = None
            return
        if self.loaded_game is not None and self.loaded_game.get('Game Title') == game_title:
            return
        game_data = (self.db.get_game_data(game_title, self.console_combo.get() or None)
                     or self.db.get_game_data(game_title))
        self.loaded_game = game_data
        
        if game_data:
            # Populate fields with game data
            self.details_entry.delete(0, tk.END)
            self.details_entry.insert(0, game_data.get('Details', ''))
            
            self.state_entry.delete(0, tk.END)
            self.state_entry.insert(0, game_data.get('State', ''))
            
            self.large_image_entry.delete(0, tk.END)
            self.large_image_entry.insert(0, game_data.get('Large Image', ''))
            
            self.large_text_entry.delete(0, tk.END)
            self.large_text_entry.insert(0, game_data.get('Large Image Text', ''))
            
            self.small_image_entry.delete(0, tk.END)
            self.small_image_entry.insert(0, game_data.get('Small Image', ''))
            
            self.small_text_entry.delete(0, tk.END)
            self.small_text_entry.insert(0, game_data.get('Small Image Text', ''))
            
            self.log_message(f"Loaded: {game_title}")
    
    def update_presence(self):
        """Update Discord Rich Presence with current values."""
        if not self.rpc or not self.rpc.is_connected():
            messagebox.showwarning("Not Connected", "Please connect to Discord first.")
            return
        
        # Get values from entries
        details = self.details_entry.get().strip()
        state = self.state_entry.get().strip()
        large_image = self.large_image_entry.get().strip()
        large_text = self.large_text_entry.get().strip()
        small_image = self.small_image_entry.get().strip()
        small_text = self.small_text_entry.get().strip()
        show_time = self.show_time_var.get()

        # Warn if URLs are used for images (Discord RPC requires Asset Keys)
        is_large_url = large_image.lower().startswith(("http://", "https://")) if large_image else False
        is_small_url = small_image.lower().startswith(("http://", "https://")) if small_image else False
        if (is_large_url or is_small_url) and not getattr(self, "_image_url_warned", False):
            self._image_url_warned = True
            messagebox.showwarning(
                "Image URLs not supported",
                "Discord Rich Presence does not display arbitrary image URLs.\n\n"
                "Upload your images as Art Assets in your Discord application (Developer Portal) "
                "and put the asset key (name) in the 'Large Image' / 'Small Image' fields. "
                "The '* Text' fields are hover text only.\n\n"
                "We'll continue with the provided values, but images may not appear until you use asset keys."
            )
        
        # The timer restarts for a different game, unless set to keep it
        game = self.game_combo.get().strip()
        switched = self.applied is not None and self.applied[0] != game
        if not show_time:
            self.start_time = None
        elif not self.start_time or (switched and not self.keep_timer_var.get()):
            self.start_time = int(time.time())
        
        # Update presence
        success = self.rpc.update_presence(
            details=details if details else None,
            state=state if state else None,
            large_image=large_image if large_image else None,
            large_text=large_text if large_text else None,
            small_image=small_image if small_image else None,
            small_text=small_text if small_text else None,
            start_timestamp=self.start_time,
            party_size=self.party_size()
        )
        
        if success:
            self.applied = self.presence_fields()
            self.session_logger.start(game or large_text or details, self.console_combo.get().strip() or None)
            self.log_message("Presence updated successfully")
            self.refresh_primary_button()
        else:
            self.log_message("ERROR: Failed to update presence")
            messagebox.showerror("Error", "Failed to update presence. Check the log for details.")
    
    def clear_presence(self):
        """Clear Discord Rich Presence."""
        if not self.rpc or not self.rpc.is_connected():
            messagebox.showwarning("Not Connected", "Please connect to Discord first.")
            return
        
        if self.rpc.clear_presence():
            self.session_logger.stop("clear")
            self.start_time = None
            self.applied = None
            self.log_message("Presence cleared")
            self.refresh_primary_button()
        else:
            self.log_message("ERROR: Failed to clear presence")
    
    def on_closing(self):
        """Handle application closing."""
        self.session_logger.stop("exit")
        if self.rpc and self.rpc.is_connected():
            self.rpc.disconnect()
        self.root.destroy()


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = DiscordRPCApp(root)
    theme.apply_dark_title_bar(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
