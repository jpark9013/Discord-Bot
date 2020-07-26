import asyncio
import json
import typing
from datetime import datetime

import discord
from discord.ext import commands, tasks
from prettytable import PrettyTable

from bot.utils.message import send_embed


class Owner(commands.Cog, name="Owner"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

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
    async def autostatus(self, ctx, *, status):
        """Autostatus the bot. Cycles through the provided name every second just like Aimware.net in CSGO. You might
        get rate limited if you put the number of seconds under 60."""

        try:
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

        statuses = statuses.replace("\n", self.bot.ON_SPLIT)
        statuslist = statuses.split(self.bot.ON_SPLIT)
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

        self.bot.ON_SPLIT = split
        await send_embed(f"Split changed to ``{split}``.")

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
            self.bot.reload_extension(f"{name}.cogs")
            await send_embed(ctx, f"Reloaded extension with name ``{name}``.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def loadextension(self, ctx, name):
        """Load an extension."""

        try:
            self.bot.load_extension(f"{name}.cogs")
            await send_embed(ctx, f"Loaded extension with name ``{name}``.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.is_owner()
    @commands.command()
    async def unloadextension(self, ctx, name):
        """Unload an extension."""

        try:
            self.bot.unload_extension(f"{name}.cogs")
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

        with open("blacklist.json", "r") as f:
            blacklist = json.load(f)

        if guild.id in blacklist["guilds"]:
            return await send_embed(ctx, "Guild already blacklisted", negative=True)

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
                member = discord.Object(id=member)

            except:
                return await send_embed(ctx, "Member ID does not exist.", negative=True)

        with open("blacklist.json", "r") as f:
            blacklist = json.load(f)

        if member.id in blacklist["members"]:
            return await send_embed(ctx, "Member already blacklisted", negative=True)

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
            await self.bot.get_member(self.bot.id).edit(nick=nick)

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)
