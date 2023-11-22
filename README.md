# Palantir

Palantir is an unofficial, highly customizable cog for [Red](https://github.com/Cog-Creators/Red-DiscordBot) that's primary task is to monitor Zandronum/Q-Zandronum servers for player activity.  
The cog uses Klaufir's [pyzandro](https://github.com/klaufir216/pyzandro) library to communicate with the master server and the individual game servers.  

Palantir currently only supports monitoring QC:Doom Edition servers, this will change in the future and it will be customizeable for each individual Discord guild the cog is used in.  

# Installing

The cog is currently under development and thus not applied for approvement as an official cog. For this reason it can't be installed from Discord.  
Place the `palantir` folder in your cog folder (default: `~/.local/share/Red-DiscordBot/data/Red/cogs/CogManager/cogs`) and load it by issuing the `[p]load palantir` command to your RedBot.

## Create cron job for updating GeoIP database

Palantir looks for a `GeoLite2-Country.mmdb` file at the following locations:

- `$GEOIP_PATH`
- `~/.geoip`
- `/usr/share/GeoIP`
- `/var/lib/GeoIP`

The cronjob below will create an entry that updates the geoip db at `~/.geoip`.

First edit crontab with the user running Red.

```
crontab -e
```

Add the following:

```
# update GeoLite2-Country.mmdb on every Monday 03:33
33 3 * * 1 bash -c 'mkdir -p ~/.geoip/ && curl -L https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb > ~/.geoip/GeoLite2-Country.mmdb'
```


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

- Special thanks to [Klaufir](https://github.com/klaufir216) for helping me on my journey to learn Python and providing assistance with the project and coming up with the name for the cog
- Thanks to [Pixo](https://github.com/GavinPixoLee) for a PoC
- Thanks to [Vexed](https://github.com/Vexed01) for an [example](https://github.com/Vexed01/Vex-Cogs/tree/master/fivemstatus) I could learn a lot from
