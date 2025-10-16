# Google Sheets Template for Discord Rich Presence

Create a Google Sheet with these columns in the first row:

## Column Headers (Row 1)
```
Game Title | Details | State | Large Image | Large Image Text | Small Image | Small Image Text
```

## Example Data (Row 2+)
```
Pokemon Red | Playing Pokemon Red | Exploring Kanto | pokemon_red | Pokemon Red | pokeball | Catching Pokemon
Pokemon Blue | Playing Pokemon Blue | Exploring Kanto | pokemon_blue | Pokemon Blue | pokeball | Catching Pokemon
Pokemon Gold | Playing Pokemon Gold | Exploring Johto | pokemon_gold | Pokemon Gold | pokeball | Catching Pokemon
Zelda: BOTW | The Legend of Zelda | Exploring Hyrule | zelda_botw | Breath of the Wild | master_sword | Adventuring
Mario Odyssey | Super Mario Odyssey | Collecting Moons | mario_odyssey | Mario Odyssey | mario_cap | Playing
```

## Instructions

1. Copy this structure to your Google Sheet
2. Customize with your own games
3. Share with your service account email
4. Use the sheet URL in the application

## Important Notes

- Keep column headers exactly as shown
- You can create multiple tabs, one per console (e.g., PS3, PS4, PS5). The app will read all tabs and use the tab name as the Console.
- Image fields (Large Image, Small Image) must be Discord Rich Presence asset keys (names) from your app's Developer Portal, not web URLs.
- The "* Text" fields are hover text shown when users hover the images.
- You can leave image fields empty if not using images
- Make sure the sheet is shared with your service account
