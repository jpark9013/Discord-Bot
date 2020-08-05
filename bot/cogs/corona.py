import corona_api
import discord
from discord.ext import commands

from bot.utils.message import send_embed

# Short for coronaclient
cc = corona_api.Client()


# f"{n:,}" to format number

def format_number(n):
    if not n:  # 0 or None
        return "Unknown"
    return f"{n:,}"


class Corona(commands.Cog, name="Corona"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(aliases=["covid", "covid-19", "covid19", "cv", "corona"])
    async def coronavirus(self, ctx, country=None, *, state=None):
        """Get the statistics for coronavirus for a certain country and optionally province/state. Defaults to all
        countries."""
