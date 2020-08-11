import asyncio
import json
import sqlite3
import time
import typing
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot.utils.format import to_embed, send_embed


async def no_mute_role(ctx, bot):
    dict = bot.muteroles
    if str(ctx.guild.id) not in dict.keys():
        return await send_embed(ctx, "No mute role in this server set.", negative=True)
    if not ctx.guild.get_role(dict[str(ctx.guild.id)]):
        return await send_embed(ctx, "Mute role deleted in this server.", negative=True)


async def invalid_time(ctx, minutes):
    if minutes > 525600 or (minutes < 1 and minutes != -1):
        return await send_embed(ctx, "Number of minutes to mute must be between 1 and 525600, inclusive.",
                                negative=True)


async def insufficient_permissions(ctx, member):
    if member == ctx.guild.owner:
        return await send_embed(ctx, "Insufficient permission to perform that action on that member.", negative=True)
    if member.top_role.position >= ctx.author.top_role.position and ctx.author != ctx.guild.owner:
        return await send_embed(ctx, "Insufficient permission to perform that action on that member.", negative=True)
    if member.top_role.position >= ctx.guild.me.top_role.position:
        return await send_embed(ctx, "Bot has insufficient permission to perform that action on that member.",
                                negative=True)


async def sql_write(ctx, member: discord.Member, minutes, mute=False, ban=False):
    if mute:
        await db.execute("Insert into Timestamps values (?, ?, ?, ?)",
                         (ctx.guild.id, member.id, time.time() + minutes, None))
        await db.commit()

        for role in member.roles:
            await db.execute("Insert into TimestampsRoles values (?, ?, ?)", (ctx.guild.id, member.id, role.id))
            await db.commit()

    elif ban:
        await db.execute("Insert into Timestamps values (?, ?, ?, ?)",
                         (ctx.guild.id, member.id, None, time.time() + minutes))
        await db.commit()


async def write_infractions(ctx, member: discord.Member, type: str, minutes: float = None, reason: str = None):
    current_time = datetime.now().strftime('%m/%d/%Y, %H:%M:%S')

    await db.execute("Insert into Infractions values (?, ?, ?, ?, ?, ?, ?, "
                     "(Select count(Type) from Infractions where GuildID = ? and MemberID = ?) + 1)",
                     (ctx.guild.id, member.id, type, reason, current_time, ctx.author.id, minutes, ctx.guild.id,
                      member.id))
    await db.commit()


async def action_message_send(minutes, ctx, member, action: str):
    if minutes == -1:
        await send_embed(ctx, f"{member.mention} was permanently {action}.")
    else:
        await send_embed(ctx, f"{member.mention} was {action} for {minutes} minutes.")


