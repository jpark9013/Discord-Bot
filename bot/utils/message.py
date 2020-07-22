from discord import Embed, Colour


async def send_embed(ctx, string, negative=False, info=False, question=False):
    if negative:
        await ctx.send(embed=Embed(colour=Colour.red(), description=f"❌ {string}"))

    elif info:
        await ctx.send(embed=Embed(colour=Colour.blue(), description=f"{string}"))

    elif question:
        await ctx.send(embed=Embed(colour=Colour.orange(), description=f"{string}"))

    else:
        await ctx.send(embed=Embed(colour=Colour.green(), description=f"✅ ***{string}***"))


async def to_embed(string, negative=False, info=False, question=False):
    if negative:
        return Embed(colour=Colour.red(), description=f"❌ {string}")

    elif info:
        return Embed(colour=Colour.blue(), description=f"{string}")

    elif question:
        return Embed(colour=Colour.orange(), description=f"{string}")

    else:
        return Embed(colour=Colour.green(), description=f"✅ ***{string}***")
