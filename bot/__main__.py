# import asyncio
import json
import time

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

    return prefixes[str(message.guild.id)]


class HumphreyGaming(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(command_prefix=get_prefix, case_insensitive=True)
        self.loop.run_until_complete(self.con())
        self.load_extension("bot.cogs")
        self.startTime = time.time()
        self.remove_command("help")

    async def con(self):
        self.db = await aiosqlite3.connect("DiscordServers.db")

    async def session(self):
        async with aiohttp.ClientSession() as httpsession:
            self.session = httpsession

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

        for i in create_tables:
            await self.db.execute(i)
            await self.db.commit()

        print("Logged in as")  # Didn't use \n on purpose
        print(self.user.name)
        print(self.user.id)
        print("------")
        await self.change_presence(status=discord.Status.online,
                                   activity=discord.Game(f";help for help"))

    def can_send(self, message):
        return isinstance(message.channel, discord.DMChannel) or \
               message.channel.permissions_for(message.guild.me).send_messages

    async def on_message(self, message):
        with open("blacklist.json") as f:
            blacklist = json.load(f)
        if message.author.bot or not self.is_ready() or not self.can_send(message) or message.author in \
                blacklist["members"] or message.guild in blacklist["guilds"]:
            return
        await self.process_commands(message)


# Running the bot
bot = HumphreyGaming()
bot.run()
