# Most of this comes from https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py

import asyncio

import discord
import youtube_dl
from discord.ext import commands

from bot.utils.format import send_embed

# Suppress errors
youtube_dl.utils.bug_reports_message = lambda: " "

format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


async def player_check(ctx):
    if not ctx.voice_client:
        return await send_embed(ctx, "Not connected to a voice channel.", negative=True)
    if not ctx.author.voice:
        return await send_embed(ctx, "You are not connected to a voice channel.", negative=True)
    if ctx.author.voice.channel != ctx.voice_client.channel:
        return await send_embed(ctx, "You are not connected to my voice channel.", negative=True)


class Music(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        global db
        db = self.bot.db

    @commands.group()
    @commands.guild_only()
    async def music(self, ctx):
        pass

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @music.command()
    @commands.guild_only()
    async def join(self, ctx):
        """Join a voice channel."""

        channel = ctx.author.voice.channel

        if not channel:
            await send_embed(ctx, "You are not currently connected to a voice channel.", negative=True)

        await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @music.command()
    @commands.guild_only()
    async def play(self, ctx, *, url):
        """Play from a youtube url."""

        player = await YTDLSource.from_url(url, loop=self.bot.loop)
        ctx.voice_client.play(player, lambda e: print(f"Error: {str(e)}") if e else None)

        await send_embed(ctx, f"Now playing **{player.title}**.", info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @music.command()
    @commands.guild_only()
    async def stream(self, ctx, *, url):
        """Stream from a url."""

        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, lambda e: print(f"Error: {str(e)}") if e else None)

        await send_embed(ctx, f"Now playing **{player.title}**.", info=True)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @music.command()
    @commands.guild_only()
    async def volume(self, ctx, volume: float):
        """Change the volume. Ranges from 0-100."""

        if player_check(ctx):
            return

        if volume < 0 or volume > 100:
            return await send_embed(ctx, "Invalid volume value.", negative=True)

        ctx.voice_client.source.volume = volume / 100
        await send_embed(ctx, f"Changed volume to {volume}")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @music.command()
    @commands.guild_only()
    async def pause(self, ctx):
        """Pause the music player."""

        if player_check(ctx):
            return

        if not ctx.voice_client.is_playing():
            return await send_embed(ctx, "Not playing anything.", negative=True)

        ctx.voice_client.pause()
        await send_embed(ctx, "Player paused.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @music.command()
    @commands.guild_only()
    async def resume(self, ctx):
        """Resumes the music player after pausing."""

        if player_check(ctx):
            return

        if not ctx.voice_client.is_paused():
            return await send_embed(ctx, "Player not paused.", negative=True)

        ctx.voice_client.resume()
        await send_embed(ctx, "Player resumed.")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @music.command(aliases=["dc"])
    async def disconnect(self, ctx):
        """Disconnect the music player."""

        if player_check(ctx):
            return

        await ctx.voice_client.disconnect()
        await send_embed(ctx, "Player disconnected.")

    @play.before_invoke
    @stream.before_invoke
    async def voice_connected(self, ctx):
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await send_embed(ctx, "You are not connected to a voice channel.", negative=True)

        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()
