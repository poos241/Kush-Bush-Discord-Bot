import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import re
import asyncio

voice_client = None

class PlayMusic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="play", description="Plays a YouTube video")
    async def play(self, ctx, query: str):
        global voice_client

        if ctx.author.voice is None:
            await ctx.respond("❌ You are not in a voice channel.")
            return

        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            voice_client = await voice_channel.connect()
        else:
            voice_client = ctx.voice_client

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0'
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                is_url = re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)', query)
                info = ydl.extract_info(query if is_url else f"ytsearch:{query}", download=False)

                if 'entries' in info:
                    info = info['entries'][0]

                title = info.get('title', 'Unknown Title')
                stream_url = info['url']
            except Exception as e:
                await ctx.respond(f"⚠️ Failed to extract video info: {e}")
                return

        ffmpeg_opts = {
            'options': '-vn'
        }

        source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
        voice_client.stop()
        voice_client.play(source)

        await ctx.respond(f"🎶 Now playing: **{title}**")

    @discord.slash_command(name="stop", description="Stops playback and leaves")
    async def stop(self, ctx):
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()
            await ctx.respond("🛑 Disconnected from the voice channel.")

    @discord.slash_command(name="pause", description="Pauses playback")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.respond("⏸️ Paused playback.")

    @discord.slash_command(name="resume", description="Resumes playback")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.respond("▶️ Resumed playback.")

    @discord.slash_command(name="volume", description="Sets the volume (1–100)")
    async def volume(self, ctx, volume: int):
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volume / 100.0
            await ctx.respond(f"🔊 Volume set to {volume}%")
        else:
            await ctx.respond("⚠️ Nothing is playing.")
            
            
    # Define a function to check if a YouTube video exists for the given query
    async def check_video(query):
        # Use YouTubeDL to search for videos on YouTube
        youtube_dl = YoutubeDL()
        search_results = await youtube_dl.search(query, max_results=1)

        # Check if any results were found
        if not search_results:
            return False

        # Get the first result (i.e., the only result) and check if it's a video...
        video = search_results[0]
        if not isinstance(video, dict) or "type" not in video:
            return False

        # Check if the video type is "video" (i.e., not a live stream)...
        if video["type"] != "video":
            return False

        # Return True if a YouTube video was found
        return True

    # Define a function to get the title of a YouTube video
    async def get_video_title(query):
        # Use YouTubeDL to search for videos on YouTube
        youtube_dl = YoutubeDL()
        search_results = await youtube_dl.search(query, max_results=1)

        # Get the first result (i.e., the only result) and get its title...
        video = search_results[0]
        return video["title"]

    # Define a function to get the URL of a YouTube video
    async def get_video_url(query):
        # Use YouTubeDL to search for videos on YouTube
        youtube_dl = YoutubeDL()
        search_results = await youtube_dl.search(query, max_results=1)

        # Get the first result (i.e., the only result) and get its URL...
        video = search_results[0]
        return video["urls"]["https://www.youtube.com/watch?v=" + video["id"]]

    # Define a function to get additional information about a YouTube video
    async def get_video_info(url):
        # Use YouTubeDL to download the YouTube video and get its metadata...
        youtube_dl = YoutubeDL()
        video_info = await youtube_dl.extract_info(url)

        # Return the video information as a dictionary
        return video_info

def setup(bot):
    bot.add_cog(PlayMusic(bot))
