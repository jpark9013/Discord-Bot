import asyncio
import random
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot.utils.format import send_embed, to_datetime


def custom_datetime(seconds):
    w, remainder = divmod(seconds, 604800)
    d, remainder = divmod(remainder, 86400)
    h, remainder = divmod(remainder, 3600)
    m, s = divmod(remainder, 60)

    w = int(w)
    d = int(d)
    h = int(h)
    m = int(m)
    s = int(s)

    string = ["Time remaining:"]

    if w:
        string.append(f"{w} weeks")
    if d:
        string.append(f"{d} days")
    if h:
        string.append(f"{h} hours")
    if m:
        string.append(f"{m} minutes")

    if w or d or h or m:
        string.append(f"and {s} seconds")
    else:
        string.append(f"{s} seconds")

    if len(string) > 3:
        string = ", ".join(string)
    else:
        string = " ".join(string)

    return string


class Giveaway(commands.Cog, name="Giveaway"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.giveitaway.start()
        self.longer_loop.start()

    @commands.group(aliases=["g"])
    @commands.guild_only()
    async def giveaway(self, ctx):
        """Base giveaway command."""
        pass

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @giveaway.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True)
    async def create(self, ctx, channel: discord.TextChannel, minutes: float, members: int, *, prize: str):
        """Create a giveaway."""

        seconds = minutes * 60

        if seconds < 30 or seconds > 31536000:
            return await send_embed(ctx, "Invalid number of minutes for the giveaway.", negative=True)

        if members < 0 or members > 20:
            return await send_embed(ctx, "Invalid number of members to giveaway to.", negative=True)

        end = int(time.time()) + seconds

        cursor = await db.execute("Select count(*) from Giveaway where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result[0] >= 20:
            return await send_embed(ctx, "Maximum of 20 giveaways in the server.", negative=True)

        embed = discord.Embed(
            description=f"React with <:tada:740055373926367383> to enter!\n"
                        f"{custom_datetime(seconds)}\n"
                        f"Hosted by: {ctx.author.mention}",
            colour=discord.Colour.green()
        )

        embed.set_author(name=prize)

        embed.set_footer(text=f"Ends at • {datetime.utcfromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S')}")

        msg = await channel.send("<:tada:740055373926367383> **GIVEAWAY** <:tada:740055373926367383>", embed=embed)
        await msg.add_reaction("<:tada:740055373926367383>")

        await db.execute("Insert into Giveaway values (?, ?, ?, ?, ?, ?)",
                         (msg.id, ctx.guild.id, end, members, False, channel.id))
        await db.commit()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @giveaway.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def end(self, ctx, message: discord.Message):
        """End a giveaway. Give message ID as the parameter."""

        if message.guild != ctx.guild:
            return await send_embed(ctx, "You do not have permission to do that.", negative=True)

        embed = message.embeds[0]
        host = embed.description.split('\n')
        host = host[2]

        async def _end(description: str):
            new_embed = discord.Embed(
                colour=discord.Colour.dark_grey(),
                description=description
            )

            new_embed.set_author(name=embed.author.name)

            new_embed.set_footer(text=f"Ended at • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            await message.edit(text="<:tada:740055373926367383> **GIVEAWAY ENDED** <:tada:740055373926367383>",
                               embed=new_embed)

            await db.execute("Update Giveaway set Ended = ? where MessageID = ?", (True, message.id,))
            await db.commit()

        cursor = await db.execute("Select Members, Ended from Giveaway where MessageID = ? and GuildID = ?",
                                  (message.id, ctx.guild.id))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Giveaway with given message ID does not exist.", negative=True)

        if result[1]:
            return await send_embed(ctx, "Giveaway has already ended.", negative=True)

        for reaction in message.reactions:
            if str(reaction) == "<:tada:740055373926367383>":
                thisreaction = reaction

        try:
            a = thisreaction
        except:
            await _end(f"Could not determine winner!\n{host}")

        members = [i for i in await thisreaction.users().flatten() if not i.bot and i in ctx.guild.members]
        winners = []

        if not members:
            return await _end(f"Could not determine winner!\n{host}")

        for i in range(result[0]):
            if not members:
                break
            member = random.choice(members)
            winners.append(member)
            members.remove(member)

        if len(winners) == 1:
            await _end(f"Winner: {winners[0].mention}\n{host}")
            await ctx.send(f"Congratulations {winners[0].mention}! You won the **{embed.author.name}**!\n"
                           f"{message.jump_url}")

        else:
            await _end(f"Winners: {', '.join([i.mention for i in winners])}\n{host}")
            await ctx.send(f"Congratulations {', '.join([i.mention for i in winners[:-1]])}, "
                           f"and {winners[-1].mention}! You won the **{embed.author.name}**!\n"
                           f"{message.jump_url}")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @giveaway.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def reroll(self, ctx, message: discord.Message):
        """Reroll a giveaway."""

        if message.guild != ctx.guild:
            return await send_embed(ctx, "You do not have permission to do that.", negative=True)

        cursor = await db.execute("Select Members, Ended from Giveaway where MessageID = ? and GuildID = ?",
                                  (message.id, ctx.guild.id))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Giveaway could not be found.", negative=True)

        if not result[1]:
            return await send_embed(ctx, "Giveaway has not ended yet.", negative=True)

        for reaction in message.reactions:
            if str(reaction) == "<:tada:740055373926367383>":
                thisreaction = reaction

        try:
            a = thisreaction
        except:
            return await send_embed(ctx,
                                    f"Could not determine new winner for giveaway with message ID **{message.id}**.",
                                    negative=True)

        members = [i for i in await thisreaction.users().flatten() if not i.bot and i in ctx.guild.members]
        winners = []

        if not members:
            return await send_embed(ctx,
                                    f"Could not determine new winner for giveaway with message ID **{message.id}**.",
                                    negative=True)

        for i in range(result[0]):
            if not members:
                break
            member = random.choice(members)
            winners.append(member)
            members.remove(member)

        if len(winners) == 1:
            return await ctx.send(f"<:tada:740055373926367383> The new winner is {winners[0].mention}! "
                                  f"Congratulations! {message.jump_url}")

        return await ctx.send(f"The new winners are {', '.join([i.mention for i in winners[:-1]])}, "
                              f"and {winners[-1].mention}! Congratulations! {message.jump_url}")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @giveaway.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def list(self, ctx):
        """Lists all active giveaways on the server."""

        cursor = await db.execute("Select MessageID, TimeEnding, Members, ChannelID from Giveaway "
                                  "where GuildID = ? and Ended = ?", (ctx.guild.id, False))
        result = await cursor.fetchall()

        for i, tup in enumerate(result):
            try:
                msg = await ctx.guild.get_channel(tup[3]).fetch_message(tup[0])
                tup = list(tup)
                tup[0] = msg
                result[i] = tup
            except:
                result.remove(tup)
                await db.execute("Delete from Giveaway where MessageID = ?", (tup[0],))
                await db.commit()

        if not result:
            return await send_embed(ctx, "No active giveaways on this server.", negative=True)

        embeds = []
        fields = []

        for i, tup in enumerate(result, start=1):
            fields.append((str(tup[0].id),
                           f"Prize: {tup[0].embeds[0].author.name}\n"
                           f"{tup[2]} possible winners\n"
                           f"Ends at {datetime.utcfromtimestamp(tup[1]).strftime('%Y-%m-%d %H:%M:%S')}"))

            if i % 10 == 0 or i == len(result):
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title="Active Giveaways"
                )

                for field in fields:
                    embed.add_field(name=field[0], value=field[1], inline=False)

                embeds.append(embed)
                fields = []

        await self.bot.paginate(ctx, embeds)

    @tasks.loop(seconds=15)
    async def giveitaway(self):
        cursor = await db.execute("Select MessageID, GuildID, ChannelID from Giveaway where TimeEnding <= ? + 3 "
                                  "and Ended = ?", (time.time(), False))
        result = await cursor.fetchall()

        for tup in result:
            try:
                msg = await self.bot.get_guild(tup[1]).get_channel(tup[2]).fetch_message(tup[0])
            except:
                await db.execute("Delete from Giveaway where MessageID = ?", (tup[0],))
                await db.commit()
                result.remove(tup)
                continue

            ctx = await self.bot.get_context(msg)
            cmd = self.bot.get_command("giveaway end")
            try:
                await cmd(ctx, msg)
            except discord.Forbidden:
                pass

    @tasks.loop(seconds=60)
    async def longer_loop(self):
        current_time = time.time()

        cursor = await db.execute("Select MessageID, GuildID, ChannelID, TimeEnding from Giveaway where Ended = ? "
                                  "and TimeEnding > ? + 30", (False, current_time))
        result = await cursor.fetchall()

        for tup in result:
            try:
                msg = await self.bot.get_guild(tup[1]).get_channel(tup[2]).fetch_message(tup[0])
            except:
                await db.execute("Delete from Giveaway where MessageID = ?", (tup[0],))
                await db.commit()
                continue

            seconds = tup[3] - current_time

            old_embed = msg.embeds[0]

            description = old_embed.description.split("\n")
            description[1] = custom_datetime(seconds)

            embed = discord.Embed(
                description="\n".join(description),
                colour=discord.Colour.green()
            )

            embed.set_author(name=old_embed.author.name)

            embed.set_footer(text=old_embed.footer.text)

            try:
                await msg.edit(embed=embed)
            except discord.Forbidden:
                await db.execute("Delete from Giveaway where MessageID = ?", (msg.id,))
                await db.commit()
