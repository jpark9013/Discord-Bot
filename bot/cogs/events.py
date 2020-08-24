import json
import time
from datetime import datetime

import discord
from discord.ext import commands


async def is_logging(GuildID: int, column: str, db, ChannelID: int = None):
    cursor = await db.execute(f"Select {column}, Enabled from Logging where GuildID = ? ", (GuildID,))
    result = await cursor.fetchone()

    if not result:
        return False

    if not result[0] or not result[1]:
        return False

    if ChannelID:
        cursor = await db.execute("Select IgnoredChannelID from LoggingIgnoredChannels where GuildID = ?", (GuildID,))
        result = await cursor.fetchall()

        ignoredchannels = [i[1] for i in result]
        return not (ChannelID in ignoredchannels)

    return True


async def send(bot, GuildID: int, embed: discord.Embed, db):
    cursor = await db.execute("Select ChannelID from Logging where GuildID = ?", (GuildID,))
    result = await cursor.fetchone()

    try:
        await bot.get_guild(GuildID).get_channel(result[0]).send(embed=embed)
    except:  # Channel deleted, Guild deleted, bot not given permission to send, etc etc.
        pass


async def is_showicon(GuildID: int, db):
    cursor = await db.execute("Select ShowIcon from Logging where GuildID = ?", (GuildID,))
    result = await cursor.fetchone()

    return result[0]


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Mute Role check
        cursor = await db.execute("Select Timeunmuted from Timestamps where MemberID = ? and GuildID = ?",
                                  (member.id, member.guild.id))
        result = await cursor.fetchone()

        if result:
            if result[0] > time.time():
                try:
                    roleID = self.bot.muteroles[str(member.guild.id)]
                    await member.edit(roles=[member.guild.get_role(roleID)])
                except:  # Role deleted, no permission, etc.
                    pass

        cursor = await db.execute("Select JoinMessage, JoinMessageChannel from JLMessage where GuildID = ?",
                                  (member.guild.id,))
        result = await cursor.fetchone()

        try:
            # Check if result exists
            a = result[0]
            a = result[1]
            channel = self.bot.get_guild(member.guild.id).get_channel(result[1])

            embed = discord.Embed(
                colour=discord.Colour.green(),
                title="Member Joined",
                description=result[0]
            )
            embed.set_author(name=str(member), icon_url=str(member.avatar_url))

            await channel.send(embed=embed)

        except:
            pass

        if await is_logging(member.guild.id, "MemberJoined", db):

            icon_url = str(member.avatar_url)

            embed = discord.Embed(
                colour=discord.Colour.green(),
                description=f"{member.mention} {str(member)}"
            )

            if await is_showicon(member.guild.id, db):
                embed.set_thumbnail(url=icon_url)
            embed.set_author(name="Member Joined", icon_url=icon_url)
            embed.set_footer(text=f"ID: {member.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, member.guild.id, embed, db)

        if not member.bot:
            cursor = await db.execute("Select RoleID from RoleOnJoin where GuildID = ?", (member.guild.id,))
            result = await cursor.fetchall()

            if result:
                # Check if they have muted role
                roles = member.roles

                for tup in result:
                    if member.guild.get_role(tup[0]):
                        roles.append(member.guild.get_role(tup[0]))

                try:
                    await member.edit(roles=list(set(roles)))
                except:
                    return

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        cursor = await db.execute("Select LeaveMessage, LeaveMessageChannel from JLMessage where GuildID = ?",
                                  (member.guild.id,))
        result = await cursor.fetchone()

        try:
            a = result[0]
            a = result[1]
            channel = self.bot.get_guild(member.guild.id).get_channel(result[1])

            embed = discord.Embed(
                colour=discord.Colour.green(),
                title="Member Left",
                description=result[0]
            )
            embed.set_author(name=str(member), icon_url=str(member.avatar_url))

            await channel.send(embed=embed)

        except:
            pass

        if await is_logging(member.guild.id, "MemberLeft", db):
            icon_url = str(member.avatar_url)

            embed = discord.Embed(
                colour=discord.Colour.red(),
                description=f"{member.mention} {str(member)}"
            )

            if await is_showicon(member.guild.id, db):
                embed.set_thumbnail(url=icon_url)
            embed.set_author(name="Member Left", icon_url=icon_url)
            embed.set_footer(text=f"ID: {member.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, member.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        if await is_logging(guild.id, "MemberBanned", db):
            icon_url = str(member.avatar_url)

            embed = discord.Embed(
                colour=discord.Colour.red(),
                description=f"{member.mention} {str(member)}"
            )

            if await is_showicon(guild.id, db):
                embed.set_thumbnail(url=icon_url)
            embed.set_author(name="Member Banned", icon_url=icon_url)
            embed.set_footer(text=f"ID: {member.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, guild.id, embed, db)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, member):
        if await is_logging(guild.id, "MemberUnbanned", db):
            icon_url = str(member.avatar_url)

            embed = discord.Embed(
                colour=discord.Colour.green(),
                description=f"{member.mention} {str(member)}"
            )

            if await is_showicon(guild.id, db):
                embed.set_thumbnail(url=icon_url)
            embed.set_author(name="Member Unbanned", icon_url=icon_url)
            embed.set_footer(text=f"ID: {member.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, guild.id, embed, db)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not after.guild:
            return

        if await is_logging(after.guild.id, "MessageEdited", db):
            if before.content != after.content:
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    description=f"**Message edited in** <#{after.channel.id}> [Jump to message]({after.jump_url})"
                )

                if await is_showicon(after.guild.id, db):
                    embed.set_thumbnail(url=str(after.author.avatar_url))

                embed.set_author(name=str(after.author), icon_url=str(after.author.avatar_url))

                embed.add_field(name="Before", value=before.content, inline=False)
                embed.add_field(name="After", value=after.content, inline=False)
                embed.set_footer(text=f"ID: {after.author.id}\n"
                                      f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

                await send(self.bot, after.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild:
            return

        if await is_logging(message.guild.id, "MessageEdited", db):
            embed = discord.Embed(
                colour=discord.Colour.red(),
                description=f"**Message sent by {message.author.mention} deleted in <#{message.channel.id}>:**\n"
                            f"{message.content}"
            )

            if await is_showicon(message.guild.id, db):
                embed.set_thumbnail(url=str(message.author.avatar_url))

            embed.set_author(name=str(message.author), icon_url=str(message.author.avatar_url))
            embed.set_footer(text=f"ID: {message.author.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, message.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages[0].guild:
            return

        if await is_logging(messages[0].guild.id, "BulkMessageDeletion", db):
            embed = discord.Embed(
                colour=discord.Colour.red(),
                description=f"**Bulk delete in <#{messages[0].channel.id}>; {len(messages)} messages deleted.**"
            )

            if await is_showicon(messages[0].guild.id, db):
                embed.set_thumbnail(url=str(messages[0].guild.icon_url))

            embed.set_author(name=str(messages[0].guild.name), icon_url=str(messages[0].guild.icon_url))
            embed.set_footer(text=f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, messages[0].guild.id, embed, db)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if await is_logging(channel.guild.id, "ChannelCreated", db):
            embed = discord.Embed(
                colour=discord.Colour.green(),
                description=f"**Channel <#{channel.id}> created.**"
            )

            if await is_showicon(channel.guild.id, db):
                embed.set_thumbnail(url=str(channel.guild.icon_url))

            embed.set_author(name=channel.guild.name, icon_url=str(channel.guild.icon_url))
            embed.set_footer(text=f"ID: {channel.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, channel.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if await is_logging(channel.guild.id, "ChannelDeleted", db):
            embed = discord.Embed(
                colour=discord.Colour.red(),
                description=f"**Channel #{channel.name} deleted.**"
            )

            if await is_showicon(channel.guild.id, db):
                embed.set_thumbnail(url=str(channel.guild.icon_url))

            embed.set_author(name=channel.guild.name, icon_url=str(channel.guild.icon_url))
            embed.set_footer(text=f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, channel.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if await is_logging(role.guild.id, "RoleCreated", db):
            embed = discord.Embed(
                colour=discord.Colour.green(),
                description=f"**Role ``{role.name}`` created.**"
            )

            if await is_showicon(role.guild.id, db):
                embed.set_thumbnail(url=str(role.guild.icon_url))

            embed.set_author(name=role.guild.name, icon_url=str(role.guild.icon_url))
            embed.set_footer(text=f"ID: {role.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, role.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if await is_logging(role.guild.id, "RoleDeleted", db):
            embed = discord.Embed(
                colour=discord.Colour.red(),
                description=f"**Role ``{role.name}`` deleted.**"
            )

            if await is_showicon(role.guild.id, db):
                embed.set_thumbnail(url=str(role.guild.icon_url))

            embed.set_author(name=role.guild.name, icon_url=str(role.guild.icon_url))
            embed.set_footer(text=f"ID: {role.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, role.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if await is_logging(after.guild.id, "RoleUpdated", db):
            embed = discord.Embed(
                colour=discord.Colour.blue(),
                description=f"**Role ``{after.name}`` updated.**"
            )

            if await is_showicon(after.guild.id, db):
                embed.set_thumbnail(url=str(after.guild.icon_url))

            embed.set_author(name=after.guild.name, icon_url=str(after.guild.icon_url))
            embed.set_footer(text=f"ID: {after.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, after.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if len(before.roles) > len(after.roles):
            a = set(before.roles)
            b = set(after.roles)
            c = a - b
            try:
                muterole = self.bot.muteroles[str(after.guild.id)]
            except KeyError:
                muterole = None
            except AttributeError:
                muterole = None

            if muterole == c:
                await db.execute("Delete from Timestamps where GuildID = ? and MemberID = ?",
                                 (before.guild.id, before.id))
                await db.commit()
                await db.execute("Delete from TimestampsRoles where RoleGuildID = ? and RoleMemberID = ?",
                                 (before.guild.id, before.id))
                await db.commit()

        if before.display_name != after.display_name and before.roles != after.roles:
            if await is_logging(after.guild.id, "RoleGiven", db) and await is_logging(after.guild.id, "RoleRemoved", db) \
                    and await is_logging(after.guild.id, "NicknameChanged", db):
                embed = discord.Embed(
                    colour=discord.Colour.blue()
                )

                if await is_showicon(after.guild.id, db):
                    embed.set_thumbnail(url=str(after.avatar_url))

                embed.set_author(name=str(after), icon_url=str(after.avatar_url))
                embed.add_field(name="Before Nick", value=f"{before.display_name}", inline=False)
                embed.add_field(name="After Nick", value=f"{after.display_name}", inline=False)

                for role in [role for role in before.roles + after.roles
                             if role not in before.roles or role not in after.roles]:
                    if role not in before.roles:
                        embed.add_field(name="Role added", value=f"``{role.name}``")
                    elif role not in after.roles:
                        embed.add_field(name="Role removed", value=f"``{role.name}``")

                embed.set_footer(text=f"ID: {after.id}\n"
                                      f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await send(self.bot, after.guild.id, embed, db)

        elif before.roles != after.roles:
            embed = discord.Embed(
                colour=discord.Colour.blue()
            )

            for role in [role for role in before.roles + after.roles
                         if role not in before.roles or role not in after.roles]:

                if role not in before.roles:
                    if await is_logging(after.guild.id, "RoleGiven", db):

                        if await is_showicon(after.guild.id, db):
                            embed.set_thumbnail(url=str(after.avatar_url))

                        embed.set_author(name=str(after), icon_url=str(after.avatar_url))

                        embed.add_field(name="Role added", value=f"``{role.name}``")

                        embed.set_footer(text=f"ID: {after.id}\n"
                                              f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

                elif role not in after.roles:
                    if await is_logging(after.guild.id, "RoleRemoved", db):

                        if await is_showicon(after.guild.id, db):
                            embed.set_thumbnail(url=str(after.avatar_url))

                        embed.set_author(name=str(after), icon_url=str(after.avatar_url))

                        embed.add_field(name="Role removed", value=f"``{role.name}``")

                        embed.set_footer(text=f"ID: {after.id}\n"
                                              f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

            if embed.fields:
                await send(self.bot, after.guild.id, embed, db)

        elif before.nick != after.nick:
            if await is_logging(after.guild.id, "NicknameChanged", db):
                embed = discord.Embed(
                    colour=discord.Colour.blue()
                )

                if await is_showicon(after.guild.id, db):
                    embed.set_thumbnail(url=str(after.avatar_url))

                embed.set_author(name=str(after), icon_url=str(after.avatar_url))
                embed.add_field(name="Before Nick", value=f"{before.display_name}", inline=False)
                embed.add_field(name="After Nick", value=f"{after.display_name}", inline=False)
                embed.set_footer(text=f"ID: {after.id}\n"
                                      f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await send(self.bot, after.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if not ctx.guild:
            return

        if await is_logging(ctx.guild.id, "ModeratorCommandUsed", db):
            if ctx.command.cog.qualified_name == "Mod":
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    description=f"**Used ``{ctx.command.name}`` command in <#{ctx.channel.id}>:**\n"
                                f"{ctx.message.content}"
                )

                if await is_showicon(ctx.guild.id, db):
                    embed.set_thumbnail(url=str(ctx.author.avatar_url))

                embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                embed.set_footer(text=f"ID: {ctx.author.id}\n"
                                      f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await send(self.bot, ctx.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Moved to VC
        if not before.channel and after.channel:
            if await is_logging(member.guild.id, "MemberJoinedVC", db):
                embed = discord.Embed(
                    colour=discord.Colour.green(),
                    description=f"**{member.mention} joined voice channel ``{after.channel.name}``.**"
                )

                if await is_showicon(member.guild.id, db):
                    embed.set_thumbnail(url=str(member.avatar_url))

                embed.set_author(name=str(member), icon_url=str(member.avatar_url))
                embed.set_footer(text=f"ID: {member.id}\n"
                                      f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await send(self.bot, member.guild.id, embed, db)

        # Left VC
        elif before.channel and not after.channel:
            if await is_logging(member.guild.id, "MemberLeftVC", db):
                embed = discord.Embed(
                    colour=discord.Colour.red(),
                    description=f"**{member.mention} left voice channel ``{before.channel.name}``.**"
                )

                if await is_showicon(member.guild.id, db):
                    embed.set_thumbnail(url=str(member.avatar_url))

                embed.set_author(name=str(member), icon_url=str(member.avatar_url))
                embed.set_footer(text=f"ID: {member.id}\n"
                                      f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await send(self.bot, member.guild.id, embed, db)

        # Moved to another VC
        elif before.channel and after.channel:
            if await is_logging(member.guild.id, "MemberMovedToVC", db):
                embed = discord.Embed(
                    colour=discord.Colour.red(),
                    description=f"**{member.mention} moved from voice channel "
                                f"``{before.channel.name}`` to ``{after.channel.name}``.**"
                )

                if await is_showicon(member.guild.id, db):
                    embed.set_thumbnail(url=str(member.avatar_url))

                embed.set_author(name=str(member), icon_url=str(member.avatar_url))
                embed.set_footer(text=f"ID: {member.id}\n"
                                      f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await send(self.bot, member.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if await is_logging(invite.guild.id, "Invites", db):
            embed = discord.Embed(
                colour=discord.Colour.green(),
                description=f"Invite Created"
            )

            if await is_showicon(invite.guild.id, db):
                embed.set_thumbnail(url=str(invite.guild.icon_url))

            embed.set_author(name=invite.guild.name, icon_url=str(invite.guild.icon_url))

            if invite.max_age == 0:
                age = "Forever"
            else:
                days, remainder = divmod(invite.max_age, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)

                if days == 0:
                    age = f"{hours}h {minutes}m {seconds}s"
                else:
                    age = f"{days}d {hours}h {minutes}m"

            embed.add_field(name="Max age", value=age, inline=False)
            embed.add_field(name="Temporary", value=str(invite.temporary), inline=False)
            embed.add_field(name="Max uses", value=str(invite.max_uses), inline=False)
            embed.add_field(name="Channel", value=f"<#{invite.channel.id}>", inline=False)

            embed.set_footer(text=f"ID: {invite.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, invite.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        if await is_logging(invite.guild.id, "Invites", db):
            embed = discord.Embed(
                colour=discord.Colour.red(),
                description=f"Invite Deleted"
            )

            if await is_showicon(invite.guild.id, db):
                embed.set_thumbnail(url=str(invite.guild.icon_url))

            embed.set_author(name=invite.guild.name, icon_url=str(invite.guild.icon_url))

            if invite.max_age == 0:
                age = "Forever"
            else:
                days, remainder = divmod(invite.max_age, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)

                if days == 0:
                    age = f"{hours}h {minutes}m {seconds}s"
                else:
                    age = f"{days}d {hours}h {minutes}m"

            embed.add_field(name="Max age", value=age, inline=False)
            embed.add_field(name="Temporary", value=str(invite.temporary), inline=False)
            embed.add_field(name="Max uses", value=str(invite.max_uses), inline=False)
            embed.add_field(name="Channel", value=f"<#{invite.channel.id}>", inline=False)

            embed.set_footer(text=f"ID: {invite.id}\n"
                                  f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await send(self.bot, invite.guild.id, embed, db)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        cursor = await db.execute("Select MessageID, RoleID, Reaction from RoleReact where MessageID = ?",
                                  (payload.message_id,))
        result = await cursor.fetchone()

        if not result:
            return

        if result[2] != str(payload.emoji):
            return

        guild = self.bot.get_guild(payload.guild_id) or await self.bot.fetch_guild(payload.guild_id)

        if not guild.get_role(result[1]):
            await db.execute("Delete from RoleReact where RoleID = ?", (result[1]))
            await db.commit()

        member = guild.get_member(payload.user_id)

        if member.bot:
            return

        try:
            roles = member.roles
            roles.append(guild.get_role(result[1]))
            await member.edit(roles=list(set(roles)))
        except:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        cursor = await db.execute("Select MessageID, RoleID, Reaction, DeleteOnRemove from RoleReact "
                                  "where MessageID = ?", (payload.message_id,))
        result = await cursor.fetchone()

        if not result:
            return

        if result[2] != str(payload.emoji):
            return

        if not result[3]:
            return

        guild = self.bot.get_guild(payload.guild_id) or await self.bot.fetch_guild(payload.guild_id)

        if not guild.get_role(result[1]):
            await db.execute("Delete from RoleReact where RoleID = ?", (result[1]))
            await db.commit()

        member = guild.get_member(payload.user_id)

        if member.bot:
            return

        try:
            roles = member.roles
            roles.remove(guild.get_role(result[1]))
            await member.edit(roles=list(set(roles)))
        except:
            pass


def setup(bot):
    bot.add_cog(Events(bot))
