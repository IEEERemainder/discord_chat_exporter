# discord_chat_exporter

## Features
- Download discord channels in DMs or guilds, with no bot setup needed (for example if server admins doesn't allow to (but you take into account why and try to don't violate a lot, for example, for backup needs (I was an admin at server whose 50% of channels had been deleted irrevocably by the fired admin)))
- CLI support (discord_chat_exporter.py)
- Quite sloppy tkinter GUI with almost no decorations
- Select channels to export in ListBox widget, filter by DM, DM (only people), DM (only groups), Guilds or concrete guilds (select guild and press 'sel guilds channels')
- Export to sqlite, json or our .data.js format (simple 'DATA = ' jsStringsArrayDecl + ';')
- Not quite fast, use other programs if it's crucial

## Requirements:
Python 3+, `[discord_api](https://github.com/IEEERemainder/discord_api)`

## Run guide
Download [discord_api](https://github.com/IEEERemainder/discord_api), put `discord_api.py` in one folder with `gui.py` or/and `discord_chat_exporter.py`, run `gui.py` for GUI (graphical interface) or use command-line based `discord_chat_exporter.py [tocen] [sqlite|json|datajs] [fileName] [channelId1,channelId2,...channelIdN]`
You can obtain your user account's tocen by loggin in discord via browser, opening DevTools (`Ctrl` + `Shift` + `I` for most popular browsers), going to networc tab, opening channel you haven't opened in this session (and if they has not accumulated enought messages to load it from cache) (you may reload page if unsure if understand it or want to), searching a request named lice 'messages?limit=50', opening it's details, copying value of 'Authorization' field in 'Request Headers'. Granting it to either user or program may result in account lose, so beware it. This program doesn't perform any malicious actions, however, you should be able to chec the code in notepad if needed.
Certain activities via API directly, unattainable from official Discord client, may result in account deactivation, don't try to download terabytes of data or distribute/process it in ways that may be unexpected for their affiliates 

## TODOS
- Mace better interface? (but it suits me)
- Simple analysis of frequent words, concordances, count by user, dialogues detection (if server log) 
- Word wrap by visible length, not character count (monospace font is unavailable, `select` is OS-dependant component)
- Probably replace `select` with CSS friendly component
- Extend browsers support?
- Adaptive page layout? (PC only for now)

## Have ideas or need help? 
Create issue or concat me via nosare@yandex.ru or Interlocked#6505