"""
Database module for reading game information from Excel/CSV files and Google Sheets.
"""
import pandas as pd
import os
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError


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
        self.games_data = None
        self.gc = None  # Google Sheets client
        self.load_database()
    
    def load_database(self):
        """Load the game database from local file or Google Sheets."""
        if self.use_google_sheets:
            return self.load_from_google_sheets()
        else:
            return self.load_from_local_file()
    
    def load_from_google_sheets(self):
        """Load game database from Google Sheets."""
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
            
            # Get the first worksheet
            worksheet = sheet.get_worksheet(0)
            
            # Get all values and convert to DataFrame
            data = worksheet.get_all_values()
            
            if not data or len(data) < 2:
                raise ValueError("Google Sheet is empty or has no data rows")
            
            # First row is headers
            headers = data[0]
            rows = data[1:]
            
            self.games_data = pd.DataFrame(rows, columns=headers)
            
            print(f"Loaded {len(self.games_data)} games from Google Sheets")
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
        """Load game database from local Excel or CSV file."""
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database file not found: {self.db_path}")
            
            # Try to read as Excel first, then CSV
            if self.db_path.endswith('.xlsx') or self.db_path.endswith('.xls'):
                self.games_data = pd.read_excel(self.db_path)
            elif self.db_path.endswith('.csv'):
                self.games_data = pd.read_csv(self.db_path)
            else:
                # Try Excel first, then CSV
                try:
                    self.games_data = pd.read_excel(self.db_path)
                except:
                    self.games_data = pd.read_csv(self.db_path)
            
            print(f"Loaded {len(self.games_data)} games from local database")
            return True
        except Exception as e:
            print(f"Error loading local database: {e}")
            # Create empty dataframe with expected columns
            self.games_data = pd.DataFrame(columns=[
                'Game Title', 'Details', 'State', 'Large Image', 
                'Large Image Text', 'Small Image', 'Small Image Text'
            ])
            return False
    
    def get_all_game_titles(self):
        """
        Get a list of all game titles in the database.
        
        Returns:
            List of game titles
        """
        if self.games_data is None or self.games_data.empty:
            return []
        return self.games_data['Game Title'].tolist()
    
    def get_game_data(self, game_title):
        """
        Get all data for a specific game.
        
        Args:
            game_title: The title of the game to look up
            
        Returns:
            Dictionary containing game data, or None if not found
        """
        if self.games_data is None or self.games_data.empty:
            return None
        
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
