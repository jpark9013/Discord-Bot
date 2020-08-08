import discord
from discord.ext import commands

from bot.utils.format import send_embed


class Notes(commands.Cog, name="Notes"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def notes(self, ctx):
        """Access your notes list."""

        cursor = await db.execute("Select Note from Notes where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchall()

        if not result:
            return await send_embed(ctx, "You do not have anything on your note list.", negative=True)

        result = [i[0] for i in result]

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

        await self.bot.paginate(ctx, embeds)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @notes.command(aliases=["add"])
    async def create(self, ctx, *, string: str):
        """Create a note."""

        await db.execute("Insert into Notes values (?, ?, (select count(*) from Notes where MemberID = ?) + 1)",
                         (ctx.author.id, string, ctx.author.id))
        await db.commit()

        await send_embed(ctx, "Created new note.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @notes.command(aliases=["remove"])
    async def delete(self, ctx, ID: int):
        """Remove a note based on its ID."""

        cursor = await db.execute("Select count(*) from Notes where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "You do not have any to-do's to delete.", negative=True)

        if ID < 1 or ID > result[0]:
            return await send_embed(ctx, "Invalid ID to delete.", negative=True)

        await db.execute("Delete from Notes where MemberID = ? and ID = ?", (ctx.author.id, ID))
        await db.commit()

        await send_embed(ctx, "Note deleted.")

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @notes.command()
    async def clear(self, ctx):
        """Clear your note list."""

        cursor = await db.execute("Select count(*) from Notes where MemberID = ?", (ctx.author.id,))
        result = await cursor.fetchone()

        if not result[0]:
            return await send_embed(ctx, "You do not have any notes.", negative=True)

        await db.execute("Delete from Notes where MemberID = ?", (ctx.author.id,))
        await db.commit()

        await send_embed(ctx, "All notes cleared.")
