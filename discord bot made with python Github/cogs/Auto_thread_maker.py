import discord, random, io, asyncio
from discord.ext import commands
from discord.commands import Option
from config import admin_required, extra_help
from data.DB.Storage.storage import (
    get_threads_settings,
    save_threads_settings,
    get_active_tickets as get_active_threads,
    save_active_tickets as save_active_threads
)

class AutoThreadMaker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_media_message(self, msg: discord.Message) -> bool:
        media_ext = (".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".mov")
        has_attach = any(
            (att.content_type and att.content_type.startswith(("image/", "video/"))) or
            (att.filename and att.filename.lower().endswith(media_ext))
            for att in msg.attachments
        )
        has_embed = any(embed.image or embed.video or embed.thumbnail for embed in msg.embeds)
        return has_attach or has_embed

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not (message.guild and message.channel):
            return

        cfg = await get_threads_settings(str(message.guild.id))
        mode = cfg.get(str(message.channel.id))
        if not mode:
            return

        is_media = self.is_media_message(message)
        if mode == "media_only" and not is_media:
            try:
                fetched = await message.channel.fetch_message(message.id)
                is_media = self.is_media_message(fetched)
            except:
                return

        if mode == "all_messages" or (mode == "media_only" and is_media):
            try:
                display = message.author.display_name
                thread = await message.channel.create_thread(
                    name=f"{display} • {message.guild.name}",
                    message=message,
                    auto_archive_duration=60
                )
                await thread.send(f"💬 Welcome to {message.author.mention}'s thread!")

                # Track in DB
                threads = await get_active_threads(str(message.guild.id))
                threads[str(message.id)] = thread.id
                await save_active_threads(str(message.guild.id), threads)
            except Exception as e:
                print("Thread error:", e)

    @discord.slash_command(name="auto_thread_add", description="Add auto-thread channel")
    @extra_help("Set channel to auto-thread: media_only or all_messages.")
    @admin_required()
    async def auto_thread_add(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.TextChannel, "Channel"), # type: ignore
        mode: Option(str, "Mode", choices=["media_only","all_messages"]) # type: ignore
    ):
        cfg = await get_threads_settings(str(ctx.guild.id))
        cfg[str(channel.id)] = mode
        cfg["guild_name"] = ctx.guild.name
        await save_threads_settings(str(ctx.guild.id), cfg)
        await ctx.respond(f"✅ {channel.mention} set to `{mode}`", ephemeral=True)

    @discord.slash_command(name="auto_thread_remove", description="Remove auto-thread channel")
    @extra_help("Stop auto-threading in a channel.")
    @admin_required()
    async def auto_thread_remove(
        self, ctx: discord.ApplicationContext,
        channel: Option(discord.TextChannel,"Channel to remove") # type: ignore
    ):
        cfg = await get_threads_settings(str(ctx.guild.id))
        if cfg.pop(str(channel.id), None) is not None:
            await save_threads_settings(str(ctx.guild.id), cfg)
            await ctx.respond(f"🗑️ Removed {channel.mention}", ephemeral=True)
        else:
            await ctx.respond("❌ That channel wasn't set.", ephemeral=True)

    @discord.slash_command(name="auto_thread_list", description="List auto-thread channels")
    @extra_help("Shows all channels configured for auto-thread.")
    @admin_required()
    async def auto_thread_list(self, ctx: discord.ApplicationContext):
        cfg = await get_threads_settings(str(ctx.guild.id))
        if not any(k.isdigit() for k in cfg):
            return await ctx.respond("⚠️ None configured.", ephemeral=True)
        lines = []
        for cid, mode in cfg.items():
            if not cid.isdigit(): continue
            lines.append(f"<#{cid}> → `{mode}`")
        await ctx.respond("📌 Auto-thread settings:\n" + "\n".join(lines), ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        threads = await get_active_threads(str(msg.guild.id))
        tid = threads.pop(str(msg.id), None)
        if not tid: return
        await save_active_threads(str(msg.guild.id), threads)
        try:
            thread = msg.guild.get_thread(int(tid))
            if thread:
                await thread.delete()
        except Exception as e:
            print("Thread cleanup error:", e)

def setup(client):
    client.add_cog(AutoThreadMaker(client))
