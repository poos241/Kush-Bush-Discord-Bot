# cogs/custom_dm_sender.py
import os
import json
import discord
from discord.ext import commands
from config import load_json, save_json, admin_required, OWNER_IDS, extra_help


DM_CONFIG_FILE = "dm_data.json"

class CustomDMSender(commands.Cog):
    """DM system for bot support/feedback"""

    def __init__(self, bot):
        self.bot = bot
        self.dm_settings = self.load_or_default()

    def load_or_default(self):
        if os.path.exists(DM_CONFIG_FILE):
            return load_json(DM_CONFIG_FILE)
        default = {
            "title": "Thanks for messaging us!",
            "description": "We've received your message and will review it soon.",
            "image_url": ""
        }
        save_json(DM_CONFIG_FILE, default)
        return default

    def save_settings(self):
        save_json(DM_CONFIG_FILE, self.dm_settings)

    def create_embed(self):
        embed = discord.Embed(
            title=self.dm_settings.get("title", ""),
            description=self.dm_settings.get("description", ""),
            color=discord.Color.green()
        )
        if self.dm_settings.get("image_url"):
            embed.set_image(url=self.dm_settings["image_url"])
        return embed

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is not None or message.author.bot:
            return

        owner = self.bot.get_user(OWNER_IDS)
        if owner:
            content = f"📩 **New DM from `{message.author}` `{message.author.display_name}` ({message.author.id})**\n```\n{message.content}\n```"
            await owner.send(content)

        await message.channel.send(embed=self.create_embed())

    @discord.slash_command(name="set_reply_embed", description="Set DM reply title & description")
    @extra_help("Set the title and description for the DM reply embed. Only the bot owner can use this command.")
    @admin_required()
    
    async def set_reply_embed(
        self,
        ctx: discord.ApplicationContext,
        title: discord.Option(str, "Title for the embed"),  # type: ignore
        description: discord.Option(str, "Description for the embed"),  # type: ignore
        url: discord.Option(str, "Direct image URL")  # type: ignore
    ):
        """Set the embed reply for DMs sent to the bot."""
        if ctx.user.id != OWNER_IDS:
            await ctx.respond("❌ You are not authorized.", ephemeral=True)
            return
        self.dm_settings["title"] = title
        self.dm_settings["description"] = description
        self.dm_settings["image_url"] = url
        self.save_settings()
        await ctx.respond("✅ Embed reply updated!", ephemeral=True)
        await ctx.respond("🖼️ Embed image set!", ephemeral=True)
        
    
def setup(bot):
    bot.add_cog(CustomDMSender(bot))
