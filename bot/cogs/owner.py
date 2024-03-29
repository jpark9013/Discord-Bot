import asyncio
import json
import typing
from datetime import datetime

import discord
from discord.ext import commands, tasks

from utils.format import send_embed, to_embed


class Owner(commands.Cog, name="Owner"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.change_status.start()

    @commands.is_owner()
    @commands.command()
    async def createtables(self, ctx):
        """Create SQL tables if needed."""

        with open("createtables.json", "r") as file:
            """List of Database tables to create"""

            create_tables = json.load(file)

        for i in create_tables:
            await db.execute(i)
            await db.commit()

        await send_embed(ctx, "Created tables.")

    @commands.is_owner()
    @commands.command()
    async def shutdown(self, ctx):
        """Shut down the bot"""

        try:
            await send_embed(ctx, "Shutting down...")

            channel = self.bot.get_guild(732980515807952897).get_channel(736352506669694976)

            embed = discord.Embed(
                colour=discord.Colour.red(),
                description="Bot is offline."
            )
            embed.set_footer(text=f"Time: {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

            await channel.send(embed=embed)

            await db.close()
            await self.bot.close()

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def changename(self, ctx, *, name: str):
        """Change the bot username"""

        try:
            await self.bot.user.edit(username=name)
            await send_embed(ctx, f"Changed bot name to {name}")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def changeavatar(self, ctx, url: typing.Union[discord.Attachment, str]):
        """Change bot avatar. Provide a URL or attachment."""

        if isinstance(url, discord.Attachment):
            url = url.url  # YEP URL

        try:
            async with self.bot.session.get(url) as response:
                url_bytes = await response.content.read()

            await self.bot.user.edit(avatar=url_bytes)
            await send_embed(ctx, "Changed bot avatar.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def autostatus(self, ctx, space: typing.Optional[bool] = True, *, status: str):
        """Autostatus the bot. Cycles through the provided name every second just like Aimware.net in CSGO. You might
        get rate limited if you put the number of seconds under 60."""

        if space:
            status += " "

        try:
            self.bot.x = 0
            self.bot.statuses = [status]
            status = list(status)
            for i in range(len(status) - 1):
                lastposition = status.pop()
                status.insert(0, lastposition)
                self.bot.statuses.append("".join(status))
            self.bot.autostatus = True
            await send_embed(ctx, f"Successfully set autostatus on {self.bot.statuses[0]}")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def autostatusoff(self, ctx):
        """Turn autostatus on/off"""

        self.bot.autostatus = not self.bot.autostatus
        if self.bot.autostatus:
            await send_embed(ctx, "Turned autostatus on.")
        else:
            await send_embed(ctx, "Turned autostatus off.")

    @commands.is_owner()
    @commands.command()
    async def changeseconds(self, ctx, seconds: int):
        """Number of seconds between changing the status of the bot. Beware, anything below 12 may get the bot rate
        limited."""

        if 1 <= seconds <= 120:
            self.change_status.change_interval(seconds=seconds)
            await send_embed(ctx, f"Successfully changed status changing cooldown to {str(seconds)}")
        else:
            await send_embed(ctx, "Invalid time to change seconds; must be an integer between 1 and 120.",
                             negative=True)

    @commands.is_owner()
    @commands.command()
    async def reversestatusorder(self, ctx):
        """Reverses status order. If it was going right, it would go left after this command, and vice versa."""

        self.bot.reverse_order = not self.bot.reverse_order
        if self.bot.reverse_order:
            await send_embed(ctx, "Status now reversing.")

        else:
            await send_embed(ctx, "Status stopped reversing.")

    @commands.is_owner()
    @commands.command()
    async def statuslist(self, ctx, *, statuses):
        """Manually make a changing status with each entry being in the list."""

        self.bot.x = 0
        statuses = statuses.replace("\n", self.bot.split)
        statuslist = statuses.split(self.bot.split)
        if len(statuslist) == 1:
            return await send_embed(ctx, "You cannot have a list with only 1 entry.", negative=True)
        self.bot.statuses = statuslist
        self.bot.autostatus = True
        await send_embed(ctx, "Changed statuslist.")

    @commands.is_owner()
    @commands.command()
    async def changesplit(self, ctx, split):
        """Change the split that the list splits on. For example, say that you want 'a r' in the status changing list,
        but you can't because the list splits on the whitespace. You can change the split to, for example, 'ttg' and it
        won't split on 'a r' anymore. You just have to sub out space for 'ttg'. Another example; if I want a list with
        'duck', 'goose', and 'mouse', with '4' as the split, I can do 'duck4goose4mouse' to get the list. Sub
        out where you would normally put a spacebar for the split. You can make the split as long or short as you want,
        as long as it's not 0 characters. It can even include spaces if you like!."""

        self.bot.split = split
        await send_embed(ctx, f"Split changed to ``{split}``.")

    @tasks.loop(seconds=60)
    async def change_status(self):
        await self.bot.wait_until_ready()
        try:
            if self.bot.autostatus:
                i = len(self.bot.statuses) - 1 - self.bot.x
                await self.bot.change_presence(activity=discord.Game(self.bot.statuses[i]))

                if self.bot.reverse_order:
                    self.bot.x += 1

                else:
                    self.bot.x -= 1

                if self.bot.x >= len(self.bot.statuses):
                    self.bot.x = 0

                elif self.bot.x < 0:
                    self.bot.x += len(self.bot.statuses)

        except Exception as e:
            print(e)

    @commands.is_owner()
    @commands.command()
    async def changestatus(self, ctx, *, status: str):
        try:
            await self.bot.change_presence(activity=discord.Game(status))
            await send_embed(ctx, f"Changed presence to {status}")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def sharedguilds(self, ctx, memberID: int):
        """Returns a list of all guild IDs a member is in that the bot is also in. If it prints blank, then there are no
        guilds that they share in common."""

        try:
            member = self.bot.get_member(memberID) or await self.bot.fetch_member(memberID)
        except:
            return await send_embed(ctx, "Invalid Member ID.", negative=True)

        await send_embed(ctx, f'Shared guilds:\n'
                              f'{", ".join([str(guild.id) for guild in self.bot.guilds if guild.get_member(member.id)])}',
                         info=True)

    @commands.is_owner()
    @commands.command()
    async def reloadextension(self, ctx, name):
        """Reload an extension."""

        try:
            if name == "all":
                extensions = self.bot.extensions.copy()
                for i in extensions:
                    self.bot.reload_extension(i)
                await send_embed(ctx, "Reloaded all extensions.")
            else:
                self.bot.reload_extension(f"cogs.{name}")
                await send_embed(ctx, f"Reloaded extension with name ``{name}``.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def loadextension(self, ctx, name):
        """Load an extension."""

        try:
            self.bot.load_extension(f"cogs.{name}")
            await send_embed(ctx, f"Loaded extension with name ``{name}``.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def unloadextension(self, ctx, name):
        """Unload an extension."""

        try:
            self.bot.unload_extension(f"cogs.{name}")
            await send_embed(ctx, f"Unloaded extension with name ``{name}``.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def blacklistguild(self, ctx, guild: int):
        """Blacklist a guild. Give its ID."""

        guild = self.bot.get_guild(guild) or await self.bot.fetch_guild(guild)

        if not guild:
            return await send_embed(ctx, "Invalid Guild ID", negative=True)

        if guild.id in self.bot.blacklist["guilds"]:
            return await send_embed(ctx, "Guild already blacklisted", negative=True)

        with open("blacklist.json", "r") as f:
            blacklist = json.load(f)

        self.bot.blacklist["guilds"].append(guild.id)
        blacklist["guilds"].append(guild.id)

        with open("blacklist.json", "w") as f:
            json.dump(blacklist, f, indent=4)

        await send_embed(ctx, f"Blacklisted guild with ID ``{str(guild)}``.")

    @commands.is_owner()
    @commands.command()
    async def blacklistmember(self, ctx, member: typing.Union[discord.Member, int]):
        """Blacklist a member."""

        if isinstance(member, int):
            try:
                member = self.bot.get_user(member) or await self.bot.fetch_user(member)
                a = member.id

            except AttributeError:
                return await send_embed(ctx, "Member ID does not exist.", negative=True)

        if member.id in self.bot.blacklist["members"]:
            return await send_embed(ctx, "Member already blacklisted", negative=True)

        with open("blacklist.json", "r") as f:
            blacklist = json.load(f)

        self.bot.blacklist["members"].append(member.id)
        blacklist["members"].append(member.id)

        with open("blacklist.json", "w") as f:
            json.dump(blacklist, f, indent=4)

        await send_embed(ctx, f"Successfully blacklisted member with ID ``{str(member.id)}``")

    @commands.is_owner()
    @commands.command()
    async def unblacklistmember(self, ctx, member: typing.Union[discord.Member, int]):
        """Unblacklist a member."""

        if isinstance(member, int):
            try:
                member = discord.Object(id=member)

            except:
                return await send_embed(ctx, "Member ID does not exist.", negative=True)

        with open("blacklist.json", "r") as f:
            blacklist = json.load(f)

        if member.id not in blacklist["members"]:
            return await send_embed(ctx, "Member is not blacklisted.", negative=True)

        blacklist["members"].remove(member.id)

        with open("blacklist.json", "w") as f:
            json.dump(blacklist, f, indent=4)

        await send_embed(ctx, f"Successfully unblacklisted member with ID ``{str(member.id)}``")

    @commands.is_owner()
    @commands.command()
    async def unblacklistguild(self, ctx, ID: int):
        """Unblacklist a guild."""

        cursor = await db.execute("Select GuildID from Blacklist where GuildID = ?", (ID,))
        result = await cursor.fetchone()

        with open("blacklist.json", "r") as f:
            blacklist = json.load(f)

        if ID not in blacklist["guilds"]:
            return await send_embed(ctx, "Guild is not blacklisted.", negative=True)

        blacklist["guilds"].remove(ID)

        with open("blacklist.json", "w") as f:
            json.dump(blacklist, f, indent=4)

        await send_embed(ctx, f"Unblacklisted guild with ID ``{ID}``.")

    @commands.is_owner()
    @commands.command()
    async def leave(self, ctx, ID: int = None):
        """Make the bot leave the guild. Defaults to the guild in which the command was used in. Takes in Guild ID
        for the argument."""

        if ID:
            if not self.bot.get_guild(ID):
                return await send_embed(ctx, "Invalid server ID.", negative=True)

        message = await ctx.send(embed=discord.Embed(
            colour=discord.Colour.orange(),
            description="Are you sure you want to make the bot leave the server? You have 60 seconds to react to this "
                        "message with the green check mark."))

        def check(reaction, user):
            return str(reaction.emoji) == "✅" and user == ctx.author and reaction.message.id == message.id

        try:
            await self.bot.wait_for("reaction_add", timeout=60, check=check)

        except asyncio.TimeoutError:
            return await send_embed(ctx, "Command cancelled due to taking too long.", negative=True)

        if not ID:
            return await ctx.guild.leave()

        await self.bot.get_guild(ID).leave()

    @commands.is_owner()
    @commands.command(aliases=["print"])
    async def eval(self, ctx, *, code: str):
        """Tries to evaluate and print the given code in python. This is dangerous, be careful."""

        try:
            await ctx.send(f"```py\n"
                           f"{str(eval(code))}\n"
                           f"```")

        except Exception as e:
            await ctx.send(f"```py\n"
                           f"{str(e)}\n"
                           f"```")

    @commands.is_owner()
    @commands.command()
    async def nickbot(self, ctx, *, nick: str):
        """Nick the bot."""

        try:
            await ctx.me.edit(nick=nick)
            await send_embed(ctx, "Changed nickname.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.command()
    @commands.is_owner()
    async def server_info(self, ctx, ID: typing.Optional[int], *, name: str = None):
        """Get info of the specified server."""

        if not ID:
            guild = discord.utils.get(self.bot.guilds, name=name)
        else:
            guild = self.bot.get_guild(ID)

        if not guild:
            return await send_embed(ctx, "Guild with specified ID does not exist, or guild is not in bot cache.",
                                    negative=True)

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"{guild.name} statistics",
            description=guild.description
        )

        embed.set_thumbnail(url=str(guild.icon_url))
        embed.set_footer(text=f"Created at {guild.created_at.strftime('%m/%d/%Y, %H:%M:%S')}")

        value = guild.features
        if not value:
            value = ["None"]

        embed.add_field(name="Features", value="\n".join(value))

        lockedtextchannels = 0
        lockedcategorychannels = 0

        if not guild.default_role.permissions.view_channel:
            lockedtextchannels = len(guild.text_channels)
            lockedcategorychannels = len(guild.categories)

        else:
            for chan in guild.text_channels:
                if chan.overwrites_for(guild.default_role).view_channel is False:
                    lockedtextchannels += 1

            for category in guild.categories:
                if category.overwrites_for(guild.default_role).view_channel is False:
                    lockedcategorychannels += 1

        lockedvoicechannels = 0

        if not guild.default_role.permissions.connect:
            lockedvoicechannels = len(guild.voice_channels)

        else:
            for chan in guild.voice_channels:
                if chan.overwrites_for(guild.default_role).connect is False:
                    lockedvoicechannels += 1

        value = f"<:textchannel:739339100058026055> {len(guild.text_channels)} " \
                f"({lockedtextchannels} locked)\n" \
                f"<:voicechannel:739339126750445579> {len(guild.voice_channels)} " \
                f"({lockedvoicechannels} locked)\n" \
                f"<:category:739339033578176522> {len(guild.categories)} " \
                f"({lockedcategorychannels} locked)"

        embed.add_field(name="Channels", value=value)

        online = 0
        idle = 0
        dnd = 0
        streaming = 0
        offline = 0
        bots = 0

        for i in guild.members:
            if i.status.value == "online":
                online += 1
            elif i.status.value == "idle":
                idle += 1
            elif i.status.value == "dnd":
                dnd += 1
            elif i.status.value == "offline":
                offline += 1
            if i.bot:
                bots += 1
            if isinstance(i.activity, discord.Streaming):
                streaming += 1

        value = f"<:online:739335368410660905> {online}" \
                f"<:idle:739335424853672007> {idle}" \
                f"<:dnd:739335328288211004> {dnd}" \
                f"<:streaming:739335478376923217> {streaming}" \
                f"<:offline:739335400593817602> {offline}\n" \
                f"Total: {len(guild.members)} members ({bots} bots)"

        embed.add_field(name="Members", value=value, inline=False)

        value = f"Nitro Tier: {guild.premium_tier}\n" \
                f"Boosters: {guild.premium_subscription_count}\n" \
                f"Maximum bitrate: {int(guild.bitrate_limit)} hz\n" \
                f"File size limit: {int(guild.filesize_limit / 1048576)}MB\n" \
                f"Maximum number of emojis: {guild.emoji_limit}"

        embed.add_field(name="Nitro", value=value, inline=False)

        value = f"{len(guild.roles)} roles, of which " \
                f"{len([i for i in guild.roles if i.permissions.administrator])} have administrator permissions."

        embed.add_field(name="Roles", value=value, inline=False)

        animated = len([i for i in guild.emojis if i.animated])

        value = f"Regular: {len(guild.emojis) - animated}/{guild.emoji_limit}\n" \
                f"Animated: {animated}/{guild.emoji_limit}\n" \
                f"{len(guild.emojis)}/{guild.emoji_limit} total"

        embed.add_field(name="Emojis", value=value, inline=False)

        if not guild.afk_channel:
            afkchannel = "None"
        else:
            afkchannel = f"<#{guild.afk_channel.id}>"

        value = f"ID: {guild.id}\n" \
                f"Owner: {guild.owner.mention}\n" \
                f"AFK Timeout: {int(guild.afk_timeout/60)} minutes\n" \
                f"AFK Channel: {afkchannel}\n" \
                f"Voice Region: {guild.region if isinstance(guild.region, str) else guild.region.value}\n" \
                f"Icon URL: {str(guild.icon_url) if str(guild.icon_url) else 'None'}\n" \
                f"Banner URL: {str(guild.banner_url) if str(guild.banner_url) else 'None'}\n"

        embed.add_field(name="Miscallenous", value=value, inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def sendtochannel(self, ctx, guildID: int, channelID: int, *, string):
        """Send to a channel."""

        try:
            channel = self.bot.get_guild(guildID).get_channel(channelID)
        except AttributeError:
            channel = self.bot.get_channel(channelID)

        await channel.send(string)
        await send_embed(ctx, "Sent message.")

    @commands.command()
    @commands.is_owner()
    async def sendembedtochannel(self, ctx, guildID: int, channelID: int, type: str, *, string):
        """Send embed to channel."""

        try:
            channel = self.bot.get_guild(guildID).get_channel(channelID)
        except AttributeError:
            channel = self.bot.get_channel(channelID)

        await channel.send(embed=to_embed(string, type))
        await send_embed(ctx, "Sent embed.")

    @commands.command(aliases=["ec"])
    @commands.is_owner()
    async def executecommand(self, ctx, guildID: typing.Optional[int], channelID: typing.Optional[int], command: str,
                             *args, **kwargs):
        """Execute a command in another server. Put quotes around the desired command."""

        send_message = True

        if not guildID or not channelID:
            channel = ctx.channel
            send_message = False
        else:
            channel = self.bot.get_guild(guildID).get_channel(channelID)

        x = None

        async for i in channel.history(limit=1):
            x = i

        context = await self.bot.get_context(x)
        cmd = self.bot.get_command(command)
        await cmd(context, *args, **kwargs)
        if send_message:
            await send_embed(ctx, "Command executed.")

    @commands.command(aliases=["dm"])
    @commands.is_owner()
    async def directmessage(self, ctx, member: typing.Union[discord.Member, int], *, content):
        """DM a member."""

        if isinstance(member, int):
            member = self.bot.get_user(member) or await self.bot.fetch_user(member)

        await member.send(content)

    @commands.command()
    @commands.is_owner()
    async def sql(self, ctx, *, query):
        """Execute some SQL."""

        if query.split()[0].lower() == "select":
            cursor = await db.execute(query)
            result = await cursor.fetchall()

            await send_embed(ctx, result, info=True)

        else:
            await db.execute(query)
            await db.commit()

            await send_embed(ctx, "Committed to database.")


def setup(bot):
    bot.add_cog(Owner(bot))
