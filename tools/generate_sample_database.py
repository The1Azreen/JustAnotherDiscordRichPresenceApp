"""
Generate a multi-sheet Excel database for testing, with curated seeds.

Outputs:
- ../games_database.xlsx with sheets: PS3, PS4, PS5 (wide format)
- ../data/ps3.csv, ../data/ps4.csv, ../data/ps5.csv (wide format)
- ../data/ps3_long.csv, ../data/ps4_long.csv, ../data/ps5_long.csv (long format: one row per field)
"""
from __future__ import annotations
import os
import random
import string
import pandas as pd


HEADERS = [
    'Game Title', 'Details', 'State', 'Large Image',
    'Large Image Text', 'Small Image', 'Small Image Text'
]


def random_word(n=6):
    return ''.join(random.choices(string.ascii_letters, k=n))


def seed_titles() -> dict[str, list[str]]:
    # Curated seeds (partial) + will be topped up to 100
    ps3 = [
        "The Last of Us", "Uncharted 2: Among Thieves", "Uncharted 3: Drake's Deception",
        "Metal Gear Solid 4: Guns of the Patriots", "Demon's Souls", "Heavy Rain",
        "Journey", "God of War III", "Gran Turismo 5", "LittleBigPlanet",
        "LittleBigPlanet 2", "Red Dead Redemption", "Grand Theft Auto V",
        "Bioshock Infinite", "Batman: Arkham City", "Ni no Kuni: Wrath of the White Witch",
        "Valkyria Chronicles", "Infamous", "Infamous 2", "Killzone 2",
        "Killzone 3", "Resistance: Fall of Man", "Resistance 2", "Yakuza 4",
        "Yakuza 5", "Dragon's Dogma", "Dark Souls", "Dead Space", "Dead Space 2",
        "Call of Duty: Modern Warfare 2", "Call of Duty: Black Ops",
        "Call of Duty: Black Ops II", "Skyrim", "Fallout 3", "Fallout: New Vegas",
        "Mass Effect 2", "Mass Effect 3", "Portal 2", "Borderlands 2",
        "Far Cry 3", "Assassin's Creed II", "Assassin's Creed Brotherhood",
        "Assassin's Creed IV: Black Flag", "Mirror's Edge", "Catherine",
        "Persona 5 (PS3)", "Persona 4 Arena", "Ultra Street Fighter IV"
    ]
    ps4 = [
        "God of War (2018)", "Horizon Zero Dawn", "Bloodborne", "Marvel's Spider-Man",
        "Ghost of Tsushima", "Uncharted 4: A Thief's End", "The Last of Us Part II",
        "Persona 5 Royal", "Final Fantasy VII Remake", "Death Stranding",
        "Sekiro: Shadows Die Twice", "Nier: Automata", "Resident Evil 2 (Remake)",
        "Resident Evil 7: Biohazard", "Monster Hunter: World", "Gran Turismo Sport",
        "Ratchet & Clank", "Days Gone", "The Witcher 3: Wild Hunt",
        "Assassin's Creed Odyssey", "Assassin's Creed Origins", "Red Dead Redemption 2",
        "Cyberpunk 2077 (PS4)", "Street Fighter V", "Tekken 7", "Mortal Kombat 11",
        "Dark Souls III", "Destiny 2", "Overwatch", "Apex Legends",
        "Fortnite", "Control", "Watch Dogs 2", "Yakuza 0", "Yakuza Kiwami",
        "Yakuza Like a Dragon (PS4)", "Tales of Arise (PS4)", "Dragon Quest XI",
        "Kingdom Hearts III", "Shadow of the Colossus (2018)", "Inside",
        "Remnant: From the Ashes", "Return of the Obra Dinn", "Hades",
        "DOOM (2016)", "DOOM Eternal", "Metal Gear Solid V: The Phantom Pain"
    ]
    ps5 = [
        "Marvel's Spider-Man 2", "Demon's Souls (PS5)", "Ratchet & Clank: Rift Apart",
        "Final Fantasy XVI", "Final Fantasy VII Rebirth", "Horizon Forbidden West",
        "God of War Ragnarök", "Returnal", "Gran Turismo 7", "Astro's Playroom",
        "Resident Evil 4 (Remake)", "Resident Evil Village", "Baldur's Gate 3",
        "Elden Ring (PS5)", "Cyberpunk 2077 (PS5)", "Ghost of Tsushima Director's Cut",
        "Death Stranding Director's Cut", "The Last of Us Part I", "Alan Wake 2",
        "Assassin's Creed Mirage", "Mortal Kombat 1", "Street Fighter 6",
        "Tekken 8", "Like a Dragon: Infinite Wealth", "Yakuza: Like a Dragon (PS5)",
        "Diablo IV", "Call of Duty: Modern Warfare III (2023)", "Nioh Collection",
        "Forspoken", "Tales of Arise (PS5)", "Scarlet Nexus (PS5)", "Kena: Bridge of Spirits",
        "It Takes Two (PS5)", "Control Ultimate Edition", "The Witcher 3 (Next-Gen)",
        "No Man's Sky (PS5)", "The Callisto Protocol", "Lies of P", "Remnant II",
        "Alan Wake Remastered", "Ghostrunner 2", "Return to Monkey Island",
        "Sifu (PS5)", "Stray", "The Pathless"
    ]
    return {"PS3": ps3, "PS4": ps4, "PS5": ps5}


