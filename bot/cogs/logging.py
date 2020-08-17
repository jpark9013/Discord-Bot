import typing

import discord
from discord.ext import commands

from bot.utils.format import send_embed

"""
Logging key: 
0. Member Joined
1. Member Left
2. Member Banned
3. Member Unbanned
4. Message Edited
5. Message Delete.
6. Bulk Message Deletion
7. Channel Created
8. Channel Deleted
9. Role Created
10. Role Deleted
11. Role Updated
12. Role Given
13. Role Removed
14. Nickname Changed
15. Moderator Command Used.
16. Member Joined VC.
17. Member Left VC.
18. Member moved to VC.
19. Log invites/invite info
"""


async def write(ctx, column, string):
    """Write to SQL db and send embed"""

    cursor = await db.execute(f"Select {column} from Logging where GuildID = ?", (ctx.guild.id,))
    result = await cursor.fetchone()
    await db.execute(f"Update Logging set {column} = ? where GuildID = ?", (not result, ctx.guild.id))
    await db.commit()
    if result:
        await send_embed(ctx, f"Turned {string} logging off.")
    else:
        await send_embed(ctx, f"Turned {string} logging on.")


class Logging(commands.Cog, name="Logging"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def log(self, ctx):
        """Turn logging on and off"""

        cursor = await db.execute("Select Enabled from Logging where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result == ():
            await db.execute("Insert into Logging values "
                             "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (ctx.guild.id, None, False, False, False, False, False, False, False, False, False, False,
                              False, False, False, False, False, False, False, False, False, False, True, False))
            await db.commit()
            await send_embed(ctx, "Turned logging off.")

        elif not result[0]:
            await db.execute("Update Logging set Enabled = ? where GuildID = ?", (1, ctx.guild.id))
            await db.commit()
            await send_embed(ctx, "Turned logging on.")

        else:
            await db.execute("Update Logging set Enabled = ? where GuildID = ?", (0, ctx.guild.id))
            await db.commit()
            await send_embed(ctx, "Turned logging off.")

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def all(self, ctx):
        """Turn all logging on or off."""

        cursor = await db.execute("Select * from Logging where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        all = True

        for i in range(2, 22):
            if not result[i]:
                all = False
                break

        if all:
            await db.execute("Update Logging set MemberJoined = ?, MemberLeft = ?, MemberBanned = ?, MemberUnbanned = "
                             "?, MessageEdited = ?, MessageDeleted = ?, BulkMessageDeletion = ?, ChannelCreated = ?, "
                             "ChannelDeleted = ?, RoleCreated = ?, RoleDeleted = ?, RoleUpdated = ?, RoleGiven = ?, "
                             "RoleRemoved = ?, NicknameChanged = ?,  ModeratorCommandUsed = ?, MemberJoinedVC = ?, "
                             "MemberLeftVC = ?, MemberMovedToVC = ?, Invites = ? where GuildID = ?",
                             (False, False, False, False, False, False, False, False, False, False, False, False, False,
                              False, False, False, False, False, False, False, ctx.guild.id))
            await db.commit()
            await send_embed(ctx, "Turned all logging off.")

        else:
            await db.execute("Update Logging set MemberJoined = ?, MemberLeft = ?, MemberBanned = ?, MemberUnbanned = "
                             "?, MessageEdited = ?, MessageDeleted = ?, BulkMessageDeletion = ?, ChannelCreated = ?, "
                             "ChannelDeleted = ?, RoleCreated = ?, RoleDeleted = ?, RoleUpdated = ?, RoleGiven = ?, "
                             "RoleRemoved = ?, NicknameChanged = ?,  ModeratorCommandUsed = ?, MemberJoinedVC = ?, "
                             "MemberLeftVC = ?, MemberMovedToVC = ?, Invites = ? where GuildID = ?",
                             (True, True, True, True, True, True, True, True, True, True, True, True, True, True, True,
                              True, True, True, True, True, ctx.guild.id))
            await db.commit()
            await send_embed(ctx, "Turned all logging on.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set channel for logging, which will automatically put it in the ignored channels list. If you switch channels
        for logging, the former channel for logging will still be in the ignored channels list unless you manually
        remove it."""

        cursor = await db.execute("Select count(*) from Logging where ChannelID = ?", (channel.id,))
        result = await cursor.fetchone()

        if result[0]:
            return await send_embed(ctx, "Logging is already set to that channel.", negative=True)

        await db.execute("Update Logging set ChannelID = ? where GuildID = ?",
                         (channel.id, ctx.guild.id))
        await db.commit()

        await db.execute("Insert or replace into LoggingIgnoredChannels values (?, ?)", (ctx.guild.id, channel.id))
        await db.commit()

        await send_embed(ctx, f"Set logging to <#{channel.id}>.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def ignorechannel(self, ctx, channel: typing.Union[discord.TextChannel,
                                                             discord.VoiceChannel, discord.CategoryChannel]):
        """Ignore a text, voice, or category channel."""

        cursor = await db.execute("Select IgnoredChannelID from LoggingIgnoredChannels where GuildID = ?",
                                  (ctx.guild.id,))
        ignoredchannels = await cursor.fetchall()

        ignoredchannels = [i[0] for i in ignoredchannels]

        cursor = await db.execute("Select ChannelID from Logging where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if channel.id in ignoredchannels and channel.id == result[0]:
            return await send_embed(ctx, "Cannot unignore the logging channel.", negative=True)

        if channel.id not in ignoredchannels:
            await db.execute("Insert into LoggingIgnoredChannels values (?, ?)", (channel.id, ctx.guild.id))
            await db.commit()
            string = "ignored"

        else:
            await db.execute("Delete from LoggingIgnoredChannels where IgnoredChannelID = ?", (channel.id,))
            await db.commit()
            string = "unignored"

        if isinstance(channel, discord.TextChannel):
            await send_embed(ctx, f"Channel ``<#{channel.id}>`` {string} in logging.")
        elif isinstance(channel, discord.VoiceChannel):
            await send_embed(ctx, f"Voice channel ``<#{channel.id}>`` {string} in logging.")
        elif isinstance(channel, discord.CategoryChannel):
            await send_embed(ctx, f"Category ``<#{channel.id}>`` {string} in logging.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def showicon(self, ctx):
        """Toggle showing author icon for logs."""

        cursor = await db.execute("Select ShowIcon from Logging where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if result[0]:
            await db.execute("Update Logging set ShowIcon = ? where GuildID = ?", (True, ctx.guild.id))
            await send_embed(ctx, "Turned showing author icon for logs on.")
        else:
            await db.execute("Update Logging set ShowIcon = ? where GuildID = ?", (False, ctx.guild.id))
            await send_embed(ctx, "Turned showing author icon for logs off.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def memberjoin(self, ctx):
        """Toggle member join logging on or off."""

        await write(ctx, "MemberJoined", "member join")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def memberleave(self, ctx):
        """Toggle member leave logging on or off."""

        await write(ctx, "MemberLeft", "member leave")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def memberban(self, ctx):
        """Toggle member ban logging on or off."""

        await write(ctx, "MemberBanned", "member ban")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def memberunban(self, ctx):
        """Toggle member unban logging on or off."""

        await write(ctx, "MemberUnbanned", "member unban")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def messageedit(self, ctx):
        """Toggle message edit logging on or off."""

        await write(ctx, "MessageEdited", "message edit")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def messagedelete(self, ctx):
        """Toggle message delete logging on or off."""

        await write(ctx, "MessageDeleted", "message delete")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def bulkmessagedeletion(self, ctx):
        """Toggle bulk message deletion logging on or off."""

        await write(ctx, "BulkMessageDeletion", "bulk message deletion")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def channelcreate(self, ctx):
        """Toggle channel create logging on or off."""

        await write(ctx, "ChannelCreation", "channel create")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def channeldelete(self, ctx):
        """Toggle channel delete logging on or off."""

        await write(ctx, "ChannelDeleted", "channel delete")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def rolecreate(self, ctx):
        """Toggle role create logging on or off."""

        await write(ctx, "RoleCreated", "role create")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def roledelete(self, ctx):
        """Toggle role delete logging on or off."""

        await write(ctx, "RoleDeleted", "role delete")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def roleupdate(self, ctx):
        """Toggle role update logging on or off."""

        await write(ctx, "RoleUpdated", "role update")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def rolegive(self, ctx):
        """Toggle role give logging on or off."""

        await write(ctx, "RoleGiven", "role give")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def roleremove(self, ctx):
        """Toggle role remove logging on or off."""

        await write(ctx, "RoleRemoved", "role remove")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def nicknamechange(self, ctx):
        """Toggle nickname change logging on or off."""

        await write(ctx, "NicknameChanged", "nickname change")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command(aliases=["moderatorcommandused"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def modcommandused(self, ctx):
        """Toggle mod command usage logging on or off."""

        await write(ctx, "ModeratorCommandUsed", "mod command usage")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def memberjoinvc(self, ctx):
        """Toggle member join VC logging on or off."""

        await write(ctx, "MemberJoinedVC", "member join VC")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def memberleavevc(self, ctx):
        """Toggle member leave VC logging on or off."""

        await write(ctx, "MemberLeftVC", "member leave VC")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def membermovetovc(self, ctx):
        """Toggle member moving to VC logging on or off."""

        await write(ctx, "MemberMovedToVC", "member moving to VC")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @log.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def invites(self, ctx):
        """Toggle invites logging on or off."""

        await write(ctx, "Invites", "invites")
