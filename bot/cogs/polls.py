import operator
import time
import typing
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot.utils.format import send_embed


class Polls(commands.Cog, name="Polls"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.EMOJIS = (
            "1️⃣",
            "2️⃣",
            "3️⃣",
            "4️⃣",
            "5️⃣",
            "6️⃣",
            "7️⃣",
            "8️⃣",
            "9️⃣",
            "🔟"
        )
        self.check_polls.start()

    @commands.group()
    async def poll(self, ctx):
        """The base poll command. Doesn't do anything when invoked."""

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @poll.command(aliases=["add"])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.guild_only()
    async def create(self, ctx, channel: typing.Optional[discord.TextChannel], minutes: float, title: str, *options):
        """Create a poll. Make the options space separated, with quotes if spaces within the options themselves, such as
        ``do thing 2`` are needed."""

        if len(options) > 10 or len(options) < 1:
            return await send_embed(ctx, "Invalid number of options; must be between one and ten.", negative=True)

        if minutes < 0.5 or minutes > 604800:
            return await send_embed(ctx, "Invalid length of time given. Must be between 0.5 and 604800 minutes.",
                                    negative=True)

        if not channel:
            channel = ctx.channel

        then = time.time() + minutes * 60

        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title=title
        )
        embed.set_author(name="React to answer the poll with the corresponding number.")
        embed.set_footer(text=f"Ends at {datetime.utcfromtimestamp(then).strftime('%m/%d/%Y, %H:%M:%S')}")
        embed.description = "\n\n".join([f"{i}. {v}" for i, v in enumerate(options, start=1)])

        msg = await channel.send(embed=embed)

        to_insert = (ctx.guild.id, channel.id, msg.id, len(options), then) + tuple([i for i in options]) \
                    + tuple([None for i in range(10 - len(options))])

        await db.execute("Insert into Polls values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", to_insert)
        await db.commit()

        for i in range(len(options)):
            await msg.add_reaction(self.EMOJIS[i])

        await send_embed(ctx, "Created poll.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @poll.command(aliases=["stop"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def end(self, ctx, msg: discord.Message):
        """End a poll early. Give Message ID as the parameter."""

        if msg.guild != ctx.guild:
            return await send_embed(ctx, "You do not have permission to do that.", negative=True)

        cursor = await db.execute("Select count(*), TopNumber, "
                                  "Option1, Option2, Option3, Option4, Option5, Option6, Option7, Option8, Option9, "
                                  "Option10 "
                                  "from Polls where MessageID = ?", (msg.id,))
        result = await cursor.fetchone()

        if not result[0]:
            return await send_embed(ctx, "The specified poll does not exist.", negative=True)

        old_embed = msg.embeds[0]

        reactions = [i.count for i in msg.reactions]

        options = [v for i, v in enumerate(result[2:12]) if i <= result[1]]
        result_dict = {i + 1: reactions[i] for i in range(result[1])}
        result_dict = dict(sorted(result_dict.items(), key=operator.itemgetter(1), reverse=True))

        results = [f"``{options[i - 1]}`` with **{v}** votes "
                   f"(original emoji of option was {self.EMOJIS[i - 1]})" for i, v in result_dict.items()]

        description = ["Results:"] + [f"{i}. {v}" for i, v in enumerate(results, start=1)]

        embed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"Poll has ended\n"
                  f"(Original title: {old_embed.title})",
            description="\n\n".join(description)
        )

        embed.set_footer(text=f"Ended at {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

        await msg.edit(embed=embed)

        await db.execute("Delete from Polls where MessageID = ?", (msg.id,))
        await db.commit()

        await send_embed(ctx, "Ended poll.")

    @tasks.loop(seconds=30)
    async def check_polls(self):
        cursor = await db.execute("Select GuildID, ChannelID, MessageID from Polls where TimeEnding <= ?",
                                  (time.time(),))
        result = await cursor.fetchall()

        for guild_id, channel_id, message_id in result:
            try:
                msg = await self.bot.get_guild(guild_id).get_channel(channel_id).fetch_message(message_id)

                cmd = self.bot.get_command("poll end")
                ctx = await self.bot.get_context(msg)
                await cmd(ctx, msg)
            except Exception as e:
                print(e)
