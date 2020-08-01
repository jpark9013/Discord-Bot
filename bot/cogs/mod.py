import asyncio
import json
import sqlite3
import time
import typing
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot.utils.message import to_embed, send_embed


async def no_mute_role(ctx):
    with open("muterole.json", "r") as f:
        dict = json.load(f)
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


async def sql_write(ctx, id, minutes, db, mute=False, ban=False):
    if minutes == -1:
        return

    cursor = await db.execute("Select count(*) from Timestamps where GuildID = ? and MemberID = ?", (ctx.guild.id, id))
    result = await cursor.fetchone()

    if result[0]:
        if mute:
            await db.execute("Update Timestamps set Timeunmuted = ? where GuildID = ? and MemberID = ?",
                             (time.time() + minutes * 60, ctx.guild.id, id))
            await db.commit()

    else:
        if mute:
            roles = [i.id for i in ctx.guild.get_member(id).roles]
            await db.execute("Insert into Timestamps values (?, ?, ?, ?, ?)",
                             (ctx.guild.id, id, time.time() + minutes, None, json.dumps(roles)))
            await db.commit()

        elif ban:
            await db.execute("Insert into Timestamps values (?, ?, ?, ?, ?)",
                             (ctx.guild.id, id, None, time.time() + minutes, None))


async def get_infractions(ctx, member, db):
    cursor = await db.execute("Select Infractions from Infractions where GuildID = ? and MemberID = ?",
                              (ctx.guild.id, member.id))
    result = await cursor.fetchone()
    if not result:
        return []
    return json.loads(result[0])


