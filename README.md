# Discord Rich Presence - Game Selector

A Python application with a graphical user interface (GUI) that allows you to display custom Discord Rich Presence status for video games. The app reads game information from an Excel/CSV database and displays it on your Discord profile.

## Features

- 🎮 **Game Database**: Store multiple games in an Excel worksheet with custom details
- 🖥️ **User-Friendly GUI**: Easy-to-use interface built with tkinter
- 🔄 **Real-Time Updates**: Change your Discord status instantly
- ⏱️ **Elapsed Time**: Optional elapsed time display
- 📝 **Customizable**: Edit all presence fields directly in the UI
- 💾 **Persistent Config**: Save your Discord Client ID in a config file

## Screenshots

The app displays information like:
- "Now Playing Pokemon Red"
- Game state (e.g., "Exploring Kanto")
- Custom images for each game
- Elapsed time since you started playing

## Prerequisites

- Python 3.7 or higher
- Discord Desktop App (must be running)
- Discord Developer Application (for Client ID)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/The1Azreen/JustAnotherDiscordRichPresenceApp.git
   cd JustAnotherDiscordRichPresenceApp
   ```

2. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Discord Application**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Copy the **Application ID** (this is your Client ID)
   - (Optional) Upload custom images under "Rich Presence > Art Assets"

4. **Configure the app**:
   - Open `config.ini` (it will be created from `config.ini.example`)
   - Replace `YOUR_CLIENT_ID_HERE` with your Discord Application ID:
     ```ini
     [Discord]
     CLIENT_ID = 123456789012345678
     ```

## Usage

1. **Run the application**:
   ```bash
   python main.py
   ```

2. **Connect to Discord**:
   - Make sure Discord is running
   - Click the "Connect" button
   - If configured correctly, you'll see "Status: Connected" in green

3. **Select a game**:
   - Choose a game from the dropdown menu
   - The fields will auto-populate with game data from the database

4. **Customize (optional)**:
   - Edit any field to customize your presence
   - Modify details, state, images, etc.

5. **Update your presence**:
   - Click "Update Presence" to apply changes
   - Your Discord profile will now show the custom status!

6. **Clear presence**:
   - Click "Clear Presence" to remove the Rich Presence

## Game Database

The game database is stored in `games_database.xlsx` (or `.csv`). The file has the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| **Game Title** | Name of the game (shown in dropdown) | Pokemon Red |
| **Details** | First line of Rich Presence | Playing Pokemon Red |
| **State** | Second line of Rich Presence | Exploring Kanto |
| **Large Image** | Asset key for large image | pokemon_red |
| **Large Image Text** | Hover text for large image | Pokemon Red |
| **Small Image** | Asset key for small image | pokeball |
| **Small Image Text** | Hover text for small image | Catching Pokemon |

### Adding New Games

1. Open `games_database.xlsx` in Excel or any spreadsheet editor
2. Add a new row with your game information
3. Save the file
4. Click "Reload Database" in the app

### Using Custom Images

To use custom images in your Rich Presence:

1. Go to your Discord Application in the [Developer Portal](https://discord.com/developers/applications)
2. Navigate to "Rich Presence" > "Art Assets"
3. Upload your images and give them names (these are your asset keys)
4. Use the asset key names in the "Large Image" and "Small Image" columns

**Note**: You can also use external image URLs if your Discord application supports them.

## File Structure

```
JustAnotherDiscordRichPresenceApp/
├── main.py                 # Main GUI application
├── discord_rpc.py          # Discord Rich Presence handler
├── database.py             # Game database reader
├── games_database.xlsx     # Game information database
├── config.ini              # Configuration file (create from .example)
├── config.ini.example      # Configuration template
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Configuration Options

Edit `config.ini` to customize behavior:

```ini
[Discord]
# Your Discord Application ID
CLIENT_ID = YOUR_CLIENT_ID_HERE

[Settings]
# Automatically connect to Discord on startup
AUTO_CONNECT = True

# Update interval in seconds (future feature)
UPDATE_INTERVAL = 15
```

## Troubleshooting

### "Failed to connect to Discord"
- Make sure Discord Desktop is running
- Verify your Client ID is correct
- Try restarting Discord

### "Import 'pypresence' could not be resolved"
- Run `pip install -r requirements.txt`
- Make sure you're using the correct Python environment

### "Database file not found"
- Make sure `games_database.xlsx` exists in the same folder as `main.py`
- Try creating a new Excel file with the correct column headers

### Images not showing
- Upload images to Discord Developer Portal under "Art Assets"
- Use the exact asset key name in the database
- Wait a few minutes for Discord to update the assets

## Development

### Running Tests

Test individual modules:

```bash
# Test database module
python database.py

# Test Discord RPC module (requires valid Client ID)
python discord_rpc.py
```

### Adding Features

Feel free to fork and modify! Some ideas:
- Add support for buttons in Rich Presence
- Auto-detect running games
- Multiple profile presets
- Database editor within the GUI

## Dependencies

- `pypresence` - Discord Rich Presence library
- `openpyxl` - Excel file support
- `pandas` - Data manipulation
- `tkinter` - GUI framework (included with Python)

## License

This project is open source. Feel free to use and modify as needed.

## Credits

Created by The1Azreen

Built with:
- [pypresence](https://github.com/qwertyquerty/pypresence) by qwertyquerty
- Python's tkinter for the GUI
- pandas and openpyxl for data handling

## Support

If you encounter issues:
1. Check the Activity Log in the app for error messages
2. Verify all configuration steps
3. Make sure Discord is running
4. Check that your Client ID is correct

For more help, please open an issue on GitHub.

## Example

Here's what your Discord profile might show:

```
🎮 Playing Pokemon Red
   Exploring Kanto
   [Pokemon Red Icon]
   Started: 15 minutes ago
```

Enjoy customizing your Discord Rich Presence! 🚀
