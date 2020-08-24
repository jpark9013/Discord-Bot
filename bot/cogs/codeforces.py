import json
import time

from aiocodeforces import client as cfclient
import discord
from discord.ext import commands, tasks

from utils.format import send_embed, shorten, to_datetime


class Codeforces(commands.Cog, name="Codeforces"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.cfclient = cfclient.Client(session=self.bot.session)
        self.first = True
        self.contests = None
        pass

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def getcontestreminders(self, ctx):
        """Enable or disable contest reminders for CodeForces through DMs."""

        if ctx.author.id in self.bot.codeforces:
            self.bot.codeforces.remove(ctx.author.id)
            message = "Disabled reminders for CodeForces contests."
        else:
            self.bot.codeforces.append(ctx.author.id)
            message = "Enabled reminders for CodeForces contests."

        with open("codeforces.json", "w") as f:
            json.dump(self.bot.codeforces, f, indent=4)
        await send_embed(ctx, message)

    @tasks.loop(minutes=2)
    async def get_contests(self):
        print("hello")
        if self.first:
            print("here")
            self.contests = await self.cfclient.get_contest_list()
            print("ok")
            return

        temp = set(self.contests)
        temp1 = [i for i in await self.cfclient.get_contest_list() if i not in temp]

        embeds = []
        for contest in reversed(temp1):
            embed = discord.Embed(
                title="New Contest",
                url=f"https://codeforces.com/contest/{contest.id}",
                description=shorten(contest.description)
            )
            embed.set_footer(text=f"Starts in {to_datetime(contest.start_time_seconds - time.time(), week=True)}")
            embeds.append(embed)

        for i in self.bot.codeforces:
            user = self.bot.get_user(i)
            try:
                for j in embeds:
                    await user.send(embed=j)
            except AttributeError:
                pass


def setup(bot):
    bot.add_cog(Codeforces(bot))
