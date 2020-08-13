import math
import numpy as np

import discord
from discord.ext import commands

from bot.utils.format import send_embed


class Math(commands.Cog, name="Math"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def add(self, ctx, numbers: commands.Greedy[float]):
        """Add up to 100 numbers at one point. Maximum amount of digits they can have is 10."""

        if len(numbers) > 100:
            return await send_embed(ctx, "Too many numbers to add.", negative=True)

        for i, v in enumerate(numbers):
            if len(str(v)) > 10:
                return await send_embed(ctx, "One or more numbers contain too many digits (limit is 10).",
                                        negative=True)

        return await send_embed(ctx, sum(numbers), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def subtract(self, ctx, number1: float, number2: float):
        """Subtract two numbers. number1 - number2"""

        return await send_embed(ctx, number1 - number2, info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["avg"])
    async def average(self, ctx, numbers: commands.Greedy[float]):
        """Take the average of up to 100 numbers. Maximum amount of digits they can have is 10."""

        if len(numbers) > 100:
            return await send_embed(ctx, "Too many numbers to add.", negative=True)

        for i, v in enumerate(numbers):
            if len(str(v)) > 10:
                return await send_embed(ctx, "One or more numbers contain too many digits (limit is 10).",
                                        negative=True)

        return await send_embed(ctx, sum(numbers) / 100, info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["exponent"])
    async def exp(self, ctx, number1: float, number2: float):
        """Take the exponent of two numbers. number1 ^ number2"""

        if number1 < 0:
            return await send_embed(ctx, "Due to technical limitations, python cannot do exponents of negative numbers."
                                    , negative=True)

        if number1 > 10 ** 10 or number2 > 10 ** 10:
            return await send_embed(ctx, "Numbers too large to do calculations on.", negative=True)

        return await send_embed(ctx, number1 ** number2, info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["square root", "root"])
    async def sqrt(self, ctx, number: float):
        """Take the square root of a number."""

        return await send_embed(ctx, math.sqrt(number), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["cosine"])
    async def cos(self, ctx, number: float, radians: bool = True):
        """Take the cosine of a number. Can be radians or degrees."""

        if not radians:
            number = number * math.pi / 180

        return await send_embed(ctx, math.cos(number), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def divide(self, ctx, number1: float, number2: float):
        """Divide two numbers. number1 / number2"""

        if number1 > 10**20 or number2 > 10**20:
            return await send_embed(ctx, "Numbers too large.", negative=True)

        return await send_embed(ctx, number1/number2, info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["fac"])
    async def factorial(self, ctx, number: int):
        """Get the factorial of a number that is 0 or greater and less than 21."""

        if number < 0 or number > 20:
            return await send_embed(ctx, "Invalid integer to give.", negative=True)

        if number == 0 or number == 1:
            return await send_embed(ctx, 1, info=True)

        await send_embed(ctx, math.factorial(number), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["sine"])
    async def sin(self, ctx, number: float, radians: bool = True):
        """Get the sin of radians/degrees."""

        if not radians:
            number = number * math.pi / 180

        return await send_embed(ctx, math.sin(number), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["tangent"])
    async def tan(self, ctx, number: float, radians: bool = True):
        """Get the tan of radians/degrees."""

        if not radians:
            number = number * math.pi / 180

        return await send_embed(ctx, math.tan(number), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(aliases=["combination", "comb"])
    async def combo(self, ctx, num1: int, num2: int):
        """Compute the combination of two numbers nCr. n = num1, r = num2"""

        if num1 > 1000000 or num2 > 1000000:
            return await send_embed(ctx, "Number(s) too high to compute.", negative=True)

        await send_embed(ctx, math.comb(num1, num2), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def logarithm(self, ctx, value: float, base: float = 10):
        """Get the log."""

        if value > 10**10 or abs(base) < 0.1:
            return await send_embed(ctx, "Number too high to compute.", negative=True)

        await send_embed(ctx, math.log(value, base), info=True)
