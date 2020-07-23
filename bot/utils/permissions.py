import discord
from discord.ext import commands


def is_above(ctx, member):
    if ctx.author == ctx.guild.owner:
        return True
    if member == ctx.guild.owner:
        return True

    return ctx.author.top_role.position > member.top_role.position

