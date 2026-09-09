import time
import discord
from discord.ext import commands

from config import load_json, save_json, admin_required, Manage_channels_required, Manage_messages_required,GUILD_IDS







class MainHelpInfo(commands.Cog):
    """Help command for the bot"""

    def __init__(self, client):
        self.bot = client
        



   






    





# Register Cog
async def setup(client: commands.Bot):
    await client.add_cog(MainHelpInfo(client))