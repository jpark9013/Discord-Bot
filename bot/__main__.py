# import asyncio
import json
import time
from datetime import datetime

import aiohttp
import aiosqlite3
import discord
# import youtube_dl

from discord.ext import commands
from bot.utils.paginator import Paginator

with open("token.txt", "r") as file:
    TOKEN = file.readline()

with open("createtables.json", "r") as file:
    """List of Database tables to create"""

    create_tables = json.load(file)


def get_prefix(bot, message):
    with open("prefixes.json", "r") as file3:
        prefixes = json.load(file3)

    try:
        return prefixes[str(message.guild.id)]
    except KeyError:
        return ";"


class HumphreyGaming(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=get_prefix, case_insensitive=True, help_command=None)

        # Status changing stuff
        self.statuses = []
        self.autostatus = False
        self.reverse_order = False
        self.split = " "
        self.x = 0

        self.loop.run_until_complete(self.con())
        self.session = aiohttp.ClientSession()

        self.remove_command("help")
        self.load_extension("bot.cogs")

        self.startTime = time.time()

    async def con(self):
        self.db = await aiosqlite3.connect("DiscordServers.db")

    async def paginate(self, ctx, entries: list, embed=True):
        p = Paginator(ctx, entries=entries, embed=embed)
        return await p.paginate()

    def run(self):
        self.loop.run_until_complete(self.bot_start())

    async def bot_start(self):
        for i in create_tables:
            await self.db.execute(i)
            await self.db.commit()

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

    def can_send(self, message):
        return isinstance(message.channel, discord.DMChannel) or \
               message.channel.permissions_for(message.guild.me).send_messages

    async def on_message(self, message):
        with open("blacklist.json") as f:
            blacklist = json.load(f)
        if message.author.bot or not self.is_ready() or not self.can_send(message) or message.author.id in \
                blacklist["members"] or message.guild.id in blacklist["guilds"]:
            return

        cursor = await self.db.execute("Select Channels, Words from Blacklist where GuildID = ?", (message.guild.id,))
        result = await cursor.fetchone()

        if result:
            if message.channel.id in json.loads(result[0]):
                return

            if not message.author.guild_permissions.administrator:
                for i in json.loads(result[1]):
                    if i in message.content.split():
                        try:
                            return await message.delete()
                        except:
                            return

        await self.process_commands(message)

        cursor = await self.db.execute("Select count(*) from Commands where MemberID = ?", (message.author.id,))
        result = await cursor.fetchone()

        if result[0]:
            await self.db.execute("Update Commands set Uses = Uses + 1 where MemberID = ?", (message.author.id,))
            await self.db.commit()

        else:
            await self.db.execute("Insert into Commands values (?, ?)", (message.author.id, 1))
            await self.db.commit()

    async def on_command(self, ctx):
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
