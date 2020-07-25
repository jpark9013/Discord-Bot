import sqlite3
import time
import random

import discord
from discord.ext import commands, tasks

from bot.utils.message import send_embed, to_embed


class Reminders(commands.Cog, name="Reminders"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.check_reminders.start()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def reminder(self, ctx):
        """Get a list of all your reminders."""

        cursor = await db.execute("Select Reminder, Time, ID from Reminders where MemberID = ? order by Time asc",
                                  (ctx.author.id,))
        result = await cursor.fetchall()

        if not result:
            return await send_embed(ctx, "You do not have any reminders.", negative=True)

        embeds = []

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Reminders",
        )
        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

        for index, tup in enumerate(result, start=1):
            days, remainder = divmod(tup[1] - time.time(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days == 0:
                embed.add_field(name=f"``{tup[2]}`` | "
                                     f"In {int(hours)} hours, {int(minutes)} minutes and {int(seconds)} seconds:",
                                value=tup[0], inline=False)
            else:
                embed.add_field(name=f"``{tup[2]}`` | "
                                     f"In {int(days)} days, {int(hours)} hours and {int(minutes)} minutes:",
                                value=tup[0], inline=False)

            if index % 10 == 0 or index == len(result):
                if len(result) == 1:
                    embed.set_footer(text=f"{len(result)} reminder")

                else:
                    embed.set_footer(text=f"{len(result)} reminders")

                embeds.append(embed)

                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title="Reminders",
                )
                embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

        await self.bot.paginate(ctx, embeds)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @reminder.command(aliases=["add"])
    async def create(self, ctx, minutes: float, *, reminder: str):
        """A reminder you can create. The bot will DM you when time is up."""

        if minutes < 0 or minutes > 525600:
            return await send_embed(ctx, "Invalid time specified. Must be between 0 and 525600 minutes.", negative=True)

        ID = str(10 ** 30 + random.randint(0, 10 ** 31 - 10 ** 30 - 1))

        await db.execute("Insert into Reminders values (?, ?, ?, ?)",
                         (ctx.author.id, reminder, time.time() + minutes * 60, ID))
        await db.commit()

        await send_embed(ctx, f"Reminder set. The ID is ``{ID}``.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @reminder.command()
    async def delete(self, ctx, ID: str):
        """Delete a reminder based on its ID."""

        cursor = await db.execute("Select count(*) from Reminders where MemberID = ? and ID = ?", (ctx.author.id, ID))
        result = await cursor.fetchone()

        if not result:
            await send_embed(ctx, f"Reminder with ID ``{ID}`` does not exist.", negative=True)

        await db.execute("Delete from Reminders where MemberID = ? and ID = ?", (ctx.author.id, ID))
        await db.commit()

        await send_embed(ctx, f"Deleted reminder with ID ``{ID}``")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @reminder.command()
    async def clear(self, ctx):
        """Clear all of your reminders."""

        await db.execute("Delete from Reminders where MemberID = ?", (ctx.author.id,))
        await db.commit()

        await send_embed(ctx, "Cleared all reminders.")

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        cursor = await db.execute("Select MemberID, Reminder from Reminders where Time <= ?", (time.time(),))
        result = await cursor.fetchall()

        for tup in result:
            try:
                member = self.bot.get_user(tup[0]) or await self.bot.fetch_user(tup[0])
                await member.send(embed=to_embed(tup[1], info=True))

            except:  # Member deleted account, member doesn't share server with bot etc.
                pass

        try:
            await db.execute("Delete from Reminders where Time <= ?", (time.time(),))
            await db.commit()

        except sqlite3.OperationalError:
            pass
