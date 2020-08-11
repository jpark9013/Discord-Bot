import discord
from discord.ext import commands

from bot.utils.format import send_embed, to_embed


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # If there is an error while invoking a command
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        cmd = ctx.command
        if hasattr(cmd, "on_error"):
            return
        error = getattr(error, "original", error)

        # Self-explanatory
        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument) \
                or isinstance(error, commands.TooManyArguments):

            await ctx.invoke(self.bot.get_command("help"), name=ctx.command.qualified_name)

        elif isinstance(error, commands.MissingPermissions):
            await send_embed(ctx, str(error), negative=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await send_embed(ctx, str(error), negative=True)
        elif isinstance(error, commands.CommandOnCooldown):
            await send_embed(ctx, str(error), negative=True)
        elif isinstance(error, commands.NotOwner):
            return
        elif isinstance(error, commands.CheckFailure):
            await send_embed(ctx, str(error), negative=True)
        else:
            await send_embed(ctx, str(error), negative=True)
            channel = self.bot.get_guild(721194829366951997).get_channel(735309492757069896)

            embed = discord.Embed(
                title="Error",
                description=f"```py\n"
                            f"{str(error)}\n"
                            f"```",
                colour=discord.Colour.red()
            )
            embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            if ctx.guild:
                embed.set_footer(text=f"Command/Content: {ctx.message.content} • Guild: {ctx.guild.name} "
                                      f"(ID {ctx.guild.id}) • Channel: {ctx.channel.name} (ID {ctx.channel.id})")
            else:
                embed.set_footer(text=f"Command/Content: {ctx.message.content} • Channel: DMChannel")

            await channel.send(embed=embed)
