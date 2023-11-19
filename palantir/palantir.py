import asyncio
import os
import pprint
import random
import shutil
import sys
import traceback

from datetime import datetime, timezone

import logging
from logging.handlers import TimedRotatingFileHandler

import discord
from discord.ext import tasks
from redbot.core import Config, bot, commands
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

import pyzandro
from pyzandro import PyZandroException
from pyzandro.server import SQF

from .geoiphelper import query_geoip

#TODO: implement notification policies
#TODO: cleanup

COG_PATH = os.path.dirname(__file__)
LOGFILE = os.path.join(COG_PATH, "logs/palantir_verbose.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False

log_formatter = logging.Formatter(fmt = "%(asctime)s %(name)s: [%(levelname)s] %(message)s", datefmt = "%Y-%m-%d %H:%M:%S")

file_handler = TimedRotatingFileHandler(filename = LOGFILE, when = "d", interval = 30, backupCount = 5)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(log_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

def load_external_config():
    import json
    with open(os.path.join(COG_PATH, "config.json"), "r") as f:
        return json.loads(f.read())



class Palantir(commands.Cog):

    def __init__(self, bot: bot.Red):

        self.bot = bot

        guild_defaults = {
            "channel_id": 0,
            "embed_id": 0,
            "role_to_notify": 0,
            "bot_config_channel": 0,
        }

        # pyzandro.set_log_target(r'/home/kulta/Sync/palantir/pyzandro_packets.log')

        self.config:Config = Config.get_conf(self, identifier = 3583395656)
        self.config.register_guild(**guild_defaults)

        self.config_external = load_external_config()

        self.active_servers = []
        self.serverlist_cache = []
        self.fail_counter = 0

        self.sched_task.start()



    def cog_unload(self):
        self.sched_task.cancel()
        
        logger.info("Palantir unloaded")
        
        while logger.hasHandlers():
           logger.removeHandler(logger.handlers[0])
        
        del file_handler
        del console_handler

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete, this cog does not store user data """
        return



    @tasks.loop(minutes = 4)
    async def sched_task(self):

        await self.bot.wait_until_red_ready()

        all_configs = await self.config.all_guilds()

        if len(all_configs) == 0:
            logger.warning("There seem to be no active embeds. Stopping.")
            self.sched_task.stop()

        try:
            qcde_servers = await self.scan_servers()
            total_players = await self.check_activity(qcde_servers)

            await self.update_embed(qcde_servers)
            await self.bot.change_presence(activity = discord.Game(f"QC:DE: {total_players} online"))
        except ConnectionResetError as e:
            logger.error(f"Could not update bot status: {e}")
        except Exception:
            logger.exception("sched_task exception")

    async def scan_servers(self) -> list:
        try:
            server_addresses = pyzandro.query_master('master.qzandronum.com:15300')
            self.serverlist_cache = server_addresses
            self.fail_counter = 0
        except PyZandroException:
            logger.warning("The master server did not respond. Working from cache.")
            server_addresses = self.serverlist_cache
            self.fail_counter += 1
        except TimeoutError:
            logger.warning("Request to the master server timed out. Working from cache.")
            server_addresses = self.serverlist_cache
            self.fail_counter += 1

        qcde_serverdata = []

        for server in server_addresses:
            try:
                server_info = {}
                server_info = pyzandro.query_server(server, flags = [SQF.NAME, SQF.MAPNAME, SQF.NUMPLAYERS, SQF.PLAYERDATA, SQF.GAMETYPE, SQF.PWADS, SQF.FORCEPASSWORD])
                for wad_bytes in server_info['pwads']:
                    wad = str(wad_bytes, 'utf-8')
                    if ("qcdev" in wad.lower()):
                        server_info['address'] = server
                        qcde_serverdata.append(server_info)
                        break
            except TimeoutError:
                server_info['name_nocolor'] = "Connection timeout..."
            except ConnectionResetError:
                server_info['name_nocolor'] = "Connection reset..."
            except Exception:
                logger.exception("Exception after querying")
                continue

        return qcde_serverdata

    async def check_activity(self, qcde_serverinfolist) -> int:
        active_servers = self.active_servers
        total_players = 0

        for serverinfo in qcde_serverinfolist:

            address = serverinfo['address']
            num_players = serverinfo['num_players']

            for player in serverinfo['players']:
                if player['bot'] == 1:
                    num_players -= 1

            if num_players >= 1 and not address in active_servers:
                active_servers.append(address)
                logger.info("%-20s %-25s %s", "Player activity on", address, serverinfo['name_nocolor'])

                if len(active_servers) == 1:
                    await self.ping_subscribers()

            if num_players < 1 and address in active_servers:
                active_servers.remove(address)
                logger.info("%-20s %-25s %s", "Server empty", address, serverinfo['name_nocolor'])

            total_players += num_players

        # remove servers that are not reported by master
        addresses_from_master = [s['address'] for s in qcde_serverinfolist]
        leftover_servers = set(active_servers) - set(addresses_from_master)
        for leftover_address in leftover_servers:
            active_servers.remove(leftover_address)
            logger.info("%-20s %s", "Leftover server", address)

        return total_players

    async def generate_embed(self, qcde_servers) -> discord.Embed:
        embed = discord.Embed(title = "QC:DE Servers", description = "​")
        embed.set_author(name = "Palantir", icon_url = self.config_external['icon'])

        try:
            for server in qcde_servers:

                player_list = []
                playernum = server['num_players']

                for player in server['players']:

                    playername = player['name_nocolor']

                    if player['bot'] == 1:
                        playername = f":robot: *{playername}*"
                        playernum -= 1
                    else:
                        playername = f"**{playername}**"

                    player_list.append(playername)

                if playernum > 0:
                    indicator = ":green_circle:"
                else:
                    indicator = ":black_circle:"

                if server['forcepassword'] == True:
                    locked = ":lock:"
                else:
                    locked = ""

                player_list.sort()
                player_list_formatted = ', '.join(player_list)

                server_address = str(server['address']).split(":")
                country = query_geoip(server_address[0])

                if playernum > 0:
                    embed.add_field(name = f":flag_{country.lower()}: {locked} {server['name_nocolor']} - [{server['mapname']}]",
                        value = f"{indicator} Players [{playernum}]: {player_list_formatted}", inline = False)

        except Exception:
            logger.exception("Palantir error")

        if self.fail_counter > 5:
            embed.set_thumbnail(url = self.config_external['thumbnail']['ded'])
            embed.color = 0x222222
            embed.add_field(name = "Service currently unavailable",
                value = "We are studying the ancient codex")

        else:
            if len(embed.fields) == 0:
                if random.randrange(10) == 0:
                    field_value = random.choice(self.config_external["memes"])
                else:
                    field_value = "​"
    
                if random.randrange(50) == 0:
                    thumbnail = random.choice(self.config_external['thumbnail']['memes'])
                else:
                    thumbnail = self.config_external['thumbnail']['inactive']
    
                embed.set_thumbnail(url = thumbnail)
                embed.color = 0xa51d2d
                embed.add_field(name = "The eternal halls are empty",
                    value = field_value)
            else:
                embed.color = 0x1fa51d
                embed.set_thumbnail(url = self.config_external['thumbnail']['active'])

        embed.set_footer(text = "Last updated")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    async def update_embed(self, qcde_servers):
        embed = await self.generate_embed(qcde_servers)

        all_configs = await self.config.all_guilds()

        for guild_id, config_data in all_configs.items():
            msg_id = config_data['embed_id']
            channel = self.bot.get_channel(config_data['channel_id'])

            try:
                msg = await channel.fetch_message(msg_id)
            except AttributeError:
                logger.error("Couldn't fetch embed for %s, channel is None", self.bot.get_guild(guild_id).name)
                continue
            except discord.DiscordServerError as e:
                logger.error(f"Could not retrieve embed to be edited for {self.bot.get_guild(guild_id).name}: {e}")

            if config_data['bot_config_channel'] != 0:
                config_channel = self.bot.get_channel(config_data['bot_config_channel'])

            try:
                await msg.edit(embed = embed)
            except discord.Forbidden:
                if config_data['bot_config_channel'] != 0:
                    await config_channel.send("Palantir error: `No permission to edit message`")
            except discord.DiscordServerError as e:
                logger.error(f"Could not edit the embed for {self.bot.get_guild(guild_id).name}: {e}")


    async def ping_subscribers(self):
        allowed_mentions = discord.AllowedMentions(roles = True)

        all_configs = await self.config.all_guilds()

        for guild_id, config_data in all_configs.items():

            guild_obj = self.bot.get_guild(guild_id)
            channel = self.bot.get_channel(config_data['channel_id'])

            if config_data['role_to_notify'] == 0:
                mention_string = ""
            else:
                role_obj = guild_obj.get_role(config_data['role_to_notify'])
                mention_string = role_obj.mention

            if config_data['bot_config_channel'] != 0:
                config_channel = self.bot.get_channel(config_data['bot_config_channel'])

            try:
                await channel.send(f"{mention_string} A warrior has entered the arenas", allowed_mentions = allowed_mentions, delete_after = 1)
            except discord.Forbidden:
                if config_data['bot_config_channel'] != 0:
                    await config_channel.send(f"Palantir error: `No permission to send messages in` {self.bot.get_channel(channel).mention}")



    ################
    # COG COMMANDS #
    ################

    @commands.group()
    @commands.admin_or_permissions(manage_guild = True)
    @commands.bot_has_guild_permissions(manage_messages = True)
    async def palantir(self, ctx: commands.Context):

        """Watch over the arena eternal by looking into Menelkir's wicked crystal ball"""

        pass

    @palantir.command(name = "setup")
    async def _setup(self, ctx: commands.Context, channel_id:int = None, role_id:int = None):

        """
        Set up a self-updating embed.

        If channel is unset the embed will be sent to the same one the command is executed from.
        If role is unset, no role will be pinged when server activity occurs.

        """

        if await self.config.guild(ctx.guild).embed_id() != 0:
            await ctx.send("You already seem to have set up an embed for this guild. Please use the `delete` command before setting a new one up.")
            return

        if channel_id is None:
            embed_channel = ctx.channel
        else:
            embed_channel = ctx.guild.get_channel(channel_id)

        await self.config.guild(ctx.guild).channel_id.set(embed_channel.id)

        if role_id is not None:
            await self.config.guild(ctx.guild).role_to_notify.set(role_id)
            role_mention = ctx.guild.get_role(role_id).mention
        else:
            role_mention = "no role"

        confirm_msg = await ctx.send(f"The embed will be created for `{ctx.guild.name}` in {embed_channel.mention} and {role_mention} will be notified")
        start_adding_reactions(confirm_msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        predicate = ReactionPredicate.yes_or_no(confirm_msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check = predicate)

        if predicate.result is True:
            embed = await self.generate_embed([])
            msg = await embed_channel.send(embed = embed)
            await self.config.guild(ctx.guild).embed_id.set(msg.id)
        else:
            await ctx.send("Cancelled.")
            return

        if not self.sched_task.is_running():
            self.sched_task.start()

    @palantir.command(name = "delete")
    async def _delete(self, ctx: commands.Context, guildID: int):

        """
        Delete a guild's self-updating embed. Issue this command from the guild you'd like to delete the embed for.
        Supplying a guild ID is required to avoid accidental deletions.
        """

        if guildID != ctx.guild.id:
            await ctx.send("Guild ID doesn't match the guild you're issuing the command from.")
            return

        all_configs = await self.config.all_guilds()

        if len(all_configs) == 0:
            ctx.send("It seems you don't have anything set up yet.")

        if guildID not in all_configs:
            ctx.send("It seems you have no embed set up for this guild.")

        for guild_id, config_data in all_configs.items():
            if guild_id == guildID:
                msg_id = config_data['embed_id']

                if msg_id == 0:
                    await ctx.send(f"There seems to be no valid embed for `{self.bot.get_guild(guild_id).name}`")
                    return

                channel = self.bot.get_channel(config_data['channel_id'])
                break


        try:
            msg = await channel.fetch_message(msg_id)

        except AttributeError:
            await ctx.send(f"Couldn't fetch embed for `{self.bot.get_guild(guild_id).name}`, channel is `None`")
            return

        except discord.NotFound:

            error_msg = await ctx.send("Cannot find the message. Purge config for this guild?")
            start_adding_reactions(error_msg, ReactionPredicate.YES_OR_NO_EMOJIS)

            predicate = ReactionPredicate.yes_or_no(error_msg, ctx.author)
            await ctx.bot.wait_for("reaction_add", check = predicate)

            if predicate.result is True:
                await self.config.guild_from_id(guildID).clear()
                await ctx.send("Guild config purged.")
                return
            else:
                await ctx.send("Cancelled.")
                return

        try:
            await msg.delete()

        except discord.Forbidden:
            await ctx.send("Couldn't delete the embed, please make sure I have the right permissions!")
            return

        await self.config.guild_from_id(guildID).clear()
        await ctx.send(f"Deleted embed for `{self.bot.get_guild(guild_id).name}`")


    @palantir.command(name = "stop")
    async def _stop(self, ctx: commands.Context):

        """
        Stops the cog's scheduled task.
        Warning! This will stop updating all existing embeds and will affect all guilds!
        """

        if self.sched_task.is_running():

            async with ctx.typing():
                self.sched_task.cancel()
                await asyncio.sleep(1)

            if not self.sched_task.is_running():
                await ctx.send("Server querying stopped.")
            else:
                await ctx.send("Could not stop server querying.")

        else:
            await ctx.send("Server querying is already stopped.")

    @palantir.command(name = "start")
    async def _start(self, ctx: commands.Context):

        """
        Starts the cog's scheduled task.
        Warning! This will start updating existing embeds and will affect all guilds!
        """

        if not self.sched_task.is_running():

            async with ctx.typing():
                self.sched_task.start()
                await asyncio.sleep(1)

            if self.sched_task.is_running():
                await ctx.send("Server querying started.")
            else:
                await ctx.send("Could not start server querying.")

        else:
            await ctx.send("Server querying is already running.")

    @palantir.command(name = "reload_json")
    async def _reload_config(self, ctx: commands.Context):

        """
        Reload the external JSON file.
        """

        self.config_external = load_external_config()
        await ctx.send("External JSON reloaded.")



    #########################
    # COG SETTINGS COMMANDS #
    #########################

    @palantir.command(name = "notifyrole")
    async def set_role(self, ctx: commands.Context, role_id: int = None):

        """
        Get or set the role to be notified of server activities.
        Set this to 0 to turn off notifications.
        """

        if role_id is None:
            ping_role_id = await self.config.guild(ctx.guild).role_to_notify()
            if ping_role_id == 0:
                await ctx.send("Role is `unset`")
            else:
                ping_role_name = ctx.guild.get_role(ping_role_id).name
                await ctx.send(f"Role to notify is currently set to: `{ping_role_name}`, ID: `{ping_role_id}`")

        else:
            await self.config.guild(ctx.guild).role_to_notify.set(role_id)
            if role_id == 0:
                await ctx.send("Role unset.")
            else:
                await ctx.send(f"The following role will be notified: `{ctx.guild.get_role(role_id).name}`")

    @palantir.command(name = "configchannel")
    async def set_conf_channel(self, ctx: commands.Context, channel_id: int = None):

        """
        Get or set the channel to recieve error messages. If this is not set, no error messages will be provided.
        Set this to 0 to turn off diagnostic messages.
        """

        if channel_id is None:
            conf_chan_id = await self.config.guild(ctx.guild).bot_config_channel()
            if conf_chan_id == 0:
                await ctx.send("Bot config channel is `unset`.")
            else:
                conf_chan_name = ctx.guild.get_channel(conf_chan_id).name
                await ctx.send(f"Bot settings channel currently set to: `{conf_chan_name}`, ID: `{conf_chan_id}`")

        else:
            await self.config.guild(ctx.guild).bot_config_channel.set(channel_id)
            if channel_id == 0:
                await ctx.send("Bot config channel unset.")
            else:
                await ctx.send(f"Error messages will be sent to: {self.bot.get_channel(channel_id).mention}")

    @palantir.command(name = "setinterval")
    async def set_query_interval(self, ctx: commands.Context, hrs = 0, mins = 0, secs = 0):

        """
        Get or set server querying interval.
        Warning! This is a global setting and will affect all guilds.
        Query interval cannot be 0.
        """

        if all(arg == 0 for arg in [hrs, mins, secs]):
            await ctx.send(f"Server query interval is currently: \n\
            `{self.sched_task.hours}` hours, \n\
            `{self.sched_task.minutes}` minutes, \n\
            `{self.sched_task.seconds}` seconds")
        else:
            self.sched_task.change_interval(seconds = secs, minutes = mins, hours = hrs)
            await ctx.send(f"Server query interval now set to: `{hrs}` hours, `{mins}` minutes and `{secs}` seconds.")

    ##################
    # DEBUG COMMANDS #
    ##################

    @palantir.group(hidden = True)
    @commands.is_owner()
    async def debug(self, ctx: commands.Context):

        """Secret testing tools"""
        pass

    @debug.command(name = "dumpconfig", hidden = True)
    async def _dumpconfig(self, ctx: commands.Context, scope: str = "guild"):

        """
        A tool to quickly check the cog's config
        Scope may be 'guild' or 'global', defaults to guild.
        """

        if scope.lower() == "guild":
            guild_group = self.config.guild(ctx.guild)
            raw_config = await guild_group.get_raw()
        elif scope.lower() == "global":
            raw_config = await self.config.all_guilds()
        else:
            await ctx.send("Invalid scope, use 'guild' or 'global'")
            return

        await ctx.send(f"```\n{pprint.pformat(raw_config)}\n```")

    @debug.command(name = "dumpserverinfo", hidden = True)
    async def _dumpserverinfo(self, ctx: commands.Context):

        """A tool to get raw server data as a text file"""

        async with ctx.typing():
            servers = await self.scan_servers()

            with open("serverdata.txt", "w") as file:
                file.write(pprint.pformat(servers))

            with open("serverdata.txt", "rb") as file:
                await ctx.send("Server query output", file = discord.File(file, "serveroutput.txt"))

        os.remove("serverdata.txt")

    @palantir.command(name = "getlog")
    async def _get_log(self, ctx: commands.Context, mode: str = "latest"):

        """
        A command to download the log of this cog.
        You can pass 'latest' or 'all' as mode, defaults to latest.
        """

        async with ctx.typing():
            
            if mode.lower() == "latest":
                with open(LOGFILE, "rb") as file:
                    await ctx.send("Latest log file", file = discord.File(file, "palantir_verbose.log"))
            
            elif mode.lower() == "all":
                log_archive = shutil.make_archive("palantir_logs", "zip", os.path.join(COG_PATH, "logs"),)
                
                with open(log_archive, "rb") as file:
                    await ctx.send("All log files", file = discord.File(file, "palantir_logs.zip"))
                
                os.remove(log_archive)
            
            else:
                await ctx.send("Invalid mode, use 'latest' or 'all'")

    
    @debug.command(name = "eval", hidden = True)
    async def _eval(self, ctx: commands.Context, *exprs):

        """A tool to evaluate expressions in their running environment"""

        expr = " ".join(exprs)
        try:
            try:
                if expr.startswith('await '):
                    result = await eval(expr[6:])
                else:
                    result = eval(expr)
            except SyntaxError:
                exec(expr)
                result = "Executed statement: " + repr(expr)
            await ctx.send(f"```\n{pprint.pformat(result)}\n```")
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            result = '\n'.join(traceback.format_exception(exc_type, exc_value,exc_traceback))
            await ctx.send(f"```\n{result}\n```")
