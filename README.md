# Hypixel Duels Discord Bot

A bot originally made for the [Hypixel Classic Duels Discord](https://discord.gg/u7fuYWMUWf) to let members verify their [Discord](https://discord.com/) account to [Hypixel](https://hypixel.net/) and automatically manage duels roles. Uses [discord.pu](https://github.com/Rapptz/discord.py).

## Features

- `Verified` role: Assigned to members after using the `/verify` command.
- Duels specific roles: Constantly updating duels game mode roles auto assigned to members after verification.
- Hypixel nicknames: Changes Discord nicknames to show IGN and Hypixel guild tag. Updates automatically.

<img src="https://raw.githubusercontent.com/BridgeSenseDev/Hypixel-Duels-Discord-Bot/main/.github/assets/img/preview.png" alt="Preview">

## Setup

1. Clone the repository.
```
git clone https://github.com/BridgeSenseDev/Hypixel-Duels-Discord-Bot.git
cd Hypixel-Duels-Discord-Bot
```
2. Set up your python environment and install packages. This project uses [uv](https://docs.astral.sh/uv/), or you can install from packages from `requirements.txt` with `pip install -r requirements.txt`
3. Rename `config.example.json` to `config.json` and `members.example.db` to `members.db`
4. Edit `config.json` with your own configuration:

```json5
{
  // Your discord bot token
  "discord_token": "",
  // Your hypixel API key
  "hypixel_api_key": "",
  // Your discord server ID
  "guild_id": 0,
  // The name of the key in the hypixel API response for the wins of your specific gamemode wins (e.g. classic_duel_wins for Classic Duels)
  "hypixel_api_wins_key": "",
  // Gif that will be shown when someone has the wrong discord set on Hypixel
  "error_gif": "https://cdn.discordapp.com/attachments/1036738622361190520/1219728234804150422/tutorial.gif",
  // Discord role IDs for different roleshttps://github.com/Rapptz/discord.py
  "role_ids": {
    "verified": 0,
    "ASCENDED": 0,
    "DIVINE": 0,
    "CELESTIAL": 0,
    "Godlike": 0,
    "Grandmaster": 0,
    "Legend": 0,
    "Master": 0,
    "Diamond": 0,
    "Gold": 0,
    "Iron": 0,
    "Rookie": 0
  },
  // Embed colors
  "colors": {
    "red": 14171198,
    "discordGray": 3092790,
    "green": 2981190
  },
  // Emojis used in embed responses
  "emojis": {
    "tick": ":white_check_mark:",
    "cross": ":x:",
    "add": ":heavy_plus_sign:",
    "minus": ":heavy_minus_sign:"
  },
  // Wins for each duel role
  "roles_wins": [
    [100000, "ASCENDED"],
    [50000, "DIVINE"],
    [25000, "CELESTIAL"],
    [10000, "Godlike"],
    [5000, "Grandmaster"],
    [2000, "Legend"],
    [1000, "Master"],
    [500, "Diamond"],
    [250, "Gold"],
    [100, "Iron"],
    [50, "Rookie"]
  ]
}
```

5. Run the bot with `python main.py`