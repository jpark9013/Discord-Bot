import asyncio
import random

import aiotrivia
import discord
from discord.ext import commands

from bot.utils.message import send_embed


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

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True, aliases=["quiz"])
    async def trivia(self, ctx, type=None, difficulty=None, *, category=None):
        """Get a trivia question. Possible types are ``multiple`` or ``true/false``. Possible levels of difficulty are
        ``easy``, ``medium``, and ``hard``. Do ``categories`` for the full list of categories."""

        if not type or type.lower() == "r" or type.lower() == "random":
            type = random.choice(("multiple", "boolean"))
        type = type.lower()
        if type == "true/false" or type == "t/f" or type == "tf" or type == "true false":
            type = "boolean"
        elif type == "m":
            type = "multiple"

        if not difficulty or difficulty.lower() == "r" or difficulty.lower() == "random":
            difficulty = random.choice(("easy", "medium", "hard"))

        difficulty = difficulty.lower()
        if difficulty == "e":
            difficulty = "easy"
        elif difficulty == "m":
            difficulty = "medium"
        elif difficulty == "h":
            difficulty = "hard"

        if not category:
            category = random.randint(9, 32)
        else:
            try:
                category = self.categories[category.lower()]
            except KeyError:
                return await send_embed(ctx, "Invalid category.", negative=True)

        try:
            q = await self.trivia.get_specific_question(type=type, difficulty=difficulty, category=category)
            q = q[0]
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
            msg = await self.bot.wait_for("message", check=lambda msg: msg.channel == ctx.channel, timeout=120.0)
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

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @trivia.command()
    async def categories(self, ctx):
        """Get the possible categories."""

        string = [f"``{i}``" for i in self.categories.keys()]
        await send_embed(ctx, "\n".join(string), info=True)
