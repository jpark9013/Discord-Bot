import time

import discord
from discord.ext import commands

from bot.utils.message import send_embed


async def sql_write(ctx, column, string):
    cursor = await db.execute(f"Select {column} from AutoMod where GuildID = ?", (ctx.guild.id,))
    result = await cursor.fetchone()

    if result[0]:
        await db.execute(f"Update AutoMod set {column} = ? where GuildID = ?", (False, ctx.guild.id))
        await db.commit()
        await send_embed(ctx, f"Turned off detection for {string}.")

    else:
        await db.execute(f"Update AutoMod set {column} = ? where GuildID = ?", (True, ctx.guild.id))
        await db.commit()
        await send_embed(ctx, f"Turned on detection for {string}.")


class AutoMod(commands.Cog, name="AutoMod"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    # Banned words command is in guildsetup, because I'm too lazy to move it here along with the rest of the DB
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.group()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def automod(self, ctx):
        """Get AutoMod settings for this server."""

        cursor = await db.execute("Select AllCaps, FastMessageSpam, DiscordInvites, Links, MassMention, EmojiSpam, "
                                  "Spoilers, Selfbot from AutoMod where GuildID = ?", (ctx.guild.id,))
        result = await cursor.fetchone()

        if not result:
            await db.execute("Insert into AutoMod values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (ctx.guild.id, False, False, False, False, False, False, False, False))
            await db.commit()
            result = (False, False, False, False, False, False, False, False)

        result = list(result)

        for i in result:
            if i:
                i = "On"
            else:
                i = "Off"

        description = f"**All Caps Detection:** {result[0]}\n" \
                      f"**Fast Message Spam Detection:** {result[1]}\n" \
                      f"**Discord Invite Detection:** {result[2]}\n" \
                      f"**Link Detection:** {result[3]}\n" \
                      f"**Mass Mention Detection:** {result[4]}\n" \
                      f"**Emoji Spam Detection:** {result[5]}\n" \
                      f"**Spoiler Detection:** {result[6]}\n" \
                      f"**Selfbot Detection:** {result[7]}\n"

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="AutoMod Settings",
            description=description
        )
        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @automod.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def allcaps(self, ctx):
        """Toggle all caps detection on or off. Removes message if detected."""

        await sql_write(ctx, "AllCaps", "all caps")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @automod.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def fastmessagespam(self, ctx):
        """Toggle fast message spam detection on or off. 15 minute mute is the punishment unless the server doesn't have
        a designated mute role or bot doesn't have permission to add roles."""

        await sql_write(ctx, "FastMessageSpam", "fast message spam")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @automod.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def discordinvites(self, ctx):
        """Toggle discord invite detection on or off. Removes message if detected."""

        await sql_write(ctx, "DiscordInvites", "discord invites")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @automod.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def links(self, ctx):
        """Toggle link detection on or off. Removes message if detected."""

        await sql_write(ctx, "Links", "links")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @automod.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def massmention(self, ctx):
        """Toggle mass mention detection on or off. Removes message and mutes member for 15 minutes if detected."""

        await sql_write(ctx, "MassMention", "mass mentions")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @automod.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def emojispam(self, ctx):
        """Toggle emoji spam detection on or off. Removes message if detected."""

        await sql_write(ctx, "EmojiSpam", "emoji spam")

