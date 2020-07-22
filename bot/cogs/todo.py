import json

import discord
from discord.ext import commands

from bot.utils.message import send_embed


class Todo(commands.Cog, name="To do"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def todo(self, ctx):
        """Access your to-do list."""

        cursor = await db.execute("Select TodoList from Todo where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchone()

        result = json.loads(result[0])

        if not result:
            return await send_embed(ctx, "You do not have anything on your to-do list.", negative=True)

        embeds = []
        description = []

        for index, string in enumerate(result, start=1):

            description.append(f"{index}. {string}")

            if index % 10 == 0 or index == len(result):
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    description="\n".join(description)
                )
                embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                embeds.append(embed)
                description = []

        await self.bot.paginate(embeds)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @todo.command(aliases=["add"])
    async def create(self, ctx, *, string: str):
        """Create a to-do."""

        cursor = await db.execute("Select TodoList from Todo where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchone()

        if result:
            result = json.loads(result[0])
            result.append(string)
            await db.execute("Update Todo set TodoList = ? where MemberID = ?", (json.dumps(result), ctx.author.id))
            await db.commit()

        else:
            await db.execute("Insert into Todo values (?, ?)", (ctx.author.id, json.dumps([string])))
            await db.commit()

        await send_embed(ctx, "Created new to-do task.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @todo.command(aliases=["remove"])
    async def delete(self, ctx, index: int):
        """Remove a to-do based on its index."""

        cursor = await db.execute("Select TodoList from Todo where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "You do not have any to-do's to delete.", negative=True)

        result = json.loads(result)

        if index > len(result) or index < 1:
            return await send_embed(ctx, "Invalid index to delete.", negative=True)

        del result[index-1]
        await db.execute("Update Todo set TodoList = ? where MemberID = ?", (json.dumps(result), ctx.author.id))
        await db.commit()

        await send_embed(ctx, "To-do deleted.")