async def write_infractions(ctx, memberID, db, infractions):
    cursor = await db.execute("Select count(*) from Infractions where GuildID = ? and MemberID = ?",
                              (ctx.guild.id, memberID))
    result = await cursor.fetchone()

    if not result[0]:
        await db.execute("Insert into Infractions values (?, ?, ?)", (ctx.guild.id, memberID, infractions))
        await db.commit()
    else:
        await db.execute("Update Infractions set Infractions = ? where GuildID = ? and MemberID = ?",
                         (infractions, ctx.guild.id, memberID))
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

        if await no_mute_role(ctx):
            return

        if minutes < 1 or minutes > 1440:
            return await send_embed(ctx, "Invalid number of minutes; must be between 1 and 1440, inclusive",
                                    negative=True)

        with open("muterole.json", "r") as f:
            dict = json.load(f)

        muterole = ctx.guild.get_role(dict[str(ctx.guild.id)])
        roles = ctx.author.roles
        roles.append(muterole)
        await ctx.author.edit(roles=roles)

        await sql_write(ctx, ctx.author.id, minutes, db, mute=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command(description="Create a mute role with the bot. Its permissions will deny members from sending "
                                  "messages in any channel.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def createmuterole(self, ctx):
        """Create mute role."""

        with open("muterole.json", "r") as file:
            rolesDict = json.load(file)

        if str(ctx.guild.id) in rolesDict.keys():

            if ctx.guild.get_role(rolesDict[str(ctx.guild.id)]):
                return await send_embed(ctx, "A mute role has already been assigned to your server.",
                                        negative=True)

        try:
            muterole = await ctx.guild.create_role(name="Muted")

            for channel in ctx.guild.channels:
                await channel.set_permissions(muterole, send_messages=False)

            rolesDict[str(ctx.guild.id)] = muterole.id

            with open("muterole.json", "w") as file:
                json.dump(rolesDict, file, indent=4)

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

                rolesDict[str(ctx.guild.id)] = role.id
                with open("muterole.json", "w") as file:
                    json.dump(rolesDict, file, indent=4)

                await ctx.send("Mute role successfully set!")

            except Exception as e:
                await send_embed(ctx, str(e), negative=True)

        with open("muterole.json", "r") as file:
            rolesDict = json.load(file)

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

        with open("muterole.json", "r") as file:
            rolesDict = json.load(file)

        if await no_mute_role(ctx):
            return

        mute_role = ctx.guild.get_role(rolesDict[str(ctx.guild.id)])

        if mute_role in member.roles:
            return await send_embed(ctx, "Member already muted.", negative=True)

        await sql_write(ctx, member.id, minutes, db, mute=True)

        infractions = await get_infractions(ctx, member, db)
        infractions.append(["Mute", reason, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), ctx.author.id, minutes])
        await write_infractions(ctx, member.id, db, json.dumps(infractions))

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

        infractions = await get_infractions(ctx, member, db)
        infractions.append(["Ban", reason, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), ctx.author.id, minutes])
        await write_infractions(ctx, member.id, db, json.dumps(infractions))

        await ctx.guild.ban(member, reason=reason)
        await action_message_send(minutes, ctx, member, "banned")
        await sql_write(ctx, member.id, minutes, db, ban=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command(description="Unmute a member.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = None):
        """Unmutes a member."""

        with open("muterole.json", "r") as file:
            rolesDict = json.load(file)

        if await no_mute_role(ctx):
            return

        mute_role = ctx.guild.get_role(rolesDict[str(ctx.guild.id)])

        if not (mute_role in member.roles):
            return await send_embed(ctx, f"{str(member)} is not muted.", negative=True)

        cursor = await db.execute("select Roles from Timestamps where GuildID = ? and MemberID = ?", (ctx.guild.id,
                                                                                                      member.id))

        result = await cursor.fetchone()

        try:
            infractions = await get_infractions(ctx, member, db)
            infractions.append(["Unmute", reason, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), ctx.author.id])
            await write_infractions(ctx, member.id, db, json.dumps(infractions))

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

            infractions = await get_infractions(ctx, m, db)
            infractions.append(["Unban", reason, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), ctx.author.id])
            await write_infractions(ctx, m.id, db, json.dumps(infractions))

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

            infractions = await get_infractions(ctx, member, db)
            infractions.append(["Kick", reason, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), ctx.author.id])
            await write_infractions(ctx, member.id, db, json.dumps(infractions))

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

        cursor = await db.execute("select GuildID, MemberID, Roles from Timestamps "
                                  "where Timeunmuted <= ?", (time.time(),))
        # Checking muted members first

        result = await cursor.fetchall()
        for row in result:
            roles_to_add = []

            try:
                guild = self.bot.get_guild(row[0])

                for roleID in json.loads(row[2]):
                    try:
                        roles_to_add.append(guild.get_role(roleID))
                    except:
                        pass

                await guild.get_member(row[1]).edit(roles=roles_to_add)

            except:
                pass

        try:
            await db.execute("delete from Timestamps where Timeunmuted <= ?", (time.time(),))
            await db.commit()
        except sqlite3.OperationalError:
            pass
        except sqlite3.DatabaseError:
            pass

        cursor = await db.execute("select GuildID, MemberID from Timestamps where Timeunbanned <= ?",
                                  (time.time(),))

        # Here checking banned members

        result = await cursor.fetchall()

        for row in result:
            try:
                await self.bot.get_guild(row[0]).unban(discord.Object(id=row[1]))

            except:
                pass

        try:
            await db.execute("delete from Timestamps where (Timeunbanned <= ? and Timeunbanned != 0)",
                             (time.time(),))
            await db.commit()

        except sqlite3.OperationalError:
            pass
        except sqlite3.DatabaseError:
            pass

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

        await ctx.channel.purge(limit=limit+1)

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

        roles = []

        for role in ctx.guild.roles:
            # No clue how this works, but it works

            if not role.permissions.manage_channels and not role.permissions.administrator:
                await channel.set_permissions(role, send_messages=False)

                if channel.overwrites_for(role).is_empty():
                    if role.permissions.send_messages:
                        roles.append(role.id)

                else:
                    # I needed to check deny for first case, allow second. Realized way too late.
                    if role.permissions.send_messages:
                        if channel.overwrites_for(role).pair()[1].send_messages:  # = False
                            roles.append(role.id)

                    else:  # If they can't send messages guild wide, then perm needs to be allow
                        if channel.overwrites_for(role).pair()[0].send_messages:
                            roles.append(role.id)

        await db.execute("Insert into Lock values (?, ?)", (channel.id, json.dumps(roles)))
        await db.commit()

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

        cursor = await db.execute("Select ChannelID, Roles from Lock where ChannelID = ?", (channel.id,))
        result = await cursor.fetchone()

        if not result:
            return await send_embed(ctx, "Channel is not on lockdown.", negative=True)

        roles = json.loads(result[1])

        for id in roles:
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

        for channel in ctx.guild.text_channels:
            roles = []

            for role in ctx.guild.roles:

                if not role.permissions.manage_channels and not role.permissions.administrator:
                    await channel.set_permissions(role, send_messages=False)

                    if channel.overwrites_for(role).is_empty():
                        if role.permissions.send_messages:
                            roles.append(role.id)

                    else:
                        # I needed to check deny for first case, allow second. Realized way too late.
                        if role.permissions.send_messages:
                            if channel.overwrites_for(role).pair()[1].send_messages:  # = False
                                roles.append(role.id)

                        else:  # If they can't send messages guild wide, then perm needs to be allow
                            if channel.overwrites_for(role).pair()[0].send_messages:
                                roles.append(role.id)

            roles = json.dumps(roles)

            cursor = await db.execute("select ChannelID from Lock where ChannelID = ?", (channel.id,))
            result = await cursor.fetchone()

            if result:
                await db.execute("update Lock "
                                 "set Roles = ? "
                                 "where ChannelID = ?", (roles, channel.id))
                await db.commit()

            else:
                await db.execute("insert into Lock values (?, ?)", (channel.id, roles))
                await db.commit()

        await send_embed(ctx, "Locked down the server.")

    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    @commands.has_permissions(manage_channels=True)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    async def unlockall(self, ctx):
        """Unlock all channels."""

        for channel in ctx.guild.text_channels:
            cursor = await db.execute("Select Roles from Lock where ChannelID = ?", (channel.id,))
            result = await cursor.fetchone()

            if result:
                roles = json.loads(result[0])

                for id in roles:
                    try:
                        await channel.set_permissions(ctx.guild.get_role(id), send_messages=True)
                    except:
                        pass

            await db.execute("Delete from Lock where ChannelID = ?", (channel.id,))
            await db.commit()

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

        try:
            await ctx.guild.ban(member, reason=reason, delete_message_days=7)
            await ctx.guild.unban(member, reason=reason)

            infractions = await get_infractions(ctx, member, db)
            infractions.append(["Softban", reason, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), ctx.author.id])
            await write_infractions(ctx, member.id, db, json.dumps(infractions))

            await send_embed(ctx, "Member softbanned.")

        except Exception as e:
            await send_embed(ctx, str(e), negative=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    @commands.command()
    @commands.guild_only()
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member."""

        if await insufficient_permissions(ctx, member):
            return

        infractions = await get_infractions(ctx, member, db)
        infractions.append(["Warn", reason, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), ctx.author.id])
        await write_infractions(ctx, member.id, db, json.dumps(infractions))

        await send_embed(ctx, f"Warned {member.mention}.")

    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @commands.command(aliases=["infractions"])
    @commands.guild_only()
    async def modlogs(self, ctx, member: discord.Member):
        """Show the modlogs for a member."""

        infractions = await get_infractions(ctx, member, db)

        if not infractions:
            return await send_embed(ctx, f"Did not find any modlogs for {member.mention}.", negative=True)

        embed = discord.Embed(color=discord.Colour.blue())
        embed.set_author(name=str(member), icon_url=str(member.avatar_url))

        for infraction in infractions:
            moderator = self.bot.get_user(infraction[3]) or await self.bot.fetch_member(infraction[3])

            if infraction[0].lower() in ["warn", "kick", "softban", "unban", "unmute"]:

                embed.add_field(name=f"Case {infractions.index(infraction) + 1}",
                                value=f"**Type:** {infraction[0]}\n"
                                      f"**User:** ({member.id}) {str(member)}\n"
                                      f"**Moderator:** {str(moderator)}\n"
                                      f"**Reason:** {infraction[1]}\n"
                                      f"**Timestamp:** {infraction[2]}", inline=False)

            else:

                if infraction[4] == -1:
                    infraction[4] = "Forever"

                else:
                    days, remainder = divmod(infraction[4], 1440)
                    hours, minutes = divmod(remainder, 60)

                    if days == 0:
                        infraction[4] = f"{hours}h {minutes}m"
                    else:
                        infraction[4] = f"{days}d {hours}h {minutes}m"

                embed.add_field(name=f"Case {infractions.index(infraction) + 1}",
                                value=f"**Type:** {infraction[0]}\n"
                                      f"**User:** ({member.id}) {str(member)}\n"
                                      f"**Moderator:** {str(moderator)}\n"
                                      f"**Reason:** {infraction[1]}\n"
                                      f"**Timestamp:** {infraction[2]}\n"
                                      f"**Time:** {infraction[4]}", inline=False)

        await ctx.send(embed=embed)


