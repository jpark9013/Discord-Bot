import asyncio
import random
from collections import OrderedDict

import discord
from discord.ext import commands

from bot.utils.format import send_embed, to_embed


class SaveServer(commands.Cog, name="Save Server"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db
        self.PermissionOverwriteType = {
            0: discord.TextChannel,
            1: discord.VoiceChannel,
            2: discord.CategoryChannel
        }

    async def commit(self, query, value):
        if not query or not value:
            return
        await db.execute(query, tuple(value))
        await db.commit()

    async def check_unique(self, ctx):
        if ctx.author != ctx.guild.owner:
            return await send_embed(ctx, "You are not the server owner.", negative=True)

        names = [i.name for i in ctx.guild.roles]
        if list(OrderedDict.fromkeys(names)) != names:
            return await send_embed(ctx, "Role names must all be unique in order to save the server.", negative=True)

        names = [i.name for i in ctx.guild.categories]
        if list(OrderedDict.fromkeys(names)) != names:
            return await send_embed(ctx, "Category names must all be unique in order to save the server.",
                                    negative=True)

        names = [i.name for i in ctx.guild.text_channels]
        if list(OrderedDict.fromkeys(names)) != names:
            return await send_embed(ctx, "Text channel names must all be unique in order to save the server.",
                                    negative=True)

        names = [i.name for i in ctx.guild.voice_channels]
        if list(OrderedDict.fromkeys(names)) != names:
            return await send_embed(ctx, "Voice channel names must all be unique in order to save the server.",
                                    negative=True)

        cursor = await db.execute("Select count(*) from Servers where AuthorID = ?", (ctx.author.id,))
        result = await cursor.fetchone()

        if result[0] >= 3:
            return await send_embed(ctx, "You may have a maximum of 3 servers saved at any time.", negative=True)

        return True

    async def save_bans(self, ctx):
        bans = await ctx.guild.bans()
        statement = ", ".join("(?, ?, ?)" for i in range(len(bans)))
        query = f"""Insert or Replace into MemberListBans values {statement}"""
        value = []
        for i in bans:
            value.extend((ctx.guild.id, i[1].id, True))
        await self.commit(query, value)

    async def save_members(self, ctx):
        members = ctx.guild.members
        statement = ", ".join("(?, ?, ?)" for i in range(len(members)))
        query = f"""Insert or Replace into MemberListBans values {statement}"""
        value = []
        for i in members:
            value.extend((ctx.guild.id, i.id, False))
        await self.commit(query, value)

    async def save_server(self, ctx, token):
        guild = ctx.guild
        query = f"""Insert or Replace into Servers values 
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        value = (ctx.author.id, guild.id, guild.name, guild.description, str(guild.icon_url), str(guild.banner_url),
                 str(guild.splash_url), guild.afk_channel.name if guild.afk_channel else None, guild.afk_timeout,
                 guild.verification_level.value, guild.default_notifications.value, guild.explicit_content_filter.value,
                 token)
        await self.commit(query, value)

        emojis = guild.emojis
        statement = ", ".join("(?, ?, ?, ?)" for i in range(len(emojis)))
        query = f"""Insert or Replace into Emojis values {statement}"""
        value = []
        for i in emojis:
            value.extend((ctx.guild.id, i.name, str(i.url), i.id))
        await self.commit(query, value)

    async def save_text_channels(self, ctx):
        text_channels = ctx.guild.text_channels
        statement = ", ".join("(?, ?, ?, ?, ?, ?, ?, ?, ?)" for i in range(len(text_channels)))
        query = f"""Insert or Replace into TextChannels values {statement}"""
        value = []
        for a, i in enumerate(text_channels):
            value.extend((ctx.guild.id, i.name, i.topic, a, i.nsfw, i.permissions_synced, i.category.name,
                          i.slowmode_delay, i.id))
            await self.save_overwrites(ctx, i)
        await self.commit(query, value)

    async def save_voice_channels(self, ctx):
        voice_channels = ctx.guild.voice_channels
        statement = ", ".join("(?, ?, ?, ?, ?, ?, ?, ?)" for i in range(len(voice_channels)))
        query = f"""Insert or Replace into VoiceChannels values {statement}"""
        value = []
        for a, i in enumerate(voice_channels):
            value.extend((ctx.guild.id, i.name, i.bitrate, i.user_limit, a, i.permissions_synced, i.category.name,
                          i.id))
            await self.save_overwrites(ctx, i)
        await self.commit(query, value)

    async def save_categories(self, ctx):
        categories = ctx.guild.categories
        statement = ", ".join("(?, ?, ?, ?, ?)" for i in range(len(categories)))
        query = f"""Insert or Replace into CategoryChannels values {statement}"""
        value = []
        for a, i in enumerate(categories):
            value.extend((ctx.guild.id, i.name, a, i.nsfw, i.id))
            await self.save_overwrites(ctx, i)
        await self.commit(query, value)

    async def save_roles(self, ctx):
        roles = [i for i in ctx.guild.roles if not i.managed and i != ctx.guild.default_role]
        statement = ", ".join("(?, ?, ?, ?, ?, ?, ?)" for i in range(len(roles)))
        query = f"""Insert or Replace into Roles values {statement}"""
        value = []
        for a, i in enumerate(roles, start=1):
            value.extend((ctx.guild.id, i.name, i.permissions.value, i.colour.value, i.hoist, i.mentionable, a))
        await self.commit(query, value)

    async def save_member_roles(self, ctx):
        members = ctx.guild.members
        value = []
        c = 0
        for i in members:
            for j in i.roles:
                if not j.managed and j != ctx.guild.default_role:
                    c += 1
                    value.extend((ctx.guild.id, i.id, j.name))
        statement = ", ".join("(?, ?, ?)" for i in range(c))
        query = f"""Insert or Replace into MemberRoles values {statement}"""
        await self.commit(query, value)

    async def save_overwrites(self, ctx, obj):
        overwrites = obj.overwrites
        statement = ", ".join("(?, ?, ?, ?, ?, ?, ?, ?)" for i in range(len(overwrites)))
        query = f"""Insert or Replace into Overwrites values {statement}"""
        value = []
        for i in overwrites:
            tup = overwrites[i].pair()
            # ENUMS don't work for me for some unknown reason
            if type(obj) == discord.TextChannel:
                x = 0
            elif type(obj) == discord.VoiceChannel:
                x = 1
            else:
                x = 2
            a = i.name if isinstance(i, discord.Role) else None
            b = i.id if isinstance(i, discord.Member) else None
            value.extend((ctx.guild.id, obj.name, a, b, tup[0].value, tup[1].value, i.id, x))
        await self.commit(query, value)

    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    async def saveserver(self, ctx):
        """Save the server in the DB."""

        cmd = self.bot.get_command("saveserver")
        if not await self.check_unique(ctx):
            cmd.reset_cooldown(ctx)
            return
        token = str(random.randint(0, 10 ** 64 - 10 ** 63 - 1) + 10 ** 63)
        await ctx.author.send(f"Your token is ``{token}``. Do not share this with anyone else!")

        await self.save_server(ctx, token)
        await self.save_bans(ctx)
        await self.save_members(ctx)
        await self.save_text_channels(ctx)
        await self.save_voice_channels(ctx)
        await self.save_categories(ctx)
        await self.save_roles(ctx)
        await self.save_member_roles(ctx)

        await send_embed(ctx, "Saved server.")

    async def wipe_server(self, ctx):
        for i in ctx.guild.roles:
            if i != ctx.guild.default_role and not i.managed:
                await i.delete(reason="Deleted during loadserver.")
        for i in ctx.guild.channels:
            await i.delete(reason="Deleted during loadserver.")
        for i in ctx.guild.emojis:
            await i.delete(reason="Deleted during loadserver.")

    async def get_bytes(self, url):
        try:
            async with self.bot.session.get(url) as resp:
                url_bytes = await resp.content.read()
        except:
            url_bytes = None
        return url_bytes

    async def load_emojis(self, ctx, id):
        cursor = await db.execute("Select Name, Image from Emojis where GuildID = ?", (id,))
        result = await cursor.fetchall()
        for name, image in result:
            await ctx.guild.create_custom_emoji(name=name, image=await self.get_bytes(image),
                                                reason="Created during loadserver.")

    async def load_bans(self, ctx, id):
        cursor = await db.execute("Select MemberID from MemberListBans where GuildID = ? and Ban = ?", (id, True))
        result = await cursor.fetchall()

        for i in result:
            try:
                user = self.bot.get_user(i[0]) or await self.bot.fetch_user(i[0])
                await ctx.guild.ban(user, reason="Banned during loadserver.")
            except discord.HTTPException:
                pass

    async def load_roles(self, ctx, id):
        query = "Select Name, Permissions, Colour, Hoist, Mentionable, Position from Roles where GuildID = ?"
        cursor = await db.execute(query, (id,))
        result = await cursor.fetchall()

        roles = {}
        for n, p, c, h, m, pp in result:
            role = await ctx.guild.create_role(
                name=n,
                permissions=discord.Permissions(p),
                colour=discord.Colour(c),
                hoist=bool(h),
                mentionable=bool(m),
                reason="Created during loadserver."
            )
            roles[n] = role

        for i, tup in enumerate(result):
            if i == 0:
                continue
            role = roles[tup[0]]
            try:
                await role.edit(position=tup[-1], reason="Edited during loadserver.")
            except discord.HTTPException:
                pass

    async def load_categories(self, ctx, id):
        cursor = await db.execute("Select Name, Position, NSFW from CategoryChannels where ID = ?", (id,))
        result = await cursor.fetchall()

        categories = {}
        for n, p, nn in result:
            a = await ctx.guild.create_category(name=n, nn=bool(nn))
            categories[n] = a
        # Wait until after they are all created
        for tup in result:
            category = categories[tup[0]]
            await category.edit(position=tup[1], reason="Edited during loadserver.")

    async def load_text_channels(self, ctx, id):
        query = """Select Name, Topic, Position, NSFW, SyncPermissions, Category, SlowmodeDelay from TextChannels 
                   where GuildID = ?"""
        cursor = await db.execute(query, (id,))
        result = await cursor.fetchall()

        text_channels = {}
        for n, t, p, nn, sp, c, sd in result:
            a = await ctx.guild.create_text_channel(
                name=n,
                category=discord.utils.get(ctx.guild.categories, name=c),
                topic=t,
                slowmode_delay=sd,
                nsfw=nn,
                sync_permissions=bool(sp),
                reason="Created during loadserver."
            )
            text_channels[n] = a
        for tup in result:
            tc = text_channels[tup[0]]
            await tc.edit(position=tup[2], reason="Edited during loadserver.")

    async def load_voice_channels(self, ctx, id):
        query = """
                Select Name, Bitrate, UserLimit, Position, SyncPermissions, Category from VoiceChannels 
                where GuildID = ?"""
        cursor = await db.execute(query, (id,))
        result = await cursor.fetchall()
        voice_channels = {}
        for n, b, u, p, s, c in result:
            a = await ctx.guild.create_voice_channel(
                name=n,
                bitrate=b,
                user_limit=u,
                sync_permissions=s,
                category=discord.utils.get(ctx.guild.categories, name=c)
            )
            voice_channels[n] = a
        for tup in result:
            vc = voice_channels[tup[0]]
            await vc.edit(position=tup[3], reason="Edited during loadserver.")

    async def load_member_roles(self, ctx, id):
        cursor = await db.execute("Select MemberID, Role from MemberRoles where GuildID = ?", (id,))
        result = await cursor.fetchall()
        for m, r in result:
            try:
                await ctx.guild.get_member(m).add_roles((discord.utils.get(ctx.guild.roles, name=r),),
                                                        reason="Edited during loadserver.")
            except AttributeError:
                pass
            except discord.Forbidden:
                pass

    async def load_permission_overwrites(self, ctx, id):
        cursor = await db.execute("Select Name, RoleName, MemberID, Allow, Deny, Type from Overwrites where GuildID = ?"
                                  , (id,))
        result = await cursor.fetchall()

        po = {}
        for n, r, m, a, d, t in result:
            if t == 0:
                z = ctx.guild.text_channels
            elif t == 1:
                z = ctx.guild.voice_channels
            else:
                z = ctx.guild.categories
            c = discord.utils.get(z, name=n)
            b = ctx.guild.get_member(m) if m else discord.utils.get(ctx.guild.roles, name=r)
            if not b:
                continue
            p_o = discord.PermissionOverwrite.from_pair(
                discord.Permissions(permissions=a),
                discord.Permissions(permissions=d)
            )
            try:
                po[c][b] = p_o
            except KeyError:
                po[c] = {b: p_o}

        for i in po:
            await i.edit(overwrites=po[i])

    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    async def loadserver(self, ctx):
        """Load the server. Will wipe the server, however. Only bans will remain."""

        cmd = self.bot.get_command("loadserver")

        if ctx.guild.roles[-1] not in ctx.me.roles:
            cmd.reset_cooldown(ctx)
            return await send_embed(ctx, "The top role needs to be in the bot roles.", negative=True)

        await ctx.author.send("Send the token through here. You have 2 minutes.")
        try:
            msg = await self.bot.wait_for("message", check=lambda x: x.author == ctx.author and not x.guild,
                                          timeout=120)
        except asyncio.TimeoutError:
            cmd.reset_cooldown(ctx)
            return await send_embed(ctx, "Timed out.", negative=True)

        await self.wipe_server(ctx)

        cursor = await db.execute("Select count(*), Name, Description, Icon, Banner, Splash, AFKChannel, AFKTimeout, "
                                  "VerificationLevel, NotificationLevel, ContentFilter, GuildID from Servers "
                                  "where Token = ?", (msg.content,))
        result = await cursor.fetchone()

        if not result[0]:
            cmd.reset_cooldown(ctx)
            return await send_embed(ctx, "Saved server with token does not exist.", negative=True)

        id = result[11]
        icon = await self.get_bytes(result[3])
        banner = await self.get_bytes(result[4])
        splash = await self.get_bytes(result[5])

        await ctx.guild.edit(
            name=result[1],
            description=result[2],
            icon=icon,
            banner=banner,
            splash=splash,
            afk_channel=None,  # FOR NOW CHANGE LATER PLS
            afk_timeout=result[7],
            verification_level=discord.VerificationLevel(result[8]),
            default_notifications=discord.NotificationLevel(result[9]),
            explicit_content_filter=discord.ContentFilter(result[10]),
        )

        await self.load_emojis(ctx, id)
        await self.load_bans(ctx, id)
        await self.load_roles(ctx, id)
        await self.load_categories(ctx, id)
        await self.load_text_channels(ctx, id)
        await self.load_voice_channels(ctx, id)
        await self.load_member_roles(ctx, id)
        await self.load_permission_overwrites(ctx, id)
        await ctx.author.send("Loaded server.")

    @commands.cooldown(rate=1, per=600, type=commands.BucketType.user)
    @commands.command(aliases=["removeserver"])
    async def deleteserver(self, ctx, token):
        """Remove a server given its token. This frees you up for the 3-server saved limit."""

        cursor = await db.execute("Select count(*) from Servers where Token = ?", (token,))
        result = await cursor.fetchone()

        if not result[0]:
            self.bot.get_command("deleteserver").reset_cooldown(ctx)
            return await send_embed(ctx, "No servers found with the given token.", negative=True)

        cursor = await db.execute("Select GuildID from Servers where Token = ?", (token,))
        result = await cursor.fetchone()
        a = result[0]

        await db.execute("Delete from Servers where Token = ?", (token,))
        await db.commit()
        await db.execute("Delete from MemberListBans where GuildID = ?", (a,))
        await db.commit()
        await db.execute("Delete from TextChannels where GuildID = ?", (a,))
        await db.commit()
        await db.execute("Delete from VoiceChannels where GuildID = ?", (a,))
        await db.commit()
        await db.execute("Delete from CategoryChannels where GuildID = ?", (a,))
        await db.commit()
        await db.execute("Delete from Roles where GuildID = ?", (a,))
        await db.commit()
        await db.execute("Delete from Overwrites where GuildID = ?", (a,))
        await db.commit()
        await db.execute("Delete from Emojis where GuildID = ?", (a,))
        await db.commit()

        await send_embed(ctx, "Deleted the server.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command()
    async def listserver(self, ctx):
        """List the servers you've saved. If invoked in DM context, will add token."""

        cursor = await db.execute("Select GuildID, Name, Token from Servers where AuthorID = ?", (ctx.author.id,))
        result = await cursor.fetchall()

        if not result:
            return await send_embed(ctx, "You do not have any servers saved.", negative=True)

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"Servers saved for {str(ctx.author)}"
        )
        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
        for g, n, t in result:
            if not ctx.guild:
                value = f"ID: ``{g}``\nToken: ``{t}``"
            else:
                value = f"ID: ``{g}``"
            embed.add_field(name=n, value=value, inline=False)

        await ctx.send(embed=embed)
