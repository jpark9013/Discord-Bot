import json

import aiosqlite3
import discord
from discord.ext import commands

from bot.utils.message import send_embed


class Guild_Setup(commands.Cog, name="Guild Setup"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        with open("bot/prefixes.json", "r") as prefixes_file:
            prefixes = json.load(prefixes_file)

        if str(guild.id) not in prefixes:
            prefixes[str(guild.id)] = ";"

        with open("bot/prefixes.json", "w") as prefixes_file:
            json.dump(prefixes, prefixes_file, indent=4)

        cursor = await db.execute("Select count(*) from Logging where GuildID = ?", (guild.id,))
        result = await cursor.fetchone()

        if result[0] == 0:
            await db.execute("Insert into Logging values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                             "?, ?, ?, ?, ?)",
                             (guild.id, None, json.dumps([]), False, False, False, False, False, False, False, False,
                              False, False, False,
                              False, False, False, False, False, False, False, False, False, False, False))
            await db.commit()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def changeprefix(self, ctx, prefix: str):
        if len(prefix) > 5:
            return await send_embed(ctx, f"You cannot have a prefix more than 5 characters long.")
        with open("bot/prefixes.json", "r") as prefixes_file:
            prefixes = json.load(prefixes_file)

        prefixes[str(ctx.guild.id)] = prefix

        with open("bot/prefixes.json", "w") as prefixes_file:
            json.dump(prefixes, prefixes_file, indent=4)

        await send_embed(ctx, f"Guild prefix changed to ``{prefix}``.")
