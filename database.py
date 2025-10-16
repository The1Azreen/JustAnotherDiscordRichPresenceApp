"""
Database module for reading game information from Excel/CSV files and Google Sheets.

Now supports multi-sheet databases where each worksheet corresponds to a console
(e.g., PS3, PS4, PS5). Provides console-aware helpers to list consoles and
filter games by console.
"""
import pandas as pd
import os
try:
    import gspread
    from google.oauth2.service_account import Credentials
    from google.auth.exceptions import GoogleAuthError
except Exception:
    # Allow module import without Google libs; will error only when used
    gspread = None
    Credentials = None
    GoogleAuthError = Exception


class GameDatabase:
    """Handles reading and managing game data from local files and Google Sheets."""
    
    def __init__(self, db_path="games_database.xlsx", use_google_sheets=False, 
                 google_sheet_url=None, credentials_path=None):
        """
        Initialize the game database.
        
        Args:
            db_path: Path to the Excel or CSV file containing game data
            use_google_sheets: Whether to load from Google Sheets instead of local file
            google_sheet_url: URL or ID of the Google Sheet
            credentials_path: Path to Google Service Account credentials JSON file
        """
        self.db_path = db_path
        self.use_google_sheets = use_google_sheets
        self.google_sheet_url = google_sheet_url
        self.credentials_path = credentials_path

        # Combined DataFrame containing all games. Will include a 'Console' column
        # when multiple worksheets are present.
        self.games_data = None  # type: pd.DataFrame | None

        # Optional mapping of console name -> DataFrame for that console
        self.games_by_console = {}  # type: dict[str, pd.DataFrame]

        # Google Sheets client
        self.gc = None

        self.load_database()

    @staticmethod
    def _normalize_sheet_df(df: pd.DataFrame, console_name: str) -> pd.DataFrame:
        """Normalize a single worksheet DataFrame to wide format with expected columns.

        Supports two input formats:
        - Wide format: columns are already the expected fields.
        - Long format: columns include ['Game Title', 'Field', 'Value'] with one row per field.
        """
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        expected_cols = [
            'Game Title', 'Details', 'State', 'Large Image',
            'Large Image Text', 'Small Image', 'Small Image Text'
        ]

        # Detect long format
        if {'Game Title', 'Field', 'Value'}.issubset(set(df.columns)):
            # Pivot to wide format
            long_df = df[['Game Title', 'Field', 'Value']].copy()
            long_df['Field'] = long_df['Field'].astype(str).str.strip()
            pivot = long_df.pivot_table(index='Game Title', columns='Field', values='Value', aggfunc='first')
            pivot = pivot.reset_index()
            # Ensure expected columns
            for col in expected_cols:
                if col not in pivot.columns:
                    pivot[col] = ""
            wide = pivot[expected_cols]
        else:
            # Treat as wide; ensure expected columns exist
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            wide = df[expected_cols]

        wide = wide.fillna("")
        wide['Console'] = console_name or 'Unknown'
        return wide
    
    def load_database(self):
        """Load the game database from local file or Google Sheets."""
        if self.use_google_sheets:
            return self.load_from_google_sheets()
        else:
            return self.load_from_local_file()
    
    def load_from_google_sheets(self):
        """Load game database from Google Sheets.

        Supports multiple worksheets: each worksheet is treated as a console tab.
        The worksheet title will be used as the 'Console' value.
        """
        try:
            if not self.google_sheet_url:
                raise ValueError("Google Sheets URL not provided")
            
            # Set up Google Sheets authentication
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            # Try service account authentication first
            if self.credentials_path and os.path.exists(self.credentials_path):
                try:
                    if Credentials is None or gspread is None:
                        raise RuntimeError("Google libraries not installed. Install requirements.")
                    creds = Credentials.from_service_account_file(
                        self.credentials_path, scopes=scopes
                    )
                    self.gc = gspread.authorize(creds)
                    print(f"Authenticated with service account from {self.credentials_path}")
                except Exception as e:
                    print(f"Service account auth failed: {e}")
                    raise
            else:
                # Try to use gspread's built-in service account discovery
                try:
                    if gspread is None:
                        raise RuntimeError("gspread not installed. Install requirements.")
                    self.gc = gspread.service_account(filename=self.credentials_path)
                    print("Authenticated with default service account")
                except Exception as e:
                    print(f"Error: Could not authenticate. {e}")
                    raise ValueError(
                        "Google Sheets authentication failed. "
                        "Please provide valid credentials file path."
                    )
            
            # Open the spreadsheet
            # Try to open by URL first, then by key
            try:
                if 'docs.google.com' in self.google_sheet_url:
                    sheet = self.gc.open_by_url(self.google_sheet_url)
                else:
                    # Assume it's a sheet ID/key
                    sheet = self.gc.open_by_key(self.google_sheet_url)
            except Exception as e:
                print(f"Error opening sheet: {e}")
                raise ValueError(
                    f"Could not open Google Sheet. Make sure:\n"
                    f"1. The sheet is shared with your service account email\n"
                    f"2. The URL or ID is correct\n"
                    f"Error: {e}"
                )
            
            # Read all worksheets and build console mapping
            self.games_by_console = {}
            frames = []
            for ws in sheet.worksheets():
                ws_title = (ws.title or "").strip()
                data = ws.get_all_values()
                if not data or len(data) < 2:
                    # Skip empty worksheets
                    continue
                headers = data[0]
                rows = data[1:]
                df = pd.DataFrame(rows, columns=headers)
                norm = self._normalize_sheet_df(df, ws_title)

                console_key = norm['Console'].iloc[0]
                self.games_by_console[console_key] = norm.copy()
                frames.append(norm)

            if not frames:
                raise ValueError("Google Sheet has no valid data in any worksheet")

            # Concatenate all into one DataFrame
            self.games_data = pd.concat(frames, ignore_index=True)
            print(f"Loaded {len(self.games_data)} games from Google Sheets across {len(self.games_by_console)} consoles")
            return True
            
        except Exception as e:
            print(f"Error loading from Google Sheets: {e}")
            # Create empty dataframe with expected columns
            self.games_data = pd.DataFrame(columns=[
                'Game Title', 'Details', 'State', 'Large Image', 
                'Large Image Text', 'Small Image', 'Small Image Text'
            ])
            return False
    
    def load_from_local_file(self):
        """Load game database from local Excel or CSV file.

        - If Excel with multiple sheets: each sheet is a console tab.
        - If single sheet or CSV: treated as a single console named 'All'.
        """
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database file not found: {self.db_path}")
            
            # Try to read as Excel with multiple sheets
            if self.db_path.endswith('.xlsx') or self.db_path.endswith('.xls'):
                try:
                    xl = pd.read_excel(self.db_path, sheet_name=None)
                    if isinstance(xl, dict):
                        self.games_by_console = {}
                        frames = []
                        for sheet_name, df in xl.items():
                            if df is None or df.empty:
                                continue
                            norm = self._normalize_sheet_df(df, str(sheet_name).strip())
                            self.games_by_console[norm['Console'].iloc[0]] = norm.copy()
                            frames.append(norm)

                        if frames:
                            self.games_data = pd.concat(frames, ignore_index=True)
                        else:
                            # Fallback to single sheet read
                            self.games_data = pd.read_excel(self.db_path)
                            self.games_data['Console'] = 'All'
                    else:
                        # Single sheet
                        self.games_data = xl
                        self.games_data['Console'] = 'All'
                except Exception:
                    # Fallback to single sheet
                    self.games_data = pd.read_excel(self.db_path)
                    self.games_data['Console'] = 'All'
            elif self.db_path.endswith('.csv'):
                self.games_data = pd.read_csv(self.db_path)
                self.games_data['Console'] = 'All'
            else:
                # Try Excel first, then CSV
                try:
                    self.games_data = pd.read_excel(self.db_path)
                    self.games_data['Console'] = 'All'
                except Exception:
                    self.games_data = pd.read_csv(self.db_path)
                    self.games_data['Console'] = 'All'
            
            # Normalize columns
            self.games_data.columns = [str(c).strip() for c in self.games_data.columns]
            expected_cols = [
                'Game Title', 'Details', 'State', 'Large Image',
                'Large Image Text', 'Small Image', 'Small Image Text',
                'Console'
            ]
            for col in expected_cols:
                if col not in self.games_data.columns:
                    self.games_data[col] = ""

            self.games_data = self.games_data[expected_cols].fillna("")
            if not self.games_by_console:
                # Build mapping from combined data
                self.games_by_console = {
                    c: df.copy() for c, df in self.games_data.groupby('Console')
                }

            print(f"Loaded {len(self.games_data)} games from local database across {len(self.games_by_console)} consoles")
            return True
        except Exception as e:
            print(f"Error loading local database: {e}")
            # Create empty dataframe with expected columns
            self.games_data = pd.DataFrame(columns=[
                'Game Title', 'Details', 'State', 'Large Image', 
                'Large Image Text', 'Small Image', 'Small Image Text', 'Console'
            ])
            self.games_by_console = {}
            return False
    
    def get_all_game_titles(self):
        """Deprecated. Use get_games_by_console or get_all_game_titles_by_console.

        Kept for backward compatibility; returns all titles across all consoles.
        """
        if self.games_data is None or self.games_data.empty:
            return []
        return self.games_data['Game Title'].tolist()

    def get_consoles(self):
        """Return a sorted list of available console names (worksheet names)."""
        if self.games_by_console:
            return sorted(list(self.games_by_console.keys()))
        if self.games_data is not None and not self.games_data.empty and 'Console' in self.games_data.columns:
            return sorted(self.games_data['Console'].dropna().unique().tolist())
        return []

    def get_all_game_titles_by_console(self, console):
        """Return all game titles for a specific console."""
        if not console:
            return self.get_all_game_titles()
        if self.games_by_console and console in self.games_by_console:
            df = self.games_by_console[console]
            if df is not None and not df.empty:
                return df['Game Title'].dropna().tolist()
            return []
        if self.games_data is None or self.games_data.empty:
            return []
        df = self.games_data[self.games_data['Console'] == console]
        return df['Game Title'].dropna().tolist()
    
    def get_game_data(self, game_title, console: str | None = None):
        """
        Get all data for a specific game.
        
        Args:
            game_title: The title of the game to look up
            console: Optional console to filter by
            
        Returns:
            Dictionary containing game data, or None if not found
        """
        if self.games_data is None or self.games_data.empty:
            return None

        if console:
            df = self.games_by_console.get(console)
            if df is None or df.empty:
                return None
            game_row = df[df['Game Title'] == game_title]
        else:
            game_row = self.games_data[self.games_data['Game Title'] == game_title]

        if game_row.empty:
            return None
        
        # Convert to dictionary, handling NaN values
        game_dict = game_row.iloc[0].to_dict()
        
        # Replace NaN with empty strings
        for key, value in game_dict.items():
            if pd.isna(value):
                game_dict[key] = ""
        
        return game_dict
    
    def reload_database(self):
        """Reload the database from file."""
        return self.load_database()
    
    def add_game(self, game_data):
        """
        Add a new game to the database (in memory only).
        
        Args:
            game_data: Dictionary containing game information
        """
        if self.games_data is None:
            self.games_data = pd.DataFrame([game_data])
        else:
            self.games_data = pd.concat([self.games_data, pd.DataFrame([game_data])], 
                                       ignore_index=True)
    
    def save_database(self):
        """Save the current database to file (local files only)."""
        if self.use_google_sheets:
            print("Cannot save directly to Google Sheets from this method")
            return False
        
        try:
            if self.db_path.endswith('.xlsx') or self.db_path.endswith('.xls'):
                self.games_data.to_excel(self.db_path, index=False)
            else:
                self.games_data.to_csv(self.db_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
    
    def switch_to_google_sheets(self, google_sheet_url, credentials_path=None):
        """
        Switch from local file to Google Sheets.
        
        Args:
            google_sheet_url: URL or ID of the Google Sheet
            credentials_path: Path to credentials JSON file
            
        Returns:
            True if successful, False otherwise
        """
        self.use_google_sheets = True
        self.google_sheet_url = google_sheet_url
        self.credentials_path = credentials_path
        return self.load_database()
    
    def switch_to_local_file(self, db_path=None):
        """
        Switch from Google Sheets to local file.
        
        Args:
            db_path: Path to local database file (optional)
            
        Returns:
            True if successful, False otherwise
        """
        self.use_google_sheets = False
        if db_path:
            self.db_path = db_path
        return self.load_database()

    # Backwards-compat convenience alias
    def get_games_by_console(self, console):
        return self.get_all_game_titles_by_console(console)


if __name__ == "__main__":
    # Test the database module
    db = GameDatabase()
    print("Available games:")
    for title in db.get_all_game_titles():
        print(f"  - {title}")
    
    # Test retrieving a specific game
    game = db.get_game_data("Pokemon Red")
    if game:
        print("\nPokemon Red data:")
        for key, value in game.items():
            print(f"  {key}: {value}")
