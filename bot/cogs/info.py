import json
import sqlite3
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot.utils.message import send_embed


def check(ctx):
    return ctx.guild.id == 732980515807952897


class Info(commands.Cog, name="Info"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.time_playing.start()

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

        embed.add_field(name="Info", value=f"{uptime}\n"
                                           f"Currently in **{len(self.bot.guilds)}** servers\n"
                                           f"Watching **{len(self.bot.users) - 1}** users\n", inline=False)

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

        embed.add_field(
            name="Check out my other projects!",
            value="[Asyncio wrapper for CodeForces](https://github.com/jpark9013/aiocodeforces)"
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

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    @commands.check(check)
    @commands.has_permissions(administrator=True)
    async def kevinstimeplayingleague(self, ctx):
        """Get Kevin's time playing league"""

        cursor = await db.execute("Select Activities from Activity where MemberID = ?", (547796508221767692,))
        result = await cursor.fetchone()

        if not result or not result[0]:
            return await send_embed(ctx, "Kevin probably hid his League activity so the bot can't see it.",
                                    negative=True)

        dict = json.loads(result[0])

        hasleague = False

        for i, v in dict.items():
            v /= 2
            if i == "League of Legends":
                hasleague = True
                d, remainder = divmod(v, 86400)
                h, remainder = divmod(remainder, 3600)
                m, s = divmod(remainder, 60)

                description = f"League time played: {int(d)}d {int(h)}h {int(m)}m {int(s)}s\n" \
                              f"Since 07/25/2020 18:00:00"
                break

        if not hasleague:
            return await send_embed(ctx, "Kevin probably hid his League activity so the bot can't see it.",
                                    negative=True)

        await send_embed(ctx, description, info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    async def timeplaying(self, ctx, member: discord.Member):
        """Get time played on various activities on a member."""

        cursor = await db.execute("Select Activities from Activity where MemberID = ?", (member.id,))
        result = await cursor.fetchone()

        if not result or not result[0]:
            return await send_embed(ctx, "Could not find any activities for the member in the DB.", negative=True)

        descriptions = []

        dict = json.loads(result[0])

        for i, v in dict.items():
            v /= 2
            d, remainder = divmod(v, 86400)
            h, remainder = divmod(remainder, 3600)
            m, s = divmod(remainder, 60)

            descriptions.append(f"Activity: {i}\n"
                                f"Time played: {int(d)}d {int(h)}h {int(m)}m {int(s)}s\n"
                                f"")

        total = sum(dict.values()) / 2
        d, remainder = divmod(total, 86400)
        h, remainder = divmod(remainder, 3600)
        m, s = divmod(remainder, 60)

        d = int(d)
        h = int(h)
        m = int(m)
        s = int(s)

        descs = []
        embeds = []

        for i, v in enumerate(descriptions, start=1):
            descs.append(v)
            if i == len(descriptions) or i % 5 == 0:
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title=f"{str(member)}'s time playing various activities",
                    description="\n".join(descs)
                )
                embed.set_author(name=str(member), icon_url=str(member.avatar_url))
                embed.set_footer(text=f"Total time played on all activities: {d}d {h}h {m}m {s}s\n"
                                      f"Since 07/25/2020/ 18:00:00")

                embeds.append(embed)
                descs = []

        await self.bot.paginate(ctx, embeds)

    @tasks.loop(seconds=30)
    async def time_playing(self):

        for member in self.bot.get_all_members():

            if not member.bot:
                cursor = await db.execute("Select Activities from Activity where MemberID = ?", (member.id,))
                result = await cursor.fetchone()

                dict = {}
                indb = False

                isactivity = False

                for activity in member.activities:
                    isactivity = True
                    if not result:
                        dict[activity.name] = 30
                    else:
                        indb = True
                        dict = json.loads(result[0])
                        try:
                            dict[activity.name] += 30
                        except KeyError:
                            dict[activity.name] = 30

                if isactivity:
                    try:
                        if not indb:
                            await db.execute("Insert into Activity values(?, ?)", (member.id, json.dumps(dict)))
                            await db.commit()

                        else:
                            await db.execute("Update Activity set Activities = ? where MemberID = ?", (json.dumps(dict),
                                                                                                       member.id))
                            await db.commit()

                    except sqlite3.OperationalError:
                        pass
                    except sqlite3.DatabaseError:
                        pass

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Get info of the current server."""

        cmd = self.bot.get_command("server_info")
        await cmd(ctx)
