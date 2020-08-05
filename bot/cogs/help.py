import json
from datetime import datetime

import discord
from discord.ext import commands

from bot.utils.message import send_embed, to_embed


class HelpCommand(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot
        db = self.bot.db
        self.content = "Multiple changes made."

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def help(self, ctx, *, name: str = None):
        """Get help on categories."""

        with open("prefixes.json", "r") as f:
            d = json.load(f)
            prefix = d[str(ctx.guild.id)]

        cogs = self.bot.cogs

        OWNER_COG_NAMES = []

        if ctx.author.id != 648741756384575509 or (not ctx.guild or ctx.guild.id != 732980515807952897):
            OWNER_COG_NAMES.append("SpreadSheets")

        if ctx.author.id != 648741756384575509:
            OWNER_COG_NAMES.append("Jishaku")
            OWNER_COG_NAMES.append("Owner")

        OWNER_COMMAND_NAMES = [i.qualified_name for i in self.bot.walk_commands() if i.cog and i.cog.qualified_name
                               in OWNER_COG_NAMES]

        cog_names_with_commands = [i for i in cogs.keys() if cogs[i].get_commands() and i not in OWNER_COG_NAMES]
        command_names = [i.qualified_name for i in self.bot.walk_commands() if
                         i.qualified_name not in OWNER_COMMAND_NAMES]

        if not name:
            value = [f"``{i}``\n" for i in cog_names_with_commands]

            # Albert
            author = str(self.bot.get_user(439228325722849290) or await self.bot.fetch_user(439228325722849290))

            embed = discord.Embed(
                title="Command Help",
                description=f"By {author}\n "
                            "```py\n"
                            f"Type {prefix}help [module name] for more information on a module. (Don't type the "
                            f"brackets) This also works for individual commands. Everything is case sensitive!"
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
                    value.append(f"{index}. ``{prefix}{command.qualified_name} {command.signature}``")

                    if index % 10 == 0 or index == len(cog.get_commands()):
                        embed = discord.Embed(
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
                    subcommands = ", ".join([f"``{i.name}``" for i in command.commands])
                except AttributeError:
                    subcommands = "None"

                aliases = ", ".join([f"``{i}``" for i in command.aliases]) if command.aliases else "None"

                description = f"**Subcommands: {subcommands}**\n" \
                              f"**Aliases: {aliases}**\n" \
                              f"\n" \
                              f"{command.help}"

                embed = discord.Embed(
                    title=f"{prefix}{command.qualified_name} {command.signature}",
                    description=description
                )

                embed.set_author(name=f"Category: {command.cog.qualified_name}")
                embed.set_footer(text=f"Do {prefix}help [command name] [subcommand name] to get help on a subcommand!")

                await ctx.send(embed=embed)

            else:
                return await send_embed(ctx, "Invalid category/command name", negative=True)

    @help.command()
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def all(self, ctx):
        """Get list of all commands and modules."""

        no_show_cogs = []

        if ctx.author.id != 648741756384575509:
            no_show_cogs.append("Owner")
            no_show_cogs.append("Jishaku")

        if ctx.author.id != 648741756384575509 or (not ctx.guild or ctx.guild.id != 732980515807952897):
            no_show_cogs.append("SpreadSheets")

        cogs = [i for i in self.bot.cogs if i not in no_show_cogs]
        commands = [i.qualified_name for i in self.bot.walk_commands() if i.cog and i.cog.qualified_name in cogs]

        description = []
        embeds = []

        for i, v in enumerate(cogs, start=1):
            description.append(f"{i}. {v}")
            if i % 10 == 0 or i == len(cogs):
                embed = discord.Embed(
                    title="Modules",
                    description="\n".join(description)
                )
                embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

                embeds.append(embed)
                description = []

        for i, v in enumerate(commands, start=1):
            description.append(f"{i}. {v}")
            if i % 10 == 0 or i == len(commands):
                embed = discord.Embed(
                    title="Commands",
                    description="\n".join(description)
                )
                embed.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

                embeds.append(embed)
                description = []

        await self.bot.paginate(ctx, embeds)

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

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Changelog Edited",
            description=content
        )
        embed.set_footer(text=datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))

        await self.bot.get_guild(732980515807952897).get_channel(736352506669694976).send(embed=embed)
