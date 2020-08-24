from discord import Embed, Colour


async def send_embed(ctx, string, negative=False, info=False, question=False):

    try:
        string = str(string)
    except Exception as e:
        print(e)

    if negative:
        await ctx.send(embed=Embed(colour=Colour.red(), description=f"<:cancel:739585812290732103> {string}"))

    elif info:
        await ctx.send(embed=Embed(colour=Colour.blue(), description=string))

    elif question:
        await ctx.send(embed=Embed(colour=Colour.orange(), description=string))

    else:
        await ctx.send(embed=Embed(colour=Colour.green(), description=f"<:check:739585649744674896> ***{string}***"))


def to_embed(string, negative=False, info=False, question=False):

    try:
        string = str(string)
    except Exception as e:
        print(e)

    if negative:
        return Embed(colour=Colour.red(), description=f"<:cancel:739585812290732103> {string}")

    elif info:
        return Embed(colour=Colour.blue(), description=string)

    elif question:
        return Embed(colour=Colour.orange(), description=string)

    else:
        return Embed(colour=Colour.green(), description=f"<:check:739585649744674896> ***{string}***")


def to_datetime(seconds: int, day=True, week=False):
    if day:
        d, remainder = divmod(seconds, 86400)
        h, remainder = divmod(remainder, 3600)
        m, s = divmod(remainder, 60)

        d = int(d)
        h = int(h)
        m = int(m)
        s = int(s)

        if d:
            return f"{d}d {h}h {m}m {s}s"
        else:
            return f"{h}h {m}m {s}s"

    elif week:
        w, remainder = divmod(seconds, 604800)
        d, remainder = divmod(remainder, 86400)
        h, remainder = divmod(remainder, 3600)
        m, s = divmod(remainder, 60)

        w = int(w)
        d = int(d)
        h = int(h)
        m = int(m)
        s = int(s)

        if w:
            return f"{w}w {d}d {h}h {m}m {s}s"
        elif d:
            return f"{d}d {h}h {m}m {s}s"
        else:
            return f"{h}h {m}m {s}s"

    else:
        h, remainder = divmod(seconds, 3600)
        m, s = divmod(remainder, 60)

        h = int(h)
        m = int(m)
        s = int(s)

        if h:
            return f"{h}h {m}m {s}s"
        else:
            return f"{m}m {s}s"


def shorten(text: str, length: int = 1024):
    if len(text) > length:
        text = ("".join(list(text)[:1024])).split()
        if len(text[-1]) < 3:
            del text[-1]
        text[-1] = "..."
        return " ".join(text)

    return text
