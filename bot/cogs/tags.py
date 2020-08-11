from datetime import datetime

import discord
from discord.ext import commands

from bot.utils.format import send_embed


def can_change(ctx, memberID):
    member = ctx.guild.get_member(memberID)

    if ctx.author == ctx.guild.owner or ctx.author == member:
        return True
    if member == ctx.guild.owner:
        return False

    if not ctx.author.guild_permissions.administrator:
        return False
    if not member.guild_permissions.administrator:
        return True

    if member:
        for i in reversed(member.roles):
            if i.permissions.administrator:
                a = i.position
        for i in reversed(ctx.author.roles):
            if i.permissions.administrator:
                b = i.position

        return b > a


class Tags(commands.Cog, name="Tags"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def tag(self, ctx, *, tag: str):
        """Get a tag."""

        tag = tag.lower()

        cursor = await db.execute("Select TagContent from Tags where GuildID = ? and Tag = ?",
                                  (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist", negative=True)

        await db.execute("Update Tags set Uses = Uses + 1 where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        await db.commit()

        await ctx.send(discord.utils.escape_mentions(result[0]))

        cursor = await db.execute("Select count(*) from TagUsage where GuildID = ? and MemberID = ?",
                                  (ctx.guild.id, ctx.author.id))
        result = await cursor.fetchone()

        if not result[0]:
            await db.execute("Insert into TagUsage values (?, ?, ?)", (ctx.guild.id, ctx.author.id, 1))
            await db.commit()

        else:
            await db.execute("Update TagUsage set Uses = Uses + 1 where GuildID = ? and MemberID = ?",
                             (ctx.guild.id, ctx.author.id))
            await db.commit()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def create(self, ctx, tag: str, *, content: str):
        """Create a tag."""

        tag = tag.lower()

        cursor = await db.execute("Select count(*) from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if result[0]:
            return await send_embed(ctx, "Tag already exists.", negative=True)

        cursor = await db.execute("Select count(*) from Tags where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        await db.execute("Insert into Tags values (?, ?, ?, ?, ?, ?, ?)",
                         (ctx.guild.id, ctx.author.id, content, tag, 0, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                          result[0] + 1))
        await db.commit()

        await send_embed(ctx, f"Created tag with name ``{tag}``.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def edit(self, ctx, tag: str, *, content: str):
        """Edit one of your tags."""

        tag = tag.lower()

        cursor = await db.execute("Select MemberID from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist.", negative=True)

        if result[0] != ctx.author.id and not can_change(ctx, result[0]):
            return await send_embed(ctx, "You do not have permission to edit this tag.", negative=True)

        await db.execute("Update Tags set TagContent = ? where GuildID = ? and Tag = ?", (content, ctx.guild.id, tag))
        await db.commit()

        await send_embed(ctx, "Edited tag.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def info(self, ctx, *, tag: str):
        """Get info on a tag."""

        tag = tag.lower()

        cursor = await db.execute("Select MemberID, Uses, TimeCreated, rank() over (order by Uses desc) from Tags "
                                  "where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist.", negative=True)

        embed = discord.Embed(
            title=tag,
            colour=discord.Colour.blue()
        )

        author = ctx.guild.get_member(result[0]) or await self.bot.fetch_user(result[0])

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

        tag = tag.lower()

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

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def list(self, ctx, member: discord.Member = None):
        """Get list of tags created by a member. Defaults to yourself."""

        if not member:
            member = ctx.author

        cursor = await db.execute("Select Tag, ID from Tags where GuildID = ? and MemberID = ? order by ID asc",
                                  (ctx.guild.id, member.id,))
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

        if not embeds:
            return await send_embed(ctx, "Target member has no tags.", negative=True)

        await self.bot.paginate(ctx, embeds)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def raw(self, ctx, *, tag: str):
        """Get raw content of a tag."""

        tag = tag.lower()

        cursor = await db.execute("Select TagContent from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist", negative=True)

        await send_embed(ctx, discord.utils.escape_markdown(result[0]), info=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def search(self, ctx, *, tag: str):
        """Search for a tag given a tag substring."""

        tag = tag.lower()

        statement = "Select Tag, ID from Tags where GuildID = ? and Tag like '%' || ? || '%' limit 20"

        cursor = await db.execute(statement, (ctx.guild.id, tag))
        result = await cursor.fetchall()

        if not result:
            return await send_embed(ctx, "Tag with requested substring does not exist.", negative=True)

        embeds = []
        description = []
        for index, lst in enumerate(result, start=1):
            description.append(f"{index}. {lst[0]} (ID: {lst[1]})")
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
    @tag.command()
    @commands.guild_only()
    async def delete(self, ctx, *, tag: str):
        """Delete a tag."""

        tag = tag.lower()

        cursor = await db.execute("Select MemberID from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Tag does not exist.", negative=True)

        if result[0] != ctx.author.id and not can_change(ctx, result[0]):
            return await send_embed(ctx, "You do not have permission to delete that tag.", negative=True)

        await db.execute("Delete from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        await db.commit()

        await send_embed(ctx, "Deleted tag.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @tag.command()
    @commands.guild_only()
    async def stats(self, ctx, member: discord.Member = None):
        if not member:
            cursor = await db.execute("Select count(Tag), sum(Uses) from Tags where GuildID = ?", (ctx.guild.id,))
            result = await cursor.fetchone()

            embed = discord.Embed(
                colour=discord.Colour.blue(),
                title="Tag Stats",
                description=f"{result[0]} tags, {result[1]} uses"
            )

            cursor = await db.execute("Select Tag, Uses from Tags where GuildID = ? order by Uses desc limit 3",
                                      (ctx.guild.id,))
            result = await cursor.fetchall()

            for i in range(0, 3):
                try:
                    a = result[i]  # Basically checking if it exists
                except:
                    if i >= len(result):
                        result.append(("[No tag here]", "No"))
                    else:
                        result[i] = ("[No tag here]", "No")

            value = f"🥇: {result[0][0]} ({result[0][1]} uses)\n" \
                    f"🥈: {result[1][0]} ({result[1][1]} uses)\n" \
                    f"🥉: {result[2][0]} ({result[2][1]} uses)"

            embed.add_field(name="Top Tags", value=value, inline=False)

            cursor = await db.execute(
                "Select MemberID, Uses from TagUsage where GuildID = ? order by Uses desc limit 3",
                (ctx.guild.id,))
            result = await cursor.fetchall()

            for i in range(0, 3):
                try:
                    result[i] = list(result[i])
                    result[i][0] = ctx.guild.get_member(result[i][0]).mention
                except:
                    if i >= len(result):
                        result.append(("No member here", 0))
                    else:
                        result[i] = ("No member here", 0)

            value = f"🥇: {result[0][0]} ({result[0][1]} times)\n" \
                    f"🥈: {result[1][0]} ({result[1][1]} times)\n" \
                    f"🥉: {result[2][0]} ({result[2][1]} times)"

            embed.add_field(name="Top Tag Users", value=value, inline=False)

            cursor = await db.execute("Select MemberID, count(*) from Tags group by MemberID order by count(*) desc "
                                      "limit 3")
            result = await cursor.fetchall()

            for i in range(0, 3):
                try:
                    result[i] = list(result[i])
                    result[i][0] = ctx.guild.get_member(result[i][0]).mention
                except:
                    if i >= len(result):
                        result.append(("No member here", 0))
                    else:
                        result[i] = ("No member here", 0)

            value = f"🥇: {result[0][0]} ({result[0][1]} tags)\n" \
                    f"🥈: {result[1][0]} ({result[1][1]} tags)\n" \
                    f"🥉: {result[2][0]} ({result[2][1]} tags)"

            embed.add_field(name="Top Tag Creators", value=value, inline=False)

            embed.set_footer(text="These statistics are for this server only.")

            await ctx.send(embed=embed)

        else:
            embed = discord.Embed(
                colour=discord.Colour.blue()
            )
            embed.set_author(name=str(member), icon_url=str(member.avatar_url))

            cursor = await db.execute("Select count(*), sum(Uses) from Tags where GuildID = ? and MemberID = ?",
                                      (ctx.guild.id, member.id))
            result = await cursor.fetchone()
            result = list(result)

            for i in range(0, 2):
                try:
                    result[i] = str(result[i])
                except:
                    if i >= len(result):
                        result.append("0")
                    else:
                        result[i] = "0"

            embed.add_field(name="Owned Tags", value=result[0])
            embed.add_field(name="Owned Tag Uses", value=result[1])

            cursor = await db.execute("Select Uses from TagUsage where GuildID = ? and MemberID = ?",
                                      (ctx.guild.id, member.id))
            result = await cursor.fetchone()

            if not result:
                embed.add_field(name="Tag Command Uses", value="0")

            else:
                embed.add_field(name="Tag Command Uses", value=result[0])

            cursor = await db.execute("Select Tag, Uses from Tags where GuildID = ? and MemberID = ? "
                                      "order by Uses desc limit 3", (ctx.guild.id, member.id))
            result = await cursor.fetchall()

            for i in range(0, 3):
                try:
                    a = result[i]
                except:
                    if i >= len(result):
                        result.append("Nothing", "0")
                    else:
                        result[i] = ("Nothing", 0)

            embed.add_field(name="🥇 Owned Tag", value=f"{result[0][0]} ({result[0][1]} uses)")
            embed.add_field(name="🥈 Owned Tag", value=f"{result[1][0]} ({result[1][1]} uses)")
            embed.add_field(name="🥉 Owned Tag", value=f"{result[2][0]} ({result[2][1]} uses)")

            embed.set_footer(text="These statistics are for this server only.")

            await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.guild)
    @tag.command(aliases=["toptag"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def toprotectedtag(self, ctx, *, tag: str):
        """Convert a tag to protected tag."""

        tag = tag.lower()

        cursor = await db.execute("Select TagContent from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "That tag does not exist.", negative=True)

        cursor = await db.execute("Select count(*) from ProtectedTags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if result[0]:
            return await send_embed(ctx, "ProtectedTag already exists", negative=True)

        if ctx.author == ctx.guild.owner:
            can_create = False
            for i in reversed(ctx.author.roles):
                if i.permissions.administrator:
                    can_create = True
                    break

            if not can_create:
                return await send_embed(ctx,
                                        "You cannot create a protectedtag even though you are the owner because you "
                                        "do not share any administrator roles. You may as well create notes for "
                                        "yourself.", negative=True)

        cmd = self.bot.get_command("protectedtag create")
        await ctx.invoke(cmd, tag=tag, content=result[0])

        cmd = self.bot.get_command("tag delete")
        await ctx.invoke(cmd, tag=tag)

        await send_embed(ctx, "Tag converted to Protected Tag.")

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.guild)
    @tag.command(aliases=["moveptag"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def moveprotectedtag(self, ctx, *, tag: str):
        """Convert a tag to protected tag without deleting the original tag."""

        tag = tag.lower()

        cursor = await db.execute("Select TagContent from Tags where GuildID = ? and Tag = ?", (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "That tag does not exist.", negative=True)

        cursor = await db.execute("Select count(*) from ProtectedTags where GuildID = ? and Tag = ?",
                                  (ctx.guild.id, tag))
        result = await cursor.fetchone()

        if result[0]:
            return await send_embed(ctx, "ProtectedTag already exists", negative=True)

        if ctx.author == ctx.guild.owner:
            can_create = False
            for i in reversed(ctx.author.roles):
                if i.permissions.administrator:
                    can_create = True
                    break

            if not can_create:
                return await send_embed(ctx,
                                        "You cannot create a protectedtag even though you are the owner because you "
                                        "do not share any administrator roles. You may as well create notes for "
                                        "yourself.", negative=True)

        cmd = self.bot.get_command("protectedtag create")
        await ctx.invoke(cmd, tag=tag, content=result[0])

        await send_embed(ctx, "Tag moved to Protected Tag.")