class Mod(commands.Cog, name="Moderator"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.check_time.start()

    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def selfmute(self, ctx, minutes: float = 15):
        """Mute yourself for x amount of minutes."""

        if await no_mute_role(ctx, self.bot):
            return

        if minutes < 1 or minutes > 1440:
            return await send_embed(ctx, "Invalid number of minutes; must be between 1 and 1440, inclusive",
                                    negative=True)

        muterole = ctx.guild.get_role(self.bot.muteroles[str(ctx.guild.id)])
        roles = ctx.author.roles
        roles.append(muterole)
        await ctx.author.edit(roles=roles)

        await sql_write(ctx, ctx.author, minutes, mute=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command(description="Create a mute role with the bot. Its permissions will deny members from sending "
                                  "messages in any channel.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def createmuterole(self, ctx):
        """Create mute role."""

        if str(ctx.guild.id) in self.bot.muteroles.keys():

            if ctx.guild.get_role(self.bot.muteroles[str(ctx.guild.id)]):
                return await send_embed(ctx, "A mute role has already been assigned to your server.",
                                        negative=True)

            else:
                del self.bot.muteroles[str(ctx.guild.id)]

        try:
            muterole = await ctx.guild.create_role(name="Muted")

            for channel in ctx.guild.channels:
                await channel.set_permissions(muterole, send_messages=False)

            self.bot.muteroles[str(ctx.guild.id)] = muterole.id

            with open("muterole.json", "w") as file:
                json.dump(self.bot.muteroles, file, indent=4)

            await send_embed(ctx, f"Mute role successfully created, "
                                  f"with permission overwrites for "
                                  f"{str(len(ctx.guild.text_channels))} text channels, "
                                  f"{str(len(ctx.guild.voice_channels))} voice channels, and "
                                  f"{str(len(ctx.guild.categories))} categories.")

        except Exception as e:
            await ctx.send(e)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command(description="Set/update a mute role. This function takes in either a role or role ID object for "
                                  "the argument, but not both.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def setmuterole(self, ctx, role: discord.Role):
        """Set mute role."""

        async def smr():
            try:

                self.bot.muteroles[str(ctx.guild.id)] = role.id
                with open("muterole.json", "w") as file:
                    json.dump(self.bot.muteroles, file, indent=4)

                await ctx.send("Mute role successfully set!")

            except Exception as e:
                await send_embed(ctx, str(e), negative=True)

        if role.position > discord.utils.get(ctx.guild.me.roles, managed=True).position:

            await send_embed(ctx, "I do not have permission to set this as the mute role "
                                  "because it is above me in the hierarchy. Move it below my "
                                  "role if you want to set it as the mute role.",
                             negative=True)

        else:
            await smr()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command(description="Mute a member. Give the time in minutes as an integer; do -1 to mute permanently.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, minutes: float = 15, *, reason: str = None):
        """Mute a member. Put -1 for minutes to permanently mute."""

        if await insufficient_permissions(ctx, member):
            return

        if member.guild_permissions.manage_roles or member.guild_permissions.administrator:
            return await send_embed(ctx, "Target member permissions too high to mute.", negative=True)

        if await invalid_time(ctx, minutes):
            return

        if await no_mute_role(ctx, self.bot):
            return

        mute_role = ctx.guild.get_role(self.bot.muteroles[str(ctx.guild.id)])

        if mute_role in member.roles:
            return await send_embed(ctx, "Member already muted.", negative=True)

        await sql_write(ctx, member, minutes, mute=True)

        await write_infractions(ctx, member, "Mute", minutes, reason)

        await member.edit(roles=[mute_role])

        await action_message_send(minutes, ctx, member, "muted")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(ban_members=True)
    @commands.command(description="Ban a member. Put the time banned in minutes. Defaults to permanently.")
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: typing.Union[discord.Member, int], minutes: float = -1, *,
                  reason: str = None):
        """Ban a member. -1 for permanent."""

        if isinstance(member, int):
            try:
                member = discord.Object(id=member)

            except Exception as e:
                return await send_embed(ctx, str(e), negative=True)

        if await insufficient_permissions(ctx, member):
            return

        if await invalid_time(ctx, minutes):
            return

        try:
            await ctx.guild.fetch_ban(member)
            return await send_embed(ctx, "Member already banned.", negative=True)

        except Exception:
            pass

        await write_infractions(ctx, member, "Ban", minutes, reason)

        await ctx.guild.ban(member, reason=reason)
        await action_message_send(minutes, ctx, member, "banned")
        await sql_write(ctx, member, minutes, ban=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command(description="Unmute a member.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = None):
        """Unmutes a member."""

        if await no_mute_role(ctx, self.bot):
            return

        mute_role = ctx.guild.get_role(self.bot.muteroles[str(ctx.guild.id)])

        if not (mute_role in member.roles):
            return await send_embed(ctx, f"{str(member)} is not muted.", negative=True)

        cursor = await db.execute("select Roles from Timestamps where GuildID = ? and MemberID = ?", (ctx.guild.id,
                                                                                                      member.id))

        result = await cursor.fetchone()

        try:
            await write_infractions(ctx, member, "Unmute", reason=reason)

            await member.edit(roles=[ctx.guild.get_role(roleID) for roleID in json.loads(result[0])
                                     if ctx.guild.get_role(roleID)])

            await send_embed(ctx, f"{str(member)} was unmuted.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(ban_members=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, member: typing.Union[discord.Member, int], *, reason: str = None):
        """Unban a member. You must use a member ID to do this."""

        if isinstance(member, discord.Member):
            return await send_embed(ctx, "Member is not currently banned.", negative=True)

        try:
            m = discord.Object(id=member)

            await write_infractions(ctx, m, "Unban", reason=reason)

            await ctx.guild.unban(m, reason=reason)
            await send_embed(ctx, f"Unbanned member with ID ``{m.id}``")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(kick_members=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kick a member."""

        if await insufficient_permissions(ctx, member):
            return

        try:
            await ctx.guild.kick(member, reason=reason)

            await write_infractions(ctx, member, "Kick", reason=None)

            await send_embed(ctx, f"{member.mention} was kicked.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_nicknames=True)
    @commands.command(aliases=["nickname"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, name: str = None):
        """Nick a member. The author must have sufficient permissions over the target member to do so."""

        if await insufficient_permissions(ctx, member):
            return

        try:
            await member.edit(nickname=name)
            if name:
                await send_embed(ctx, f"Changed {str(member)}'s nickname to {name}")
            else:
                await send_embed(ctx, f"Reset {str(member)}'s nickname.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @tasks.loop(seconds=30)
    async def check_time(self):
        """Loops through the DB every 30 seconds to unmute/unban members when their time is up"""

        await self.bot.wait_until_ready()

        # Do mute AND ban members, do mute first
        cursor = await db.execute("Select GuildID, MemberID from Timestamps where Timeunbanned <= ? "
                                  "and Timeunbanned != -1", (time.time(),))
        result = await cursor.fetchall()

        for guild_id, member_id in result:
            guild = self.bot.get_guild(guild_id)
            if not guild or guild.unavailable:
                continue

            member = discord.Object(member_id)
            try:
                await guild.unban(member)
            except discord.Forbidden:
                continue

        cursor = await db.execute("Select GuildID, MemberID from Timestamps "
                                  "inner join TimestampsRoles on TimestampsRoles.RoleGuildID = Timestamps.GuildID "
                                  "and TimestampsRoles.RoleMemberID = Timestamps.MemberID "
                                  "where Timeunmuted <= ? "
                                  "and Timeunmuted != -1 ", (time.time(),))
        result = await cursor.fetchall()

        if not result:
            return

        a, b = result[0][0], result[0][1]

        roles = []

        for i, tup in enumerate(result):

            guild_id = tup[0]
            member_id = tup[1]
            try:
                role_id = tup[2]
            except IndexError:
                role_id = None

            if not self.bot.get_guild(guild_id) or self.bot.get_guild(guild_id).unavailable:
                continue

            if (a != guild_id and b != member_id) or i == len(result)-1:
                try:
                    member = self.bot.get_guild(a).get_member(b)
                    await member.edit(roles=roles)
                except AttributeError:
                    pass
                except discord.Forbidden:
                    try:
                        await member.edit(roles=[])
                    except discord.Forbidden:
                        pass

                a, b = guild_id, member_id
                roles = []

            else:
                if not self.bot.get_guild(guild_id).get_role(role_id):
                    continue
                roles.append(self.bot.get_guild(a).get_role(role_id))

    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    @commands.has_permissions(manage_channels=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke(self, ctx, channel: discord.TextChannel = None):
        """Nuke a channel. Aka delete all its messages."""

        if not channel:
            channel = ctx.channel
        cloned_channel = await channel.clone()
        await channel.delete()
        await cloned_channel.send(embed=await to_embed("Channel nuked."))

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.has_permissions(manage_messages=True)
    @commands.command(aliases=["clear"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def prune(self, ctx, limit: int):
        """Prune some number of messages."""

        if limit == 0 or limit > 99:
            return await send_embed(ctx, "Invalid number of messages to prune.", negative=True)

        await ctx.channel.purge(limit=limit + 1)

        embed = discord.Embed(
            colour=discord.Colour.green(),
            description=f"✅ ***{limit} messages deleted.***"
        )

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        await msg.delete()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(aliases=["findmember"])
    @commands.guild_only()
    async def searchmember(self, ctx, memberID: int):
        """Search for a member by their ID in the server. Anyone can use this :)"""

        try:
            await send_embed(ctx, f"Found member: {ctx.guild.get_member(memberID).mention}")

        except:
            await send_embed(ctx, "Failed to find member.", negative=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_messages=True)
    @commands.command(aliases=["deletereactions"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clearreactions(self, ctx, message: discord.Message):
        """Clear all of a message's reactions. Use its ID as the argument."""

        try:
            await message.clear_reactions()

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.has_permissions(manage_channels=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock down a channel to all roles that do not have manage_channels permissions."""

        if not channel:
            channel = ctx.channel

        cursor = await db.execute("Select ChannelID from Lock where ChannelID = ?", (channel.id,))
        result = await cursor.fetchone()

        if result:
            return await send_embed(ctx, "Channel already locked.", negative=True)

        for role in ctx.guild.roles:
            # No clue how this works, but it works

            if not role.permissions.manage_channels and not role.permissions.administrator:

                if channel.overwrites_for(role).is_empty():
                    if role.permissions.send_messages:
                        await db.execute("Insert into Lock values (?, ?)", (channel.id, role.id))
                        await db.commit()

                else:
                    # I needed to check deny for first case, allow second. Realized way too late.
                    if role.permissions.send_messages:
                        if channel.overwrites_for(role).pair()[1].send_messages:  # = False
                            await db.execute("Insert into Lock values (?, ?)", (channel.id, role.id))
                            await db.commit()

                    else:  # If they can't send messages guild wide, then perm needs to be allow
                        if channel.overwrites_for(role).pair()[0].send_messages:
                            await db.execute("Insert into Lock values (?, ?)", (channel.id, role.id))
                            await db.commit()

                await channel.set_permissions(role, send_messages=False)

        await send_embed(ctx, "Channel locked.")

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.has_permissions(manage_channels=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a channel."""

        if not channel:
            channel = ctx.channel

        cursor = await db.execute("Select RoleID from Lock where ChannelID = ?", (channel.id,))
        result = await cursor.fetchall()

        if not result:
            return await send_embed(ctx, "Channel is not on lockdown.", negative=True)

        for id in (i[0] for i in result):
            try:
                await channel.set_permissions(ctx.guild.get_role(id), send_messages=True)
            except:
                # This is if the role was deleted in the guild, or bot doesn't have permission, etc
                pass

        await db.execute("Delete from Lock where ChannelID = ?", (channel.id,))
        await db.commit()

        await send_embed(ctx, "Channel unlocked.")

    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    @commands.has_permissions(manage_channels=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    async def lockall(self, ctx):
        """Locks down all channels for members without manage_channels permissions."""

        statement = """If (Select count(*) from Lock where ChannelID = ?) == 0 
                       Begin 
                        Insert into Lock values (?, ?) 
                       End"""

        for channel in ctx.guild.text_channels:

            for role in ctx.guild.roles:

                if not role.permissions.manage_channels and not role.permissions.administrator:

                    if channel.overwrites_for(role).is_empty():
                        if role.permissions.send_messages:
                            await db.execute(statement, (channel.id, channel.id, role.id))
                            await db.commit()

                    else:
                        # I needed to check deny for first case, allow second. Realized way too late.
                        if role.permissions.send_messages:
                            if channel.overwrites_for(role).pair()[1].send_messages:  # = False
                                await db.execute(statement, (channel.id, channel.id, role.id))
                                await db.commit()

                        else:  # If they can't send messages guild wide, then perm needs to be allow
                            if channel.overwrites_for(role).pair()[0].send_messages:
                                await db.execute(statement, (channel.id, channel.id, role.id))
                                await db.commit()

                    await channel.set_permissions(role, send_messages=False)

        await send_embed(ctx, "Locked down the server.")

    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    @commands.has_permissions(manage_channels=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    async def unlockall(self, ctx):
        """Unlock all channels."""

        islocked = False

        for channel in ctx.guild.text_channels:
            cursor = await db.execute("Select Role from Lock where ChannelID = ?", (channel.id,))
            result = await cursor.fetchall()

            if result:
                islocked = True

                for role_id in result:
                    try:
                        await channel.set_permissions(ctx.guild.get_role(role_id), send_messages=True)
                    except:
                        pass

            await db.execute("Delete from Lock where ChannelID = ?", (channel.id,))
            await db.commit()

        if not islocked:
            return await send_embed(ctx, "No channels are locked.", negative=True)
        await send_embed(ctx, "Unlocked the server.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(ban_members=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = None):
        """Instantly bans and unbans the member to delete all messages."""

        if await insufficient_permissions(ctx, member):
            return

        await ctx.guild.ban(member, reason=reason, delete_message_days=7)
        await ctx.guild.unban(member, reason=reason)

        await write_infractions(ctx, member, "Softban", reason=reason)

        await send_embed(ctx, "Member softbanned.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command()
    @commands.guild_only()
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member."""

        if await insufficient_permissions(ctx, member):
            return

        await write_infractions(ctx, member, "Warn", reason=reason)

        await send_embed(ctx, f"Warned {member.mention}.")
