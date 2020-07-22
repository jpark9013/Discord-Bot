from datetime import datetime

import discord
from discord.ext import commands

from bot.utils.message import send_embed


class Tags(commands.Cog, name="Tags"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def tag(self, ctx, *, tag: str):
        """Get a tag."""

        cursor = await db.execute("Select TagContent from Tags where GuildID = ? and Tag = ?",
                                  (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result[0]:
            return await send_embed(ctx, "Tag does not exist", negative=True)

        await db.execute("Update TagContent set Uses = Uses + 1 where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        await db.commit()

        await send_embed(ctx, result[0], info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def create(self, ctx, tag: str, *, content: str):
        """Create a tag."""

        cursor = await db.execute("Select count(*) from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if result[0]:
            return await send_embed(ctx, "Tag already exists.", negative=True)

        cursor = await db.execute("Select count(*) from Tags where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        await db.execute("Insert into Tags values (?, ?, ?, ?, ?, ?, ?)",
                         (ctx.guild.id, ctx.author.id, content, tag, 0, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                          result[0]+1))
        await db.commit()

        await send_embed(ctx, f"Created tag with name ``{tag}``.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def edit(self, ctx, tag: str, *, content: str):
        """Edit one of your tags."""

        cursor = await db.execute("Select MemberID from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist.", negative=True)

        if result[0] != ctx.author.id:
            return await send_embed(ctx, "You do not own this tag.", negative=True)

        await db.execute("Update Tags set TagContent = ? where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        await db.commit()

        await send_embed(ctx, "Edited tag.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def info(self, ctx, *, tag: str):
        """Get info on a tag."""

        cursor = await db.execute("Select MemberID, Uses, TimeCreated, rank() over (order by Uses desc) from Tags "
                                  "where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist.", negative=True)

        embed = discord.Embed(
            title=tag,
            colour=discord.Colour.blue()
        )

        author = ctx.guild.get_member(result[0]) or await self.bot.fetch_member(result[0])

        embed.set_author(name=str(author), icon_url=str(author.avatar_url))
        embed.set_footer(text=f"Tag created at {result[2]}")

        embed.add_field(name="Owner", value=author.mention)
        embed.add_field(name="Uses", value=str(result[1]))
        embed.add_field(name="Rank", value=str(result[3]))

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def claim(self, ctx, *, tag: str):
        """Claim a tag if the member has left the server or deleted their account."""

        cursor = await db.execute("Select MemberID from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist.", negative=True)

        if ctx.guild.get_member(result[0]):
            return await send_embed(ctx, "Owner of tag is still in the server", negative=True)

        await db.execute("Update Tags set MemberID = ? where GuildID = ? and Tag = ?",
                         (ctx.author.id, ctx.guild.id, tag))
        await db.commit()

        await send_embed(ctx, "Transferred tag ownership.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def list(self, ctx, member: discord.Member = None):
        """Get list of tags created by a member. Defaults to yourself."""

        if not member:
            member = ctx.author

        cursor = await db.execute("Select Tag, ID from Tags where MemberID = ?", (member.id,))
        result = await cursor.fetchall()

        embeds = []
        description = []
        for index, lst in enumerate(result, start=1):
            description.append(f"{index}. {lst[0]} (ID: {lst[1]})")
            if index % 10 == 0 or index == len(result):
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    description="\n".join(description)
                )
                embed.set_author(name=str(member), icon_url=str(member.avatar_url))
                embeds.append(embed)
                description = []

        await self.bot.paginate(embeds)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def raw(self, ctx, *, tag: str):
        """Get raw content of a tag."""

        cursor = await db.execute("Select TagContent from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist", negative=True)

        await send_embed(ctx, discord.utils.escape_markdown(result[0]), info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def search(self, ctx, *, content: str):
        """Search for a tag based on its content."""

        cursor = await db.execute("Select Tag, ID from Tags where GuildID = ? and TagContent = ?",
                                  (ctx.guild.id, content))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag with requested content does not exist.", negative=True)

        embeds = []
        description = []
        for index, lst in enumerate(result, start=1):
            description.append(f"{index}. {lst[0]} (ID: {lst[1]})")
            if index % 10 == 0:
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    description="\n".join(description)
                )
                embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                embeds.append(embed)
                description = []

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def delete(self, ctx, *, tag: str):
        """Delete a tag you own."""

        cursor = await db.execute("Select MemberID from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist.", negative=True)

        if result[0] != ctx.author.id:
            return await send_embed(ctx, "You are not the owner of the tag.", negative=True)

        await db.execute("Delete from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        await db.commit()

        await send_embed(ctx, "Deleted tag.")
