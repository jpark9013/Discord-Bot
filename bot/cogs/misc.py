import json
import random
import statistics

import discord
import wikipedia
from discord.ext import commands

from bot.utils.format import send_embed, to_embed


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(aliases=["randomnumber", "randomint", "randominteger"])
    async def randomnum(self, ctx, num1: int = 0, num2: int = 100):
        """Pick a random integer inclusive. Default range is from 0 to 100."""

        await send_embed(ctx, str(random.randint(num1, num2)), info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    async def randomfloat(self, ctx, num1: float = 0, num2: float = 100):
        """Pick a random float. Default range is from 0 to 100."""

        await send_embed(ctx, str(random.uniform(num1, num2)), info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    async def format(self, ctx, language: str, *, text: str):
        """Format a text block in a language."""

        await ctx.send(f"```{language}\n"
                       f"{text}\n"
                       f"```")

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(aliases=["haste"])
    async def hastebin(self, ctx, *, payload: str):
        """Posts the content to hastebin, then returns the link."""

        try:
            async with self.bot.session.post(url="https://hastebin.com/documents", data=payload) as response:
                key = json.loads(await response.content.read())["key"]

            await send_embed(ctx, f"https://hastebin.com/{key}", info=True)

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(aliases=["wiki"])
    async def wikipedia(self, ctx, *, text: str):
        """Search something up on wikipedia"""

        def convert_large(textc):
            if len(textc) > 1024:
                textc = ("".join(list(textc)[:1024])).split()
                if len(textc[-1]) >= 3:
                    textc[-1] = "..."
                    return " ".join(textc)
                else:
                    del textc[-1]
                    textc[-1] = "..."
                    return " ".join(textc)
            else:
                return textc

        try:
            page = wikipedia.page(text)
            embed = discord.Embed(
                colour=discord.Colour.blue(),
                title=page.title,
                url=page.url
            )

            embed.set_thumbnail(url=page.images[0])
            embed.add_field(name="Summary", value=convert_large(wikipedia.summary(text)))
            await ctx.send(embed=embed)

        except wikipedia.DisambiguationError as e:
            description = "\n".join(e.options)
            embed = discord.Embed(colour=discord.Colour.blue(),
                                  title=f"{text.capitalize()} may refer to:",
                                  description=description
                                  )
            await ctx.send(embed=embed)

        except wikipedia.PageError:
            try:
                page = wikipedia.page((wikipedia.suggest(text)))
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title=f"(Suggested) {page.title}",
                    url=page.url
                )

                embed.set_thumbnail(url=page.images[0])
                embed.add_field(name="Summary", value=convert_large(wikipedia.summary(wikipedia.suggest(text))))
                await ctx.send(embed=embed)

            except Exception as e:
                await send_embed(ctx, str(e), negative=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def ping(self, ctx):
        """Returns your ping."""

        ping = self.bot.latency * 1000

        await db.execute("Insert into Ping values (?, ?)", (ctx.author.id, ping))
        await db.commit()

        await send_embed(ctx, f"Your ping is **{round(ping)} ms**", info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @ping.command()
    async def average(self, ctx):
        """Returns your average ping."""

        cursor = await db.execute("Select Value from Ping where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchall()

        if not result:
            return await send_embed(ctx, "You do not have any pings sent yet.", negative=True)

        result = [i[0] for i in result]

        await send_embed(ctx, f"Your average ping is **{round(statistics.mean(result))}** ms.", info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @ping.command()
    async def history(self, ctx):
        """Returns your ping history."""

        cursor = await db.execute("Select Value from Ping where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "You do not have any pings sent yet.", negative=True)

        embeds = []
        result = [i[0] for i in result]
        resultstr = []
        for i, v in enumerate(reversed(result), start=1):
            resultstr.append(f"{i}. {round(v)} ms")
            if i % 10 == 0 or i == len(result):
                embeds.append(await to_embed("\n".join(resultstr), info=True))
                resultstr = []

        await self.bot.paginate(ctx, embeds)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    async def botinvite(self, ctx, member: discord.Member = None):
        """Generate a bot invite given the bot. Defaults to this bot."""

        if not member:
            return await send_embed(ctx, f"[Click me]"
                                         f"(https://discord.com/api/oauth2/authorize?client_id=718287109030543370"
                                         f"&permissions=8&scope=bot)", info=True)

        if not member.bot:
            return await send_embed(ctx, "Invalid bot.", negative=True)

        await send_embed(ctx,
                         f"[Click Me](https://discord.com/oauth2/authorize?client_id={member.id}"
                         f"&scope=bot&permissions=0)",
                         info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def reversetext(self, ctx, *, text: str):
        """Reverse text."""

        await send_embed(ctx, text[::-1], info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["converttoimperial", "ctf", "cti"])
    async def converttofeet(self, ctx, meters: float):
        """Convert meters to feet and inches."""

        if meters <= 0 or meters > 100000000000:
            return await send_embed(ctx, "Invalid input.", negative=True)

        inches = 39.3701 * meters
        feet, inches = divmod(inches, 12)
        feet = int(feet)
        inches = round(inches, 2)

        await send_embed(ctx, f"{feet} feet {inches} inches", info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["converttoeuropean", "cte", "ctm"])
    async def converttometers(self, ctx, feet: int, inches: float = 0):
        """Convert feet and inches to meters."""

        if feet <= 0 or feet > 1000000000 or inches < 0 or inches > 1000000000000:
            return await send_embed(ctx, "Invalid input.", negative=True)

        inches = feet * 12 + inches
        meters = round(inches/39.3701, 2)

        await send_embed(ctx, f"{meters} meters", info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def flip(self, ctx):
        """Returns with Heads or Tails."""

        await send_embed(ctx, random.choice(("Heads", "Tails")), info=True)
