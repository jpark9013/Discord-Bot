import time
from datetime import datetime

import discord
from discord.ext import commands


class Info(commands.Cog, name="Info"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(aliases=["memberinfo"])
    @commands.guild_only()
    async def userinfo(self, ctx, member: discord.Member = None):
        """Show user info."""

        if not member:
            member = ctx.author

        embed = discord.Embed(colour=discord.Colour.blue(), description=member.mention)
        embed.set_author(name=str(member), icon_url=str(member.avatar_url))
        embed.set_thumbnail(url=str(member.avatar_url))
        embed.add_field(name="Joined", value=member.joined_at.strftime('%m/%d/%Y, %H:%M:%S'))
        embed.add_field(name="Registered", value=member.created_at.strftime('%m/%d/%Y, %H:%M:%S'))
        roles = ", ".join([role.name for role in member.roles if role != ctx.guild.default_role])
        if not roles:
            roles = "None"
        embed.add_field(name=f"Roles ({len(member.roles) - 1})", value=roles, inline=False)
        permissions = []
        if member.guild_permissions.kick_members:
            permissions.append("Kick Members")
        if member.guild_permissions.ban_members:
            permissions.append("Ban Members")
        if member.guild_permissions.administrator:
            permissions.append("Administrator")
        if member.guild_permissions.manage_channels:
            permissions.append("Manage Channels")
        if member.guild_permissions.manage_guild:
            permissions.append("Manage Server")
        if member.guild_permissions.view_audit_log:
            permissions.append("View Audit Log")
        if member.guild_permissions.manage_messages:
            permissions.append("Manage Messages")
        if member.guild_permissions.mention_everyone:
            permissions.append("Mention Everyone")
        if member.guild_permissions.mute_members:
            permissions.append("Mute Members")
        if member.guild_permissions.deafen_members:
            permissions.append("Deafen Members")
        if member.guild_permissions.move_members:
            permissions.append("Move Members")
        if member.guild_permissions.manage_nicknames:
            permissions.append("Manage Nicknames")
        if member.guild_permissions.manage_roles:
            permissions.append("Manage Roles")
        if member.guild_permissions.manage_webhooks:
            permissions.append("Manage Webhooks")
        if member.guild_permissions.manage_emojis:
            permissions.append("Manage Emojis")
        key_permissions = ", ".join(permissions)
        if not key_permissions:
            key_permissions = "None"
        embed.add_field(name="Key Permissions", value=key_permissions, inline=False)

        if member == ctx.guild.owner:
            embed.add_field(name="Acknowledgments", value="Server Owner", inline=False)

        embed.set_footer(text=f"ID: {member.id}\n"
                              f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    async def info(self, ctx):
        """Show bot info."""

        embed = discord.Embed(colour=discord.Colour.blue(), title="Bot Info", description="A bot.")
        embed.set_author(name=str(self.bot.user), icon_url=str(self.bot.user.avatar_url))
        embed.set_thumbnail(url=str(self.bot.user.avatar_url))

        days, remainder = divmod(time.time() - self.bot.startTime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days == 0:
            uptime = f"Uptime: {int(hours)}h {int(minutes)}m {int(seconds)}s"
        else:
            uptime = f"Uptime: {int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

        cursor = await db.execute("Select sum(Uses) from Commands")
        result = await cursor.fetchone()

        embed.add_field(name="Info", value=f"{uptime}\n"
                                           f"Currently in **{len(self.bot.guilds)}** servers\n"
                                           f"Watching **{len(self.bot.users)-1}** users\n"
                                           f"With **{result[0]}** commands sent", inline=False)

        embed.add_field(
            name="Invite",
            value=f"[Click me]"
                  f"(https://discord.com/api/oauth2/authorize?client_id=718287109030543370&permissions=8&scope=bot)",
        )

        embed.add_field(
            name="Github",
            value="[Click me](https://github.com/jpark9013/HumphreyGaming)",
        )

        embed.add_field(
            name="top.gg link",
            value="[Vote for me here](https://top.gg/bot/718287109030543370)"
        )

        try:
            mention = (self.bot.get_user(439228325722849290) or await self.bot.fetch_user(439228325722849290)).mention
        except:
            mention = (self.bot.get_user(648741756384575509) or await self.bot.fetch_user(648741756384575509)).mention

        embed.add_field(
            name="Owner",
            value=f"{mention}"
        )

        embed.set_footer(text=datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    async def leaderboard(self, ctx):
        """Returns the top 10 command users."""

        cursor = await db.execute("Select MemberID, Uses from Commands order by Uses desc limit 10")
        result = await cursor.fetchall()

        members = []
        for i in result:
            member = self.bot.get_user(i[0]) or await self.bot.fetch_user(i[0])
            if not member:
                members.append(("Account deleted", 0))
                await db.execute("Delete from Commands where MemberID = ?", (i[0]))
                await db.commit()
            else:
                members.append((member.mention, i[1]))

        for i in range(0, 10):
            try:
                a = members[i]
            except:
                members.append(("None", 0))

        description = []

        for index, tuple in enumerate(members, start=1):
            description.append(f"{index}. {tuple[0]} ({tuple[1]} uses)")

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Leaderboard",
            description="\n".join(description)
        )

        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
        embed.set_footer(text="If there is an 'Account Deleted' entry in the leaderboard, do not worry; it has been "
                              "deleted in the database, and will not pop up the next time you call this command.")

        await ctx.send(embed=embed)