def top_up_to_100(titles: list[str], console: str) -> list[str]:
    titles = list(dict.fromkeys(titles))  # de-dupe preserving order
    i = 1
    while len(titles) < 100:
        candidate = f"{console} Game {i}"
        if candidate not in titles:
            titles.append(candidate)
        i += 1
    return titles[:100]


def make_wide_rows(console: str, titles: list[str]) -> pd.DataFrame:
    rows = []
    for idx, title in enumerate(titles, start=1):
        details = f"Playing {title}"
        state = random.choice([
            "Main Menu", "Exploring", "In Battle", "Cutscene", "Paused", "Multiplayer"
        ])
        large_image = f"{console.lower()}_cover_{idx%10}"
        large_text = f"{title} Cover"
        small_image = random.choice(["controller", "logo", "icon", "badge"])  # placeholder asset keys
        small_text = random.choice(["Ready", "Online", "AFK", "Grinding"])
        rows.append([title, details, state, large_image, large_text, small_image, small_text])
    return pd.DataFrame(rows, columns=HEADERS)


def make_long_rows(console: str, wide_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in wide_df.iterrows():
        title = row['Game Title']
        for field in HEADERS[1:]:  # skip Game Title
            records.append([title, field, row[field]])
    return pd.DataFrame(records, columns=['Game Title', 'Field', 'Value'])


def main():
    consoles = ["PS3", "PS4", "PS5"]
    seeds = seed_titles()
    wide_data = {}
    long_data = {}

    # Ensure output dir for CSV
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    for c in consoles:
        titles = top_up_to_100(seeds.get(c, []), c)
        wide_df = make_wide_rows(c, titles)
        long_df = make_long_rows(c, wide_df)
        wide_data[c] = wide_df
        long_data[c] = long_df
        # Write CSVs
        wide_df.to_csv(os.path.join(data_dir, f"{c.lower()}.csv"), index=False)
        long_df.to_csv(os.path.join(data_dir, f"{c.lower()}_long.csv"), index=False)

    # Write Excel workbook (wide format per sheet)
    out_path = os.path.join(base_dir, "games_database.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for c in consoles:
            wide_data[c].to_excel(writer, sheet_name=c, index=False)
    print(f"Wrote sample database to: {out_path}")
    print(f"CSV outputs in: {data_dir}")


if __name__ == "__main__":
    main()
