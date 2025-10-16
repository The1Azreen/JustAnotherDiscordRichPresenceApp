"""
Main GUI application for Discord Rich Presence Game Selector.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import configparser
import os
from database import GameDatabase
from discord_rpc import DiscordRPC
import time


class DiscordRPCApp:
    """Main application window for Discord Rich Presence."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Discord Rich Presence - Game Selector")
        self.root.geometry("700x650")
        self.root.resizable(False, False)
        
        # Initialize variables
        self.client_id = None
        self.rpc = None
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
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(main_frame, text="Discord Rich Presence Manager",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)

        # Connection section
        connection_frame = ttk.LabelFrame(main_frame, text="Discord Connection", padding="10")
        connection_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.connection_status = ttk.Label(connection_frame, text="Status: Not Connected",
                                           foreground="red")
        self.connection_status.grid(row=0, column=0, padx=5)

        self.connect_button = ttk.Button(connection_frame, text="Connect",
                                         command=self.connect_discord)
        self.connect_button.grid(row=0, column=1, padx=5)

        self.disconnect_button = ttk.Button(connection_frame, text="Disconnect",
                                            command=self.disconnect_discord, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=2, padx=5)

        # Client ID section
        client_frame = ttk.Frame(connection_frame)
        client_frame.grid(row=1, column=0, columnspan=3, pady=5)

        ttk.Label(client_frame, text="Client ID:").grid(row=0, column=0, padx=5)
        self.client_id_entry = ttk.Entry(client_frame, width=30)
        self.client_id_entry.grid(row=0, column=1, padx=5)
        if self.client_id:
            self.client_id_entry.insert(0, self.client_id)

        # Game selection section
        game_frame = ttk.LabelFrame(main_frame, text="Game Selection", padding="10")
        game_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # Database source selection
        source_frame = ttk.Frame(game_frame)
        source_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(source_frame, text="Database Source:").grid(row=0, column=0, sticky=tk.W, padx=5)

        self.db_source_var = tk.StringVar(value="Google Sheets" if self.use_google_sheets else "Local File")
        self.local_radio = ttk.Radiobutton(source_frame, text="Local File",
                                           variable=self.db_source_var, value="Local File",
                                           command=self.on_db_source_change)
        self.local_radio.grid(row=0, column=1, padx=5)

        self.sheets_radio = ttk.Radiobutton(source_frame, text="Google Sheets",
                                            variable=self.db_source_var, value="Google Sheets",
                                            command=self.on_db_source_change)
        self.sheets_radio.grid(row=0, column=2, padx=5)

        # Google Sheets URL entry
        self.sheets_url_frame = ttk.Frame(game_frame)
        self.sheets_url_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(self.sheets_url_frame, text="Google Sheets URL:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.sheets_url_entry = ttk.Entry(self.sheets_url_frame, width=40)
        self.sheets_url_entry.grid(row=0, column=1, padx=5)
        if self.google_sheet_url:
            self.sheets_url_entry.insert(0, self.google_sheet_url)

        self.load_sheets_button = ttk.Button(self.sheets_url_frame, text="Load",
                                             command=self.load_google_sheets)
        self.load_sheets_button.grid(row=0, column=2, padx=5)

        # Local file selection
        self.local_file_frame = ttk.Frame(game_frame)
        self.local_file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(self.local_file_frame, text="Local File:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.local_file_entry = ttk.Entry(self.local_file_frame, width=40)
        self.local_file_entry.grid(row=0, column=1, padx=5)
        # Prefill default if exists
        default_local = 'games_database.xlsx'
        if os.path.exists(default_local):
            self.local_file_entry.insert(0, default_local)

        self.browse_file_button = ttk.Button(self.local_file_frame, text="Browse...",
                                             command=self.browse_local_file)
        self.browse_file_button.grid(row=0, column=2, padx=5)

        self.load_local_button = ttk.Button(self.local_file_frame, text="Load",
                                            command=self.load_local_file)
        self.load_local_button.grid(row=0, column=3, padx=5)

        # Update state based on current source
        if self.use_google_sheets:
            # Show Sheets frame, hide Local frame
            self.sheets_url_entry.config(state=tk.NORMAL)
            self.load_sheets_button.config(state=tk.NORMAL)
            try:
                self.local_file_frame.grid_remove()
            except Exception:
                pass
        else:
            # Show Local frame, hide Sheets frame
            self.sheets_url_entry.config(state=tk.DISABLED)
            self.load_sheets_button.config(state=tk.DISABLED)
            try:
                self.sheets_url_frame.grid_remove()
            except Exception:
                pass

        # Console dropdown
        ttk.Label(game_frame, text="Console:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.console_combo = ttk.Combobox(game_frame, width=25, state='readonly')
        self.console_combo.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
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
        ttk.Label(game_frame, text="Select Game:").grid(row=3, column=0, sticky=tk.W, pady=5)

        self.game_combo = ttk.Combobox(game_frame, width=40, state='readonly')
        self.game_combo.grid(row=3, column=1, padx=10, pady=5)
        # Initialize games based on selected console
        initial_console = self.console_combo.get() if hasattr(self, 'console_combo') else None
        try:
            if initial_console:
                titles = self.db.get_all_game_titles_by_console(initial_console)
            else:
                titles = self.db.get_all_game_titles()
        except Exception:
            titles = []
        self.game_combo['values'] = titles
        self.game_combo.bind('<<ComboboxSelected>>', self.on_game_selected)

        ttk.Button(game_frame, text="Reload Database",
                   command=self.reload_database).grid(row=3, column=2, padx=5)

        # Game details section
        details_frame = ttk.LabelFrame(main_frame, text="Game Details", padding="10")
        details_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Details field
        ttk.Label(details_frame, text="Details:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.details_entry = ttk.Entry(details_frame, width=50)
        self.details_entry.grid(row=0, column=1, padx=10, pady=5)

        # State field
        ttk.Label(details_frame, text="State:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.state_entry = ttk.Entry(details_frame, width=50)
        self.state_entry.grid(row=1, column=1, padx=10, pady=5)

        # Large image
        ttk.Label(details_frame, text="Large Image (Asset Key):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.large_image_entry = ttk.Entry(details_frame, width=50)
        self.large_image_entry.grid(row=2, column=1, padx=10, pady=5)

        # Large image text
        ttk.Label(details_frame, text="Large Image Text (Hover Text):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.large_text_entry = ttk.Entry(details_frame, width=50)
        self.large_text_entry.grid(row=3, column=1, padx=10, pady=5)

        # Small image
        ttk.Label(details_frame, text="Small Image (Asset Key):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.small_image_entry = ttk.Entry(details_frame, width=50)
        self.small_image_entry.grid(row=4, column=1, padx=10, pady=5)

        # Small image text
        ttk.Label(details_frame, text="Small Image Text (Hover Text):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.small_text_entry = ttk.Entry(details_frame, width=50)
        self.small_text_entry.grid(row=5, column=1, padx=10, pady=5)

        # Show elapsed time checkbox
        self.show_time_var = tk.BooleanVar(value=True)
        self.time_checkbox = ttk.Checkbutton(details_frame, text="Show Elapsed Time",
                                             variable=self.show_time_var)
        self.time_checkbox.grid(row=6, column=1, sticky=tk.W, padx=10, pady=5)

        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        self.update_button = ttk.Button(button_frame, text="Update Presence",
                                        command=self.update_presence, state=tk.DISABLED)
        self.update_button.grid(row=0, column=0, padx=5)

        self.clear_button = ttk.Button(button_frame, text="Clear Presence",
                                       command=self.clear_presence, state=tk.DISABLED)
        self.clear_button.grid(row=0, column=1, padx=5)

        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=80,
                                                  state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Initial log message
        self.log_message("Application started. Please connect to Discord.")
        if not self.client_id:
            self.log_message("WARNING: Client ID not configured. Please enter your Discord Client ID.")
    
    def log_message(self, message):
        """Add a message to the activity log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
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
            self.connection_status.config(text="Status: Connected", foreground="green")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            self.update_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)
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
            self.connection_status.config(text="Status: Not Connected", foreground="red")
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.update_button.config(state=tk.DISABLED)
            self.clear_button.config(state=tk.DISABLED)
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
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        
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
        
        close_button = ttk.Button(help_window, text="Close", command=help_window.destroy)
        close_button.pack(pady=10)
    
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
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
