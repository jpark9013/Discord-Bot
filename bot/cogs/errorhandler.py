import discord
from discord.ext import commands

from bot.utils.message import send_embed


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
            command_names = [i.qualified_name for i in self.bot.walk_commands()
                             if i.cog and i.cog.qualified_name != "Owner"]

            if ctx.command.qualified_name not in command_names:
                return

            await ctx.invoke(self.bot.get_command("help"), name=ctx.command.qualified_name)

        elif isinstance(error, commands.MissingPermissions):
            await send_embed(ctx, str(error), negative=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await send_embed(ctx, str(error), negative=True)
        elif isinstance(error, commands.CommandOnCooldown):
            await send_embed(ctx, str(error), negative=True)
        elif isinstance(error, commands.NotOwner):
            return
