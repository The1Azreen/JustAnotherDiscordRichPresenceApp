"""
Main GUI application for Discord Rich Presence Game Selector.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import configparser
import os
from database import GameDatabase
from discord_rpc import DiscordRPC
import theme
import time


TAB_NAMES = ("Presence", "Images", "Settings", "Log")


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
        
        # Load configuration
        self.load_config()
        
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
        self.build_settings_tab()
        self.build_log_tab()

        self.build_footer()

        self.show_tab("Presence")
        self.set_connected(False)
        self.tick()

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
        self.avatar.create_oval(1, 1, 37, 37, fill=theme.BLURPLE, outline="")
        self.avatar.create_text(22, 21, text="▶", fill="#FFFFFF", font=theme.FONT_TITLE)
        self.status_dot = self.avatar.create_oval(26, 26, 41, 41, fill=theme.OFFLINE,
                                                  outline=theme.BG_SECONDARY, width=3)
        self.avatar.grid(row=0, column=0, rowspan=2, padx=(0, 10))

        tk.Label(header, text="Rich Presence Manager", bg=theme.BG_SECONDARY,
                 fg=theme.TEXT_STRONG, font=theme.FONT_TITLE).grid(row=0, column=1, sticky="sw")
        self.connection_status = tk.Label(header, text="Disconnected", bg=theme.BG_SECONDARY,
                                          fg=theme.TEXT_MUTED, font=theme.FONT_SMALL)
        self.connection_status.grid(row=1, column=1, sticky="nw")

        theme.FlatButton(header, text="?", variant="ghost", padx=10, pady=2,
                         font=theme.FONT_TITLE,
                         command=self.show_google_sheets_help).grid(row=0, column=2, rowspan=2)
        theme.FlatButton(header, text="⚙", variant="ghost", padx=8, pady=2,
                         font=(theme.SYMBOL, 14),
                         command=lambda: self.show_tab("Settings")).grid(row=0, column=3, rowspan=2, padx=(4, 0))

    def build_tab_bar(self):
        """Segmented tab buttons under the header."""
        bar = tk.Frame(self.root, bg=theme.BG_SECONDARY, padx=16)
        bar.grid(row=1, column=0, sticky="ew")
        self.tab_buttons = {}
        for i, name in enumerate(TAB_NAMES):
            bar.columnconfigure(i, weight=1, uniform="tabs")
            button = theme.FlatButton(bar, text=name, variant="tab", font=theme.FONT_BUTTON,
                                      command=lambda n=name: self.show_tab(n))
            button.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0), pady=(0, 12))
            self.tab_buttons[name] = button

    def show_tab(self, name):
        """Raise the given tab and highlight its button."""
        self.tabs[name].tkraise()
        for tab_name, button in self.tab_buttons.items():
            button.config(variant="tab_active" if tab_name == name else "tab")

    def add_tab(self, name):
        """Create a scrollable tab page and return a Form to fill it."""
        page = theme.ScrollFrame(self.tab_container)
        page.grid(row=0, column=0, sticky="nsew")
        page.inner.configure(padx=24, pady=20)
        self.tabs[name] = page
        return theme.Form(page.inner)

    def add_field(self, form, label, hint=None, live_preview=True):
        """Add a labelled text input to a form and return the entry."""
        var = tk.StringVar()
        self.field_vars.append(var)
        if live_preview:
            var.trace_add("write", self.update_preview)
        form.add(theme.section_label(form.body, label), pady=(0, 6))
        box, entry = theme.make_entry(form.body, textvariable=var)
        form.add(box, pady=(0, 0 if hint else 16))
        if hint:
            form.add(theme.hint_label(form.body, hint), pady=(6, 16))
        return entry

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

        # Game dropdown
        form.add(theme.section_label(form.body, "Game"), pady=(0, 6))
        self.game_combo = ttk.Combobox(form.body, state='readonly', font=theme.FONT_BODY)
        form.add(self.game_combo)
        # Initialize games based on selected console
        initial_console = self.console_combo.get()
        try:
            if initial_console:
                titles = self.db.get_all_game_titles_by_console(initial_console)
            else:
                titles = self.db.get_all_game_titles()
        except Exception:
            titles = []
        self.game_combo['values'] = titles
        self.game_combo.bind('<<ComboboxSelected>>', self.on_game_selected)
        self.game_combo.bind('<<ComboboxSelected>>', self.update_preview, add="+")

        form.add(theme.divider(form.body), pady=20)

        self.details_entry = self.add_field(form, "Details", "The first line shown under the game name.")
        self.state_entry = self.add_field(form, "State", "The second line, e.g. what you're doing in game.")

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
        form.add(theme.hint_label(form.body, "Displays a timer that starts the first time you "
                                             "update your presence."), pady=(6, 0))

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
        self.large_image_entry = self.add_field(form, "Large image (asset key)")
        self.large_text_entry = self.add_field(form, "Large image text",
                                               "Shown when hovering over the large image.")
        form.add(theme.divider(form.body), pady=(4, 20))
        self.small_image_entry = self.add_field(form, "Small image (asset key)",
                                                "Shown as a badge in the corner of the large image.")
        self.small_text_entry = self.add_field(form, "Small image text",
                                               "Shown when hovering over the small image.")

    def build_settings_tab(self):
        """Client ID and database source settings."""
        form = self.add_tab("Settings")

        self.client_id_entry = self.add_field(form, "Discord Client ID",
                                              "Your Application ID from the Discord Developer Portal.",
                                              live_preview=False)
        if self.client_id:
            self.client_id_entry.insert(0, self.client_id)

        form.add(theme.divider(form.body), pady=(4, 20))

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
        self.timer_label = tk.Label(footer, bg=theme.BG_TERTIARY, fg=theme.TEXT_MUTED,
                                    font=theme.FONT_BUTTON, padx=10, width=8)
        self.timer_label.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.clear_button = theme.FlatButton(footer, text="Clear", variant="secondary", pady=8,
                                             command=self.clear_presence)
        self.clear_button.grid(row=0, column=2, sticky="ns", padx=(8, 0))
        self.disconnect_button = theme.FlatButton(footer, text="Disconnect", variant="danger", pady=8,
                                                  command=self.disconnect_discord)
        self.disconnect_button.grid(row=0, column=3, sticky="ns", padx=(8, 0))

    def set_connected(self, connected):
        """Reflect the Discord connection state across the UI."""
        self.connected = connected
        state = tk.NORMAL if connected else tk.DISABLED
        self.clear_button.config(state=state)
        self.disconnect_button.config(state=state)
        if connected:
            self.avatar.itemconfig(self.status_dot, fill=theme.GREEN)
            self.connection_status.config(text="Connected", fg=theme.GREEN)
            self.primary_button.config(text="Update Presence", variant="primary",
                                       command=self.update_presence)
        else:
            self.avatar.itemconfig(self.status_dot, fill=theme.OFFLINE)
            self.connection_status.config(text="Disconnected", fg=theme.TEXT_MUTED)
            self.primary_button.config(text="Connect to Discord", variant="success",
                                       command=self.connect_discord)

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

        for label, entry in ((self.preview_details, self.details_entry),
                             (self.preview_state, self.state_entry)):
            value = entry.get().strip()
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
            self.game_combo['values'] = titles
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
            self.game_combo['values'] = titles
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
                self.game_combo['values'] = titles
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
            self.game_combo['values'] = titles
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
                self.game_combo['values'] = titles
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
    
    def on_game_selected(self, event):
        """Handle game selection from dropdown."""
        game_title = self.game_combo.get()
        game_data = self.db.get_game_data(game_title)
        
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
        
        # Set start time if showing elapsed time
        if show_time and not self.start_time:
            self.start_time = int(time.time())
        elif not show_time:
            self.start_time = None
        
        # Update presence
        success = self.rpc.update_presence(
            details=details if details else None,
            state=state if state else None,
            large_image=large_image if large_image else None,
            large_text=large_text if large_text else None,
            small_image=small_image if small_image else None,
            small_text=small_text if small_text else None,
            start_timestamp=self.start_time
        )
        
        if success:
            self.log_message("Presence updated successfully")
            messagebox.showinfo("Success", "Discord Rich Presence updated!")
        else:
            self.log_message("ERROR: Failed to update presence")
            messagebox.showerror("Error", "Failed to update presence. Check the log for details.")
    
    def clear_presence(self):
        """Clear Discord Rich Presence."""
        if not self.rpc or not self.rpc.is_connected():
            messagebox.showwarning("Not Connected", "Please connect to Discord first.")
            return
        
        if self.rpc.clear_presence():
            self.start_time = None
            self.log_message("Presence cleared")
            messagebox.showinfo("Success", "Discord Rich Presence cleared!")
        else:
            self.log_message("ERROR: Failed to clear presence")
    
    def on_closing(self):
        """Handle application closing."""
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
