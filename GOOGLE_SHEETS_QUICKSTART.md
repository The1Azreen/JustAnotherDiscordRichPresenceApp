# Quick Start Guide: Google Sheets Integration

## What's New?
Your Discord Rich Presence app now supports loading game data from Google Sheets!

## Quick Setup (5 minutes)

### 1. Install New Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- `gspread` - Google Sheets API
- `google-auth` - Authentication libraries

### 2. Get Google Credentials

**Quick Steps:**
1. Go to https://console.cloud.google.com/
2. Create a project
3. Enable "Google Sheets API" and "Google Drive API"
4. Create Service Account credentials
5. Download JSON key as `credentials.json`
6. Place in app folder

**Detailed instructions:** See README.md "Google Sheets Setup" section

### 3. Share Your Google Sheet

1. Create or open a Google Sheet with your games
2. Format: `Game Title | Details | State | Large Image | Large Image Text | Small Image | Small Image Text`
3. Click "Share"
4. Add the email from your `credentials.json` (client_email field)
5. Give Viewer or Editor access

### 4. Run the App

```bash
python main.py
```

1. Select "Google Sheets" radio button
2. Paste your sheet URL
3. Click "Load"
4. Your games will appear in the dropdown!

## Features

✅ **Switch between sources**: Toggle between local file and Google Sheets
✅ **Auto-sync**: Click "Reload" to get latest data from Google Sheets
✅ **Help dialog**: Built-in setup instructions (shown if credentials missing)
✅ **Error handling**: Clear error messages for common issues

## Configuration

Edit `config.ini`:

```ini
[GoogleSheets]
USE_GOOGLE_SHEETS = True
SHEET_URL = https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
CREDENTIALS_PATH = credentials.json
```

## Troubleshooting

**Can't connect to Google Sheets?**
- Check that credentials.json exists
- Verify sheet is shared with service account email
- Make sure APIs are enabled in Google Cloud Console

**See full troubleshooting guide in README.md**

## Benefits of Google Sheets

- 📱 Update your game list from any device
- 🔄 No need to manually sync files
- 👥 Share with friends/team
- ☁️ Cloud backup
- 📊 Use Google Sheets formulas and features

Enjoy your cloud-powered Discord Rich Presence! 🚀
