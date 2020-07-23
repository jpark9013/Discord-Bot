import json

import discord
from discord.ext import commands

from bot.utils.message import send_embed, to_embed


class HelpCommand(commands.Cog, name="HelpCommand"):
    def __init__(self, bot):
        self.bot = bot
        db = self.bot.db
        self.content = "Multiple changes made."

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command()
    async def help(self, ctx, *, name: str = None):
        """Get help on categories."""

        with open("prefixes.json", "r") as f:
            d = json.load(f)
            prefix = d[str(ctx.guild.id)]

        cogs = self.bot.cogs

        cog_names_with_commands = [i for i in cogs.keys() if cogs[i].get_commands() and i != "Owner" and i != "Jishaku"]
        command_names = [i.qualified_name for i in self.bot.walk_commands()
                         if i.cog and i.cog.qualified_name != "Owner" and i.cog.qualified_name != "Jishaku"]

        if not name:
            value = [f"-{i}\n" for i in cog_names_with_commands]

            # Albert
            author = str(self.bot.get_user(439228325722849290) or await self.bot.fetch_user(439228325722849290))

            embed = discord.Embed(
                title="Command Help",
                description=f"By {author}\n "
                            "```\n"
                            f"Type {prefix}help [module name] for more information on a module. (Don't type the "
                            f"brackets)\n"
                            "This also works for individual commands. Everything is case sensitive!"
                            "```"
            )

            embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            embed.set_footer(text=f"{prefix}support create [query] to create a new support ticket. (Don't type the "
                                  f"brackets)")

            embed.add_field(name="Modules:", value="".join(value))

            await ctx.send(embed=embed)

        else:

            if name in cog_names_with_commands:

                cog = self.bot.get_cog(name)

                embeds = []
                value = []

                for index, command in enumerate(cog.get_commands(), start=1):
                    value.append(f"{index}. {prefix}{command.qualified_name} {command.signature}")

                    if index % 10 == 0 or index == len(cog.get_commands()):
                        embed = discord.Embed(
                            colour=discord.Colour.blue(),
                            description="\n".join(value),
                            title=command.cog.qualified_name
                        )

                        embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        embed.set_footer(text=f"Do {prefix}help [command name] to get more info on a command!")

                        embeds.append(embed)
                        value = []

                await self.bot.paginate(ctx, embeds)

            elif name in command_names:

                command = self.bot.get_command(name)

                if command.cog.qualified_name == "Owner":
                    return await send_embed(ctx, "Invalid category/command name", negative=True)

                try:
                    subcommands = ", ".join([i.name for i in command.commands])
                except AttributeError:
                    subcommands = "None"

                aliases = ", ".join(command.aliases) if command.aliases else "None"

                description = f"**Subcommands: {subcommands}**\n" \
                              f"**Aliases: {aliases}**\n" \
                              f"\n" \
                              f"{command.help}"

                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title=f"{prefix}{command.qualified_name} {command.signature}",
                    description=description
                )

                embed.set_author(name=f"Category: {command.cog.qualified_name}")
                embed.set_footer(text=f"Do {prefix}help [command name] [subcommand name] to get help on a subcommand!")

                await ctx.send(embed=embed)

            else:
                return await send_embed(ctx, "Invalid category/command name", negative=True)

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def changelog(self, ctx):
        """Shows the changelog."""

        return await send_embed(ctx, self.content, info=True)

    @changelog.command(aliases=["edit"])
    @commands.is_owner()
    async def change(self, ctx, *, content):
        """Edit the changelog."""

        self.content = content
        await send_embed(ctx, "Changelog edited.")
