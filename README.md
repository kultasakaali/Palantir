# Palantir

Palantir is an unofficial, highly customizable custom cog for [Red](https://github.com/Cog-Creators/Red-DiscordBot) that's primary task is to monitor Zandronum/Q-Zandronum servers for player activity.  
The cog uses Klaufir's [pyzandro](https://github.com/klaufir216/pyzandro) library to communicate with the master server and the individual game servers.  

Palantir currently only supports monitoring QC:Doom Edition servers, this will change in the future and it will be customizeable for each individual Discord guild the cog is used in.  

# Installing

The cog is currently under development and thus not applied for approvement as an official cog. For this reason it can't be installed from Discord.  
Place the `palantir` folder in your cog folder (default: `~/.local/share/Red-DiscordBot/data/Red/cogs/CogManager/cogs`) and load it by issuing the `[p]load palantir` command to your RedBot.

# Usage

Use the `[p]palantir setup` command to create an embed in the channel of your choice which will display a list of active servers.  
Consult the built-in help for further info on commands.

## List of available commands:

|Command       |Arguments              |Description                                              |
|--------------|-----------------------|---------------------------------------------------------|
|setup         |[channel_id] [role_id] |Set up a self-updating embed.                            |
|delete        |<guild_id>             |Delete a guild's self-updating embed.                    |
|stop          |                       |Stops the cog's scheduled task.                          |
|start         |                       |Starts the cog's scheduled task.                         |
|notifyrole    |[role_id]              |Get or set the role to be notified of server activities. |
|configchannel |[channel_id]           |Get or set the channel to recieve error messages.        |
|setinterval   |[hrs] [mins] [secs]    |Get or set server querying interval.                     |
|reload_json   |                       |Reload the external JSON file.                           |
|getlog        |[mode]                 |Download server usage/diagnostic logs                    |

# Credits

- Special thanks to [Klaufir](https://github.com/klaufir216) for helping me on my journey to learn Python and providing assistance with the project
- Thanks to [Pixo](https://github.com/GavinPixoLee) for a PoC
- Thanks to [Vexed](https://github.com/Vexed01) for an [example](https://github.com/Vexed01/Vex-Cogs/tree/master/fivemstatus) I could learn a lot from
