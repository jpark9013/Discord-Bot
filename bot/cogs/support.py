import json
from datetime import datetime

import discord
from discord.ext import commands

from bot.utils.message import send_embed


class Support(commands.Cog, name="Support"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.id = 1

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def support(self, ctx):
        await send_embed(ctx, "Send a support message with ``;support create``!", info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @support.command()
    async def create(self, ctx, *, suggestion):
        """Create a new support ticket"""

        with open("supportTicketID.json", "r") as f:
            num = json.load(f)

        channel = self.bot.get_guild(721194829366951997).get_channel(735612451839672340)

        embed = discord.Embed(
            title="New Suggestion",
            description=suggestion
        )

        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
        embed.set_footer(text=f"ID: {num} | Time: {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

        await channel.send(embed=embed)
        await send_embed(ctx, "Suggestion has been sent.")

        num += 1
        with open("supportTicketID.json", "w") as f:
            json.dump(num, f)
