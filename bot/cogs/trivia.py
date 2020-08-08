import asyncio
import random

import aiotrivia
import discord
from discord.ext import commands

from bot.utils.format import send_embed


class Trivia(commands.Cog, name="Trivia"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.trivia = aiotrivia.TriviaClient()
        self.categories = {
            "general knowledge": 9,
            "entertainment: books": 10,
            "entertainment: film": 11,
            "entertainment: music": 12,
            "entertainment: musicals & theatres": 13,
            "entertainment: television": 14,
            "entertainment: video games": 15,
            "entertainment: board games": 16,
            "science & nature": 17,
            "science: computers": 18,
            "science: mathematics": 19,
            "mythology": 20,
            "sports": 21,
            "geography": 22,
            "history": 23,
            "politics": 24,
            "art": 25,
            "celebrities": 26,
            "animals": 27,
            "vehicles": 28,
            "entertainment: comics": 29,
            "science: gadgets": 30,
            "entertainment: japanese anime & manga": 31,
            "entertainment: cartoon & animations": 32
        }

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True, aliases=["quiz"])
    async def trivia(self, ctx, type=None, difficulty=None, *, category=None):
        """Get a trivia question. Possible types are ``multiple`` or ``true/false``. Possible levels of difficulty are
        ``easy``, ``medium``, and ``hard``. Do ``categories`` for the full list of categories.
        You have two minutes to respond. Also to count a question towards the leaderboard/stats you have to leave all
        arguments blank or random."""

        typeR = False
        diffR = False
        catR = False

        if not type or type.lower() == "r" or type.lower() == "random":
            type = random.choice(("multiple", "boolean"))
            typeR = True
        type = type.lower()
        if type == "true/false" or type == "t/f" or type == "tf" or type == "true false":
            type = "boolean"
        elif type == "m":
            type = "multiple"

        if not difficulty or difficulty.lower() == "r" or difficulty.lower() == "random":
            difficulty = random.choice(("easy", "medium", "hard"))
            diffR = True

        difficulty = difficulty.lower()
        if difficulty == "e":
            difficulty = "easy"
        elif difficulty == "m":
            difficulty = "medium"
        elif difficulty == "h":
            difficulty = "hard"

        if not category or category.lower() == "r" or category.lower() == "random":
            category = random.randint(9, 32)
            catR = True
        else:
            try:
                category = self.categories[category.lower()]
            except KeyError:
                return await send_embed(ctx, "Invalid category.", negative=True)

        try:
            q = await self.trivia.get_specific_question(type=type, difficulty=difficulty, category=category)
            q = q[0]
        except aiotrivia.ResponseError as e:
            if typeR and catR and diffR:
                while True:
                    try:
                        q = await self.trivia.get_random_question(difficulty=random.choice(("easy", "medium", "hard")))
                        break
                    except aiotrivia.ResponseError:
                        continue
            else:
                return await send_embed(ctx, str(e), negative=True)
        except aiotrivia.AiotriviaException as e:
            return await send_embed(ctx, str(e), negative=True)

        answers = q.responses
        random.shuffle(answers)

        embed = discord.Embed(
            colour=discord.Colour.orange(),
            description=f"Category: ``{q.category}`` • Difficulty: ``{q.difficulty.capitalize()}``"
        )

        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        if len(answers) == 4:
            embed.title = q.question

            answers = {
                "A": answers[0],
                "B": answers[1],
                "C": answers[2],
                "D": answers[3]
            }

            for i, v in answers.items():
                embed.add_field(name=i, value=v, inline=False)

        else:
            embed.title = f"True or False question:\n" \
                          f"{q.question}"

        if isinstance(answers, dict):
            for i, v in answers.items():
                if v == q.answer:
                    answer = i.lower()
                    break
        else:
            answer = q.answer.lower()

        await ctx.send(embed=embed)

        try:
            msg = await self.bot.wait_for("message", check=lambda msg: msg.channel == ctx.channel
                                          and msg.author == ctx.author, timeout=120.0)
        except asyncio.TimeoutError:
            return await send_embed(ctx, f"Correct answer was **{answer}**", negative=True)

        resp = msg.content.lower()

        if resp == "yes" or resp == "y" or resp == "t":
            resp = "true"
        elif resp == "no" or resp == "n" or resp == "f":
            resp = "false"
        elif resp == "1":
            resp = "a"
        elif resp == "2":
            resp = "b"
        elif resp == "3":
            resp = "c"
        elif resp == "4":
            resp = "d"

        if resp != answer:
            await send_embed(ctx, f"Correct answer was **{answer.capitalize()}**.", negative=True)
        else:
            await send_embed(ctx, "Answer is correct.")

        if typeR and diffR and catR:
            cursor = await db.execute("Select count(*) from TriviaTop where GuildID = ? and MemberID = ?",
                                      (ctx.guild.id, ctx.author.id))
            result = await cursor.fetchone()
            result = result[0]

            if resp == answer:
                if result:
                    await db.execute("Update TriviaTop set Correct = Correct + 1, Total = Total + 1, "
                                     "Score = (Correct + 1) * (Correct + 1) / (Total + 1) "
                                     "where GuildID = ? and MemberID = ?", (ctx.guild.id, ctx.author.id))
                    await db.commit()
                else:
                    await db.execute("Insert into TriviaTop values (?, ?, ?, ?, ?)",
                                     (ctx.guild.id, ctx.author.id, 1, 1, 1))
                    await db.commit()

            else:
                if result:
                    await db.execute("Update TriviaTop set Total = Total + 1, Score = Correct * Correct / (Total + 1) "
                                     "where GuildID = ? and MemberID = ?", (ctx.guild.id, ctx.author.id))
                    await db.commit()
                else:
                    await db.execute("Insert into TriviaTop values (?, ?, ?, ?, ?)",
                                     (ctx.guild.id, ctx.author.id, 0, 1, 0))
                    await db.commit()

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @trivia.command()
    async def categories(self, ctx):
        """Get the possible categories."""

        string = [f"``{i}``" for i in self.categories.keys()]
        await send_embed(ctx, "\n".join(string), info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @trivia.command(aliases=["top"])
    @commands.guild_only()
    async def leaderboard(self, ctx):
        """Get the leaderboard. This is guild only."""

        cursor = await db.execute("Select MemberID, Correct, Total, Score from TriviaTop where GuildID = ? "
                                  "order by Score desc limit 10", (ctx.guild.id,))
        result = await cursor.fetchall()

        for i, tup in enumerate(result):
            result[i] = list(result[i])
            id = result[i][0]
            member = ctx.guild.get_member(id) or await self.bot.fetch_user(id)
            if not member:
                result[i][0] = "Account Deleted"
                await db.execute("Delete from TriviaTop where MemberID = ?", (id,))
                await db.commit()
            else:
                result[i][0] = member.mention

        for i, tup in enumerate(result, start=1):
            if i == 1:
                a = "🥇"
            elif i == 2:
                a = "🥈"
            elif i == 3:
                a = "🥉"
            else:
                a = i

            s = tup[3]

            if isinstance(s, float):
                if s == int(s):
                    s = int(s)
                else:
                    s = round(s, 2)

            result[i-1] = f"{a}: {tup[0]} • Score: {s} ({int(tup[1])}/{int(tup[2])} correct)"

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Trivia Leaderboard",
            description="\n".join(result)
        )

        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
        embed.set_footer(text="If you see an 'Account Deleted' on the leaderboard, it has been deleted in the DB and "
                              "will not show up the next time you call this command.")

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @trivia.command()
    @commands.guild_only()
    async def stats(self, ctx, member: discord.Member = None):
        """Get stats of yourself or another member."""

        if not member:
            member = ctx.author

        cursor = await db.execute("Select Correct, Total, Score from TriviaTop where GuildID = ? and MemberID = ?",
                                  (ctx.guild.id, member.id))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Member has no stats in this server for trivia.", negative=True)

        s = int(result[2]) if int(result[2]) == result[2] else round(result[2], 2)

        embed = discord.Embed(
            description=f"Score: {s} ({int(result[0])}/{int(result[1])} correct)",
            colour=discord.Colour.blue()
        )

        embed.set_author(name=str(member), icon_url=str(member.avatar_url))

        await ctx.send(embed=embed)
