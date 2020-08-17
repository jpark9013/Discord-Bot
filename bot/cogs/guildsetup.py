import json
import typing
from datetime import datetime

import discord
from discord.ext import commands

from bot.utils.format import send_embed, to_embed


class Guild_Setup(commands.Cog, name="Guild Setup"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if str(guild.id) not in self.bot.prefixes.keys():
            self.bot.prefixes[str(guild.id)] = "?"

        with open("prefixes.json", "w") as prefixes_file:
            json.dump(self.bot.prefixes, prefixes_file, indent=4)

        cursor = await db.execute("Select count(*) from Logging where GuildID = ?", (guild.id,))
        result = await cursor.fetchone()

        if not result[0]:
            await db.execute("Insert into Logging values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                             "?, ?, ?, ?, ?)",
                             (guild.id, None, False, False, False, False, False, False, False, False,
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
    async def changeprefix(self, ctx, prefix: str):
        """Change the bot prefix for the server."""

        if not ctx.author.guild_permissions.administrator and ctx.author.id != 648741756384575509:
            return await send_embed(ctx, "You do not have permission to do that.", negative=True)

        if len(prefix) > 5:
            return await send_embed(ctx, f"You cannot have a prefix more than 5 characters long.")

        self.bot.prefixes[str(ctx.guild.id)] = prefix

        with open("prefixes.json", "w") as prefixes_file:
            json.dump(self.bot.prefixes, prefixes_file, indent=4)

        await send_embed(ctx, f"Guild prefix changed to ``{prefix}``.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def blacklist(self, ctx):
        """Get a list of all blacklisted channels and words."""

        guild = self.bot.blacklistchannels.get(ctx.guild.id, {})
        channels = guild.get("channels", set())
        words = guild.get("words", set())

        if not channels and not words:
            return await send_embed(ctx, "No blacklisted channels or words.", negative=True)

        channels = ", ".join(f"<#{id}>" for id in channels)

        words = ", ".join(f"||{word}||" for word in words)

        if not channels:
            channels = "None"
        elif not words:
            words = "None"

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

        channels = self.bot.blacklistchannels.get(ctx.guild.id, {}).get("channels", set())

        if channel.id not in channels:
            message = "Blacklisted channel."

            try:
                guild = self.bot.blacklistchannels[ctx.guild.id]
            except KeyError:
                self.bot.blacklistchannels[ctx.guild.id] = {"channels": set(), "words": set()}
                guild = self.bot.blacklistchannels[ctx.guild.id]

            channels = guild["channels"]

            channels.add(channel.id)

            await db.execute("Insert into Blacklist values (?, ?, ?)", (ctx.guild.id, channel.id, None))
            await db.commit()

        else:
            message = "Unblacklisted channel."

            channels.remove(channel.id)

            await db.execute("Delete from Blacklist where ChannelID = ? and GuildID = ?", (channel.id, ctx.guild.id))
            await db.commit()

        await send_embed(ctx, message)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @chan.command(aliases=["all"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def total(self, ctx):
        """Blacklist all channels besides the current one."""

        try:
            result = self.bot.blacklistchannels[ctx.guild.id]
        except KeyError:
            self.bot.blacklistchannels[ctx.guild.id] = {"channels": set(), "words": set()}
            result = self.bot.blacklistchannels[ctx.guild.id]

        result = result["channels"]

        message = "Blacklisted all channels."

        text_channels = {i.id for i in ctx.guild.text_channels if i.id != ctx.channel.id}

        if result != text_channels:
            for id in text_channels:
                await db.execute("Insert or replace into Blacklist values (?, ?, ?)", (ctx.guild.id, id, None))
                await db.commit()

            result = text_channels

        else:
            message = "Unblacklisted all channels."

            await db.execute("Delete from Blacklist where GuildID = ?", (ctx.guild.id,))
            await db.commit()

            result = set()

        await send_embed(ctx, message)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @blacklist.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def word(self, ctx, word: str):
        """Blacklist a word. Summon this command again with the same argument to unblacklist a word. You can also put
        spoilers around the word, and the bot will try to remove them when adding them to the blacklist."""

        try:
            guild = self.bot.blacklistchannels[ctx.guild.id]
        except KeyError:
            self.bot.blacklistchannels[ctx.guild.id] = {"channels": set(), "words": set()}
            guild = self.bot.blacklistchannels[ctx.guild.id]

        words = guild["words"]

        if word[0] == "|" and word[1] == "|" and word[-1] == "|" and word[-2] == "|":
            word = word[2:-2]

        message = f"||``{word}``|| added to blacklist."

        if word not in words:
            await db.execute("Insert into Blacklist values (?, ?, ?)",
                             (ctx.guild.id, None, word))
            await db.commit()

            words.add(word)

        else:
            message = f"||``{word}``|| removed from blacklist."

            await db.execute("Delete from Blacklist where GuildID = ? and Word = ?", (ctx.guild.id, word))
            await db.commit()

            words.remove(word)

        await send_embed(ctx, message)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def joinmessage(self, ctx, *, message):
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
    async def leavemessage(self, ctx, *, message):
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

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.group(aliases=["ar"])
    async def autorespond(self, ctx):
        """Base autorespond command."""

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.guild)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @autorespond.command(aliases=["add"])
    async def create(self, ctx, trigger: str, *, message: str = ''):
        """Create an autorespond for a certain trigger. The trigger MUST BE IN QUOTES, otherwise the bot will only catch
         the first word of it. Lastly, this serves as a workaround to disable certain commands, but for everyone, if the
          response is none."""

        trigger.replace('"', '\"')
        message.replace('"', '\"')

        autorespond = self.bot.autorespond.get(ctx.guild.id, {})

        if len(autorespond) >= 100:
            return await send_embed(ctx, "Your server has the max autorespond messages of 100.", negative=True)

        if trigger in autorespond:
            return await send_embed(ctx, "Your server already has this autorespond trigger.", negative=True)

        await db.execute("Insert into AutoRespond values (?, ?, ?)", (ctx.guild.id, trigger, message))
        await db.commit()

        try:
            guild = self.bot.autorespond[ctx.guild.id]
            guild[trigger] = message
        except KeyError:
            self.bot.autorespond[ctx.guild.id] = {trigger: message}

        await send_embed(ctx, "Created AutoRespond trigger.")

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.guild)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @autorespond.command(aliases=["remove"])
    async def delete(self, ctx, *, trigger: str):
        """Delete a trigger for AutoRespond."""

        trigger.replace('"', '\"')

        autorespond = self.bot.autorespond.get(ctx.guild.id, {})

        if trigger not in autorespond:
            return await send_embed(ctx, "No matching trigger found for this server.", negative=True)

        await db.execute("Delete from AutoRespond where GuildID = ? and Trigger = ?",
                         (ctx.guild.id, trigger))
        await db.commit()

        del autorespond[trigger]

        await send_embed(ctx, "Deleted AutoRespond trigger.")

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.guild)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @autorespond.command()
    async def edit(self, ctx, trigger: str, *, message: str = ''):
        """Edit an AutoRespond trigger."""

        trigger.replace('"', '\"')
        message.replace('"', '\"')

        autorespond = self.bot.autorespond.get(ctx.guild.id, {})

        if trigger not in autorespond:
            return await send_embed(ctx, "Specified trigger does not exist.", negative=True)

        await db.execute("Update AutoRespond set Message = ? where GuildID = ? and Trigger = ?",
                         (message, ctx.guild.id, trigger))
        await db.commit()

        autorespond[trigger] = message

        await send_embed(ctx, "Edited AutoRespond trigger.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @autorespond.command(aliases=["all"])
    async def list(self, ctx):
        """Lists all AutoRespond triggers for this server."""

        autorespond = self.bot.autorespond.get(ctx.guild.id, {})

        if not autorespond:
            return await send_embed(ctx, "No AutoRespond triggers on this server.", negative=True)

        embeds = []
        desc = []

        # Enumerating through keys
        for i, v in enumerate(autorespond, start=1):
            desc.append(f"{i}. Trigger: ``{v}`` (Message: ``{autorespond[v]}``)")
            if i == len(autorespond) or i % 10 == 0:
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title=f"AutoRespond triggers for {ctx.guild.name}",
                    description="\n".join(desc)
                )

                embeds.append(embed)
                desc = []

        await self.bot.paginate(ctx, embeds)
