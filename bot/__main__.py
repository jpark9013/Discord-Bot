import json
import logging
import os
import re
import time
from datetime import datetime

import aiohttp
import aiosqlite
import discord
from discord.ext import commands

from utils.paginator import Paginator

logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

with open("token.txt", "r") as file:
    TOKEN = file.readline()


class HumphreyGaming(commands.AutoShardedBot):
    def __init__(self):

        def get_prefix(bot, message):

            try:
                return self.prefixes[str(message.guild.id)]
            except KeyError:
                return "?"
            except AttributeError:
                return "?"

        super().__init__(command_prefix=get_prefix, case_insensitive=True, help_command=None)

        # Status changing stuff
        self.statuses = []
        self.autostatus = False
        self.reverse_order = False
        self.split = " "
        self.x = 0

        self.loop.run_until_complete(self.con())
        self.loop.run_until_complete(self.session())
        self.loop.run_until_complete(self.send_to_cache())

        for f in os.listdir("./cogs"):
            if f.endswith(".py") and str(f) != "__init__.py":
                self.load_extension(f"cogs.{f[:-3]}")
        self.load_extension("jishaku")

        self.startTime = time.time()

        self.invite_regex = re.compile("(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?")
        self.link_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
        self.emoji_regex = re.compile("<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>")
        self.alpha_regex = re.compile("[^a-zA-Z]")
        self.token_regex = re.compile("([a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}|mfa\.[a-zA-Z0-9_\-]{84})")

        with open("prefixes.json", "r") as f:
            self.prefixes = json.load(f)

        with open("blacklist.json", "r") as f:
            self.blacklist = json.load(f)

        with open("muterole.json", "r") as f:
            self.muteroles = json.load(f)

        with open("supportTicketID.json", "r") as f:
            self.support_ticket_number = json.load(f)

        with open("codeforces.json", "r") as f:
            self.codeforces = json.load(f)

    async def send_to_cache(self):
        cursor = await self.db.execute("Select * from AutoMod")
        result = await cursor.fetchall()
        self.automod = {i[0]: list(i[1:]) for i in result}

        cursor = await self.db.execute("Select * from AutomodIgnoredChannels")
        result = await cursor.fetchall()
        self.automodignoredchannels = {}
        for i in result:
            if i[0] in self.automodignoredchannels:
                self.automodignoredchannels[i[0]].add(i[1])
            else:
                self.automodignoredchannels[i[0]] = {i[1]}

        cursor = await self.db.execute("Select * from Blacklist")
        result = await cursor.fetchall()
        self.blacklistchannels = {}
        for i in result:
            if i[0] in self.blacklistchannels:
                if i[1]:
                    self.blacklistchannels[i[0]]["channels"].add(i[1])
                else:
                    self.blacklistchannels[i[0]]["words"].add(i[2])
            else:
                if i[1]:
                    self.blacklistchannels[i[0]] = {"words": set(), "channels": {i[1]}}
                else:
                    self.blacklistchannels[i[0]] = {"words": {i[2]}, "channels": set()}

        cursor = await self.db.execute("Select * from AutoRespond")
        result = await cursor.fetchall()
        self.autorespond = {}
        for i in result:
            if i[0] in self.autorespond:
                self.autorespond[i[0]][i[1]] = i[2]
            else:
                self.autorespond[i[0]] = {i[1]: i[2]}

        self.fastmessagespam = {}

    async def con(self):
        self.db = await aiosqlite.connect("Servers.db")

    async def session(self):
        self.session = aiohttp.ClientSession()

    async def paginate(self, ctx, entries: list, embed=True):
        p = Paginator(ctx, entries=entries, embed=embed)
        return await p.paginate()

    def run(self):
        self.loop.run_until_complete(self.bot_start())

    async def bot_start(self):
        await self.login(TOKEN)
        await self.connect(reconnect=True)

    async def on_ready(self):
        """Everything that follows this is mostly initialization stuff."""

        print("Logged in as")  # Didn't use \n on purpose
        print(self.user.name)
        print(self.user.id)
        print("------")
        await self.change_presence(status=discord.Status.online,
                                   activity=discord.Game(f"?help"))

        channel = self.get_guild(732980515807952897).get_channel(736352506669694976)

        embed = discord.Embed(
            colour=discord.Colour.green(),
            description="Bot is online."
        )

        embed.set_footer(text=f"Time: {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

        await self.wait_until_ready()

        await channel.send(embed=embed)

    def can_send(self, message):
        return isinstance(message.channel, discord.DMChannel) or \
               message.channel.permissions_for(message.guild.me).send_messages

    async def delete_message(self, message):
        try:
            return await message.delete()
        except discord.Forbidden:
            pass

    async def on_message(self, message):
        ctx = await self.get_context(message)

        if ctx.author.bot or not self.is_ready() or not self.can_send(message) or \
                (ctx.guild and ctx.guild.id in self.blacklist["guilds"]):
            return

        if not ctx.guild:
            if ctx.author.id in self.blacklist["members"]:
                return
            return await self.process_commands(message)

        result = self.automod.get(ctx.guild.id, None)
        ignoredchannels = self.automodignoredchannels.get(ctx.guild.id, set())

        if result and ctx.guild and ctx.channel.id not in ignoredchannels:

            if result[0]:
                sub = self.alpha_regex.sub("", message.content)
                if sub.isupper() and len(sub) > 7:
                    return await self.delete_message(message)

            if result[1]:
                if ctx.guild.id not in self.fastmessagespam:
                    self.fastmessagespam[ctx.guild.id] = {ctx.author.id: {"starttime": time.time(), "times": 0}}
                dic = self.fastmessagespam[ctx.guild.id]

                if ctx.author.id not in dic:
                    self.fastmessagespam[ctx.guild.id][ctx.author.id] = {"starttime": time.time(), "times": 0}
                dic = dic[ctx.author.id]

                if dic["starttime"]+5 >= time.time():
                    dic["times"] += 1
                    if dic["times"] >= 5:
                        del self.fastmessagespam[ctx.guild.id][ctx.author.id]
                        cmd = self.get_command("mute")
                        try:
                            return await cmd(ctx, member=ctx.author, reason="Automuted by bot for spam.")
                        except discord.Forbidden:
                            return

                else:
                    del self.fastmessagespam[ctx.guild.id][ctx.author.id]

            if result[2]:
                if self.invite_regex.search(message.content):
                    return await self.delete_message(message)

            if result[3]:
                if self.link_regex.search(message.content):
                    return await self.delete_message(message)

            if result[4]:
                if len(message.mentions) >= 5:
                    return await self.delete_message(message)

            if result[5]:
                if len(self.emoji_regex.findall(message.content)) >= 7:
                    return await self.delete_message(message)

            if result[6]:
                for i in message.content.split():
                    if len(i) >= 5 and i[0] == "|" and i[1] == "|" and i[-1] == "|" and i[-2] == "|":
                        return await self.delete_message(message)

            if result[7]:
                if message.embeds:
                    cmd = self.get_command("ban")
                    return await cmd(ctx, member=ctx.author, reason="Selfbot detected")

        blacklist_guild = self.blacklistchannels.get(ctx.guild.id, {})
        blacklisted_channels = blacklist_guild.get("channels", set())
        blacklisted_words = blacklist_guild.get("words", set())

        if ctx.channel.id in blacklisted_channels:
            return

        content = message.content.lower().split()

        if any(i.lower() in content for i in blacklisted_words):
            return await self.delete_message(message)

        if ctx.author.id in self.blacklist["members"]:
            return

        msg = message.content.lower()

        a = self.autorespond.get(ctx.guild.id, {})
        respond = a.get(msg, None)
        try:
            return await ctx.send(respond)
        except discord.errors.HTTPException:
            pass

        await self.process_commands(message)

    async def on_command(self, ctx):

        await self.wait_until_ready()

        if isinstance(ctx.channel, discord.DMChannel):
            embed = discord.Embed(
                colour=discord.Colour.blue(),
                title="Command Used",
                description="DMChannel\n"
                            f"Author: {ctx.author.mention}\n"
                            f"Command/Content: {ctx.message.content}"
            )

        else:
            embed = discord.Embed(
                colour=discord.Colour.blue(),
                title="Command Used",
                description=f"Guild: {ctx.guild.name} ({ctx.guild.id})\n"
                            f"Author: {ctx.author.mention}\n"
                            f"Channel: {ctx.channel.name} ({ctx.channel.id})\n"
                            f"Command/Content: {ctx.message.content}"
            )

        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
        embed.set_footer(text=f"Time: {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

        channel = self.get_guild(721194829366951997).get_channel(735309492757069896)
        await channel.send(embed=embed)


# Running the bot
bot = HumphreyGaming()
bot.run()
