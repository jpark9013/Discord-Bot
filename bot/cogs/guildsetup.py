import json
import typing
from datetime import datetime

import discord
from discord.ext import commands

from bot.utils.message import send_embed, to_embed


class Guild_Setup(commands.Cog, name="Guild Setup"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        with open("prefixes.json", "r") as prefixes_file:
            prefixes = json.load(prefixes_file)

        if str(guild.id) not in prefixes:
            prefixes[str(guild.id)] = ";"

        with open("prefixes.json", "w") as prefixes_file:
            json.dump(prefixes, prefixes_file, indent=4)

        cursor = await db.execute("Select count(*) from Logging where GuildID = ?", (guild.id,))
        result = await cursor.fetchone()

        if not result[0]:
            await db.execute("Insert into Logging values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                             "?, ?, ?, ?, ?)",
                             (guild.id, None, json.dumps([]), False, False, False, False, False, False, False, False,
                              False, False, False, False, False, False, False, False, False, False, False, False,
                              False, False))
            await db.commit()

        cursor = await db.execute("Select count(*) from AutoMod where GuildID = ?", (guild.id,))
        result = await cursor.fetchone()

        if not result[0]:
            await db.execute("Insert into AutoMod values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (guild.id, False, False, False, False, False, False, False, False))
            await db.commit()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def changeprefix(self, ctx, prefix: str):
        """Change the bot prefix for the server."""

        if len(prefix) > 5:
            return await send_embed(ctx, f"You cannot have a prefix more than 5 characters long.")
        with open("prefixes.json", "r") as prefixes_file:
            prefixes = json.load(prefixes_file)

        prefixes[str(ctx.guild.id)] = prefix

        with open("prefixes.json", "w") as prefixes_file:
            json.dump(prefixes, prefixes_file, indent=4)

        await send_embed(ctx, f"Guild prefix changed to ``{prefix}``.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def blacklist(self, ctx):
        """Get a list of all blacklisted channels and words."""

        cursor = await db.execute("Select Channels, Words from Blacklist where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "No blacklisted channels or words.", negative=True)

        if json.loads(result[0]):
            channels = ", ".join(f"<#{id}>" for id in json.loads(result[0]))
        else:
            channels = "None!"

        if json.loads(result[1]):
            words = ", ".join(f"||{word}||" for word in json.loads(result[1]))
        else:
            words = "None!"

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Blacklist",
            description=f"**Channels:** {channels}\n"
                        f"**Words:** {words}"
        )

        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @blacklist.group(invoke_without_command=True, aliases=["channel"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def chan(self, ctx, channel: discord.TextChannel):
        """Blacklist or unblacklist a channel based on its id or mention. Type 'all' at the end to blacklist all
        channels besides the current one. By the way this command will break very often because of SQL glitches."""

        cursor = await db.execute("Select Channels from Blacklist where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        message = "Blacklisted channel."

        if not result:
            await db.execute("Insert into Blacklist values (?, ?, ?)",
                             (ctx.guild.id, json.dumps([channel.id]), json.dumps([])))
            await db.commit()

        else:
            result = json.loads(result[0])

            if channel.id in result:
                result.remove(channel.id)
                message = "Unblacklisted channel."
            else:
                result.append(channel.id)

            await db.execute("Update Blacklist set Channels = ? where GuildID = ?",
                             (json.dumps(result), ctx.guild.id))
            await db.commit()

        await send_embed(ctx, message)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @chan.command(aliases=["all"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def total(self, ctx):
        """Blacklist all channels besides the current one."""

        cursor = await db.execute("Select Channels from Blacklist where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        message = "Blacklisted all channels."

        if not result:
            await db.execute("Insert into Blacklist values (?, ?, ?)",
                             (ctx.guild.id, json.dumps([i.id for i in ctx.guild.text_channels if i != ctx.channel]),
                              json.dumps([])))
            await db.commit()

        else:
            result = json.loads(result[0])
            if result == [i.id for i in ctx.guild.text_channels if i != ctx.channel]:
                await db.execute("Update Blacklist values set Channels = ? where GuildID = ?",
                                 (json.dumps([]), ctx.guild.id))
                await db.commit()
                message = "Unblacklisted all channels."
            else:
                await db.execute("Update Blacklist set Channels = ? where GuildID = ?",
                                 (json.dumps([i.id for i in ctx.guild.text_channels if i != ctx.channel]),
                                  ctx.guild.id))
                await db.commit()

        await send_embed(ctx, message)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @blacklist.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def word(self, ctx, word: str):
        """Blacklist a word. Summon this command again with the same argument to unblacklist a word. You can also put
        spoilers around the word, and the bot will try to remove them when adding them to the blacklist."""

        cursor = await db.execute("Select Words from Blacklist where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if word[0] == "|" and word[1] == "|" and word[-1] == "|" and word[-2] == "|":
            word = word[2:-2]

        message = f"||``{word}``|| added to blacklist."

        if not result:
            await db.execute("Insert into Blacklist values (?, ?, ?)",
                             (ctx.guild.id, json.dumps([]), json.dumps([word])))
            await db.commit()

        else:
            result = json.loads(result[0])

            if word in result:
                result.remove(word)
                message = f"||``{word}``|| removed from blacklist."
            else:
                result.append(word)

            await db.execute("Update Blacklist set Words = ? where GuildID = ?", (json.dumps(result), ctx.guild.id))
            await db.commit()

        await send_embed(ctx, message)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def joinmessage(self, ctx, *, message=None):
        """Set a join message. You must also set the channel in order for join messages to be sent."""

        cursor = await db.execute("Select count(*) from JLMessage where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result[0]:
            await db.execute("Update JLMessage set JoinMessage = ? where GuildID = ?", (message, ctx.guild.id))
            await db.commit()

        else:
            await db.execute("Insert into JLMessage values (?, ?, ?, ?, ?)", (ctx.guild.id, message, None, None, None))
            await db.commit()

        await send_embed(ctx, "Set join message.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @joinmessage.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set a channel for sending join messages."""

        cursor = await db.execute("Select count(*) from JLMessage where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result[0]:
            await db.execute("Update JLMessage set JoinMessageChannel = ? where GuildID = ?",
                             (channel.id, ctx.guild.id))
            await db.commit()

        else:
            await db.execute("Insert into JLMessage values (?, ?, ?, ?, ?)",
                             (ctx.guild.id, None, channel.id, None, None))
            await db.commit()

        await send_embed(ctx, "Set join message channel.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def leavemessage(self, ctx, *, message=None):
        """Set leave message. You must also set the channel in order for leave messages to be sent."""

        cursor = await db.execute("Select count(*) from JLMessage where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result[0]:
            await db.execute("Update JLMessage set LeaveMessage = ? where GuildID = ?", (message, ctx.guild.id))
            await db.commit()

        else:
            await db.execute("Insert into JLMessage values (?, ?, ?, ?, ?)", (ctx.guild.id, None, None, message, None))
            await db.commit()

        await send_embed(ctx, "Set leave message.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @leavemessage.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set a channel for sending join messages."""

        cursor = await db.execute("Select count(*) from JLMessage where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result[0]:
            await db.execute("Update JLMessage set LeaveMessageChannel = ? where GuildID = ?",
                             (channel.id, ctx.guild.id))
            await db.commit()

        else:
            await db.execute("Insert into JLMessage values (?, ?, ?, ?, ?)",
                             (ctx.guild.id, None, None, None, channel.id))
            await db.commit()

        await send_embed(ctx, "Set leave message channel.")

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.guild)
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def createrolereact(self, ctx, role: discord.Role, channel: discord.TextChannel,
                              emoji: typing.Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str],
                              deleteOnRemove: bool = True, *, text: str):
        """Create a role react message in a certain channel."""

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="React for Role",
            description=text
        )

        embed.set_footer(text=f"Created by {str(ctx.author)} | {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

        msg = await channel.send(embed=embed)
        await msg.add_reaction(emoji)

        await db.execute("Insert into RoleReact values (?, ?, ?, ?)", (msg.id, role.id, str(emoji), deleteOnRemove))
        await db.commit()

        await send_embed(ctx, "Created role react message.")

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.guild)
    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def giveroleonjoin(self, ctx, role: discord.Role):
        """Give a role to any member when they join."""

        cursor = await db.execute("Select count(*) from RoleOnJoin where GuildID = ? and RoleID = ?",
                                  (ctx.guild.id, role.id))
        result = await cursor.fetchone()

        if result[0]:
            return await send_embed(ctx, "Role already given automatically.", negative=True)

        await db.execute("Insert into RoleOnJoin values (?, ?)", (ctx.guild.id, role.id))
        await db.commit()

        await send_embed(ctx, "Role will be given automatically to any member that joins.")

    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.guild)
    @createrolereact.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rainbow(self, ctx, channel: discord.TextChannel):
        """Create role react messages for all colors of the rainbow (ROYGBV + White, Grey, Black) """

        rainbow = {
            "Red": (discord.Colour.red(), "🔴"),
            "Orange": (discord.Colour.orange(), "🟠"),
            "Yellow": (discord.Colour.gold(), "🟡"),
            "Green": (discord.Colour.green(), "🟢"),
            "Blue": (discord.Colour.blue(), "🔵"),
            "Purple": (discord.Colour.purple(), "🟣"),
            "White": (discord.Colour.from_rgb(254, 254, 254), "⚪"),
            "Grey": (discord.Colour.from_rgb(128, 128, 128), "🔘"),
            "Black": (discord.Colour.from_rgb(1, 1, 1), "⚫")
        }

        ids = {}

        for i, tup in rainbow.items():
            role = await ctx.guild.create_role(name=i, colour=tup[0])
            ids[i] = (role.id, tup[0], tup[1])
            try:
                await role.edit(position=ctx.guild.me.top_role.position - 2)
            except:
                pass

        for colorname, tup in ids.items():
            embed = discord.Embed(
                colour=tup[1],
                title="React for Role",
                description=f"React to this message for the role color **{colorname}**!"
            )

            msg = await channel.send(embed=embed)

            await msg.add_reaction(tup[2])

        await send_embed(ctx, "Sent role react messages for all colors.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji(self, ctx):
        """The base emoji command."""

        pass

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    @emoji.command(aliases=["add"])
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def create(self, ctx, name, emoji: typing.Union[discord.Attachment, str], *, reason=None):
        """Create an emoji given an attachment."""

        if isinstance(emoji, discord.Attachment):
            byteobj = await emoji.read(use_cached=True)

            if not byteobj:
                byteobj = await emoji.read()

        else:
            async with self.bot.session.get(emoji) as resp:
                byteobj = await resp.content.read()

        await ctx.guild.create_custom_emoji(name=name, image=byteobj, reason=reason)
        await send_embed(ctx, "Created emoji.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    @emoji.command(aliases=["delete"])
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def remove(self, ctx, emoji: discord.Emoji, *, reason=None):
        """Remove an emoji."""

        await emoji.delete(reason=reason)
        await send_embed(ctx, "Deleted emoji.")
