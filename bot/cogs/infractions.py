import discord
from discord.ext import commands

from utils.format import send_embed


class Infraction:

    __slots__ = ["type", "reason", "time", "mod_id", "minutes", "id"]

    def __init__(self, type: str, reason: str, time: str, mod_id: int, minutes: float, id: int):
        self.type = type
        self.reason = reason
        self.time = time
        self.mod_id = mod_id
        self.minutes = minutes
        self.id = id


async def get_infractions(member):
    cursor = await db.execute("Select Type, Reason, Time, ModeratorID, Minutes, ID from Infractions "
                              "where GuildID = ? and MemberID = ?",
                              (member.guild.id, member.id))
    result = await cursor.fetchall()

    return [Infraction(i[0], i[1], i[2], i[3], i[4], i[5]) for i in result]


class Infractions(commands.Cog, name="Infractions"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @commands.group(aliases=["infractions"])
    @commands.guild_only()
    async def modlogs(self, ctx, member: discord.Member):
        """Show the modlogs for a member."""

        infractions = await get_infractions(member)

        if not infractions:
            return await send_embed(ctx, f"Did not find any modlogs for {member.mention}.", negative=True)

        embed = discord.Embed(color=discord.Colour.blue())
        embed.set_author(name=str(member), icon_url=str(member.avatar_url))

        for i, infraction in enumerate(infractions, start=1):
            moderator = self.bot.get_user(infraction.mod_id) or await self.bot.fetch_member(infraction.mod_id)

            if infraction.type.lower() in ["warn", "kick", "softban", "unban", "unmute"]:

                embed.add_field(name=f"Case {i}",
                                value=f"**Type:** {infraction.type}\n"
                                      f"**User:** ({member.id}) {str(member)}\n"
                                      f"**Moderator:** {str(moderator)}\n"
                                      f"**Reason:** {infraction.reason}\n"
                                      f"**Timestamp:** {infraction.time}"
                                      f"**ID:** {infraction.id}", inline=False)

            else:

                if infraction.minutes == -1:
                    infraction.minutes = "Forever"

                else:
                    days, remainder = divmod(infraction.minutes, 1440)
                    hours, minutes = divmod(remainder, 60)

                    if days == 0:
                        infraction.minutes = f"{hours}h {minutes}m"
                    else:
                        infraction.minutes = f"{days}d {hours}h {minutes}m"

                embed.add_field(name=f"Case {i}",
                                value=f"**Type:** {infraction.type}\n"
                                      f"**User:** ({member.id}) {str(member)}\n"
                                      f"**Moderator:** {str(moderator)}\n"
                                      f"**Reason:** {infraction.reason}\n"
                                      f"**Timestamp:** {infraction.time}\n"
                                      f"**Time:** {infraction.minutes}\n"
                                      f"**ID:** {infraction.id}", inline=False)

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @modlogs.group(aliases=["remove"])
    @commands.guild_only()
    async def delete(self, ctx, member: discord.Member, InfractionID: int):
        """Delete a modlog infraction from a member."""

        cursor = await db.execute("Select count(Time) from Infractions where GuildID = ? and MemberID = ? "
                                  "and ID = ?", (ctx.guild.id, member.id, InfractionID))
        result = await cursor.fetchone()

        if not result[0]:
            return await send_embed(ctx, "No infraction found with the given ID.", negative=True)

        await db.execute("Delete from Infractions where GuildID = ? and MemberID = ? and ID = ?",
                         (ctx.guild.id, member.id, InfractionID))
        await db.commit()

        await send_embed(ctx, "Infraction removed from member.")


def setup(bot):
    bot.add_cog(Infractions(bot))
