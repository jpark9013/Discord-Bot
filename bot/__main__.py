# import asyncio
import json
import re
import time
from datetime import datetime

import aiohttp
import aiosqlite3
import discord
# import youtube_dl

from discord.ext import commands
from bot.utils.message import to_embed
from bot.utils.paginator import Paginator

with open("token.txt", "r") as file:
    TOKEN = file.readline()


class HumphreyGaming(commands.AutoShardedBot):
    def __init__(self):

        def get_prefix(self, message):
            with open("prefixes.json", "r") as f:
                prefixes = json.load(f)

            try:
                return prefixes[str(message.guild.id)]
            except KeyError:
                return ";"

        super().__init__(command_prefix=get_prefix, case_insensitive=True, help_command=None)

        # Status changing stuff
        self.statuses = []
        self.autostatus = False
        self.reverse_order = False
        self.split = " "
        self.x = 0

        self.loop.run_until_complete(self.con())
        self.loop.run_until_complete(self.session())

        self.load_extension("bot.cogs")
        self.load_extension("jishaku")

        self.startTime = time.time()

        self.invite_regex = re.compile("(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?")
        self.link_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
        self.emoji_regex = re.compile("<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>")

    async def con(self):
        self.db = await aiosqlite3.connect("DiscordServers.db")

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
                                   activity=discord.Game(f";help"))

        channel = self.get_guild(732980515807952897).get_channel(736352506669694976)

        embed = discord.Embed(
            colour=discord.Colour.green(),
            description="Bot is online."
        )
        embed.set_footer(text=f"Time: {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

        await channel.send(embed=embed)

    def can_send(self, message):
        return isinstance(message.channel, discord.DMChannel) or \
               message.channel.permissions_for(message.guild.me).send_messages

    async def on_message(self, message):

        ctx = await self.get_context(message)

        with open("blacklist.json") as f:
            blacklist = json.load(f)
        if ctx.author.bot or not self.is_ready() or not self.can_send(message) or \
                (ctx.guild and ctx.guild.id in blacklist["guilds"]):
            return

        cursor = await self.db.execute("Select * from AutoMod where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result and ctx.guild and ctx.channel.id not in json.loads(result[9]):

            if result[1]:
                if message.content.isupper() and len(message.content) > 7:
                    return await message.delete()

            if result[2]:
                cursor = await self.db.execute("""Select firstTime, Times from FastMessageSpam
                where GuildID = ? and MemberID = ?""", (ctx.guild.id, ctx.author.id))
                result = await cursor.fetchone()

                if not result:
                    await self.db.execute("Insert into FastMessageSpam values (?, ?, ?, ?)",
                                          (ctx.guild.id, ctx.author.id, time.time(), 1))
                    await self.db.commit()

                else:
                    if time.time() <= result[0] + 5:

                        if result[1] == 5:
                            cmd = self.get_command("mute")
                            return await cmd(ctx, member=ctx.author, reason="Automuted due to spam.")

                        else:
                            await self.db.execute("""Update FastMessageSpam set Times = Times + 1
                            where GuildID = ? and MemberID = ?""", (ctx.guild.id, ctx.author.id))
                            await self.db.commit()

                    else:
                        await self.db.execute("Delete from FastMessageSpam where GuildID = ? and MemberID = ?",
                                              (ctx.guild.id, ctx.author.id))
                        await self.db.commit()

            if result[3]:
                if self.invite_regex.search(message.content):
                    return await message.delete()

            if result[4]:
                if self.link_regex.search(message.content):
                    return await message.delete()

            if result[5]:
                if message.mentions > 5:
                    return await message.delete()

            if result[6]:
                if len(self.emoji_regex.findall(message.content)) >= 10:
                    return await message.delete()

            if result[7]:
                for i in message.content.split():
                    if len(i) >= 5 and i[0] == "|" and i[1] == "|" and i[-1] == "|" and i[-2] == "|":
                        return await message.delete(reason="Spoiler detected.")

            if result[8]:
                if message.embeds:
                    cmd = self.get_command("ban")
                    return await cmd(ctx, member=ctx.author, reason="Selfbot detected")

        cursor = await self.db.execute("Select Channels, Words from Blacklist where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result:
            if not ctx.author.guild_permissions.administrator:
                for i in json.loads(result[1]):
                    if i in message.content.split():
                        try:
                            return await message.delete()
                        except discord.Forbidden:
                            return

            if ctx.channel.id in json.loads(result[0]):
                return

        if ctx.author.id in blacklist["members"]:
            return

        await self.process_commands(message)

    async def on_command(self, ctx):

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
