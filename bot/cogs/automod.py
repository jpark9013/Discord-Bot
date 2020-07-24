import time

import discord
from discord.ext import commands

from bot.utils.message import send_embed


class AutoMod(commands.Cog, name="AutoMod"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    # Banned words command is in guildsetup, because I'm too lazy to move it here along with the rest of the DB
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()

