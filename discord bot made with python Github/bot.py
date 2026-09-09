# bot.py
import asyncio
import os
import random
from dotenv import load_dotenv
import discord
from discord.ext import commands
from cogs.Ticket_system import ClaimView, TicketPanelView
from config import GUILD_IDS, statuses, load_json, save_json, admin_required, OWNER_IDS
from data.DB.Storage.storage import get_ticket_config  # ✅ Make sure this is imported
from cogs.Ticket_system import TicketPanelView  # ✅ Adjust the path if needed



import datetime as DT
from pathlib import Path
import ast
import json
# Load token
load_dotenv()
TOKEN = os.getenv("TOKEN2")

# Intents
intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())
client.help_categories = {}







# Load cogs
COGS = [
    "cogs.admin_cog",
    "cogs.welcome",
    "cogs.vc",
    ##"cogs.Level_system", ## this still need more work to make it work better.
    "cogs.Fun_thing_games",
    "cogs.Ticket_system",
    ##"cogs.Auto_thread_maker", this was broekn and really needs to be fixed to make sure it works.
    ##"cogs.Custom_DM_sender_help", 
    ##"cogs.Play_music", don't really see a point to play music over discord. 
    "cogs.db_tools",
    ##"cogs.emuvr",
    ##"cogs.economy_games", needs more work before it's something worth putting out there.
    "cogs.Event_maker", 
    "cogs.VRChat",
    ##"cogs.Logger",
    ##"cogs.Love",
    ##"cogs.Reminder",
    
    
    ##"cogs.OSRS_System",
    
    
    "cogs.Help_Info_Doc",
]

for cog in COGS:
    client.load_extension(cog)

client.load_extension("cogs.Logger")







@client.event
async def on_message(message):
    if message.guild is None and not message.author.bot:
        if message.content.lower() == "hi":
            await message.channel.send("Hello 👋 I work in DMs too!")
    await client.process_commands(message)  # let commands still run





@client.event
async def change_status():
                while True:
                    # Choose a random status
                    status = random.choice(statuses)
                    # Set the bot's status
                    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))  # Corrected line
                    # Wait for a random amount of time (between 10 and 60 seconds)
                    await asyncio.sleep(random.randint(10, 60))




@client.event
async def on_ready():
    print("🔄 Loading persistent ticket views...")
    for guild in client.guilds:
        config = await get_ticket_config(guild.id)
        if not config:
            continue

        panel = config.get("ticket_panel")
        if panel and "buttons" in panel:
            client.add_view(TicketPanelView(panel["buttons"], guild.id))  # ✅ Persistent view
            print(f"🔁 Loaded ticket panel for guild: {guild.name} ({guild.id})")


    # ✅ Once-only setup
    ##print("📦 Persistent ticket views loaded and registered.")
    await client.sync_commands(force=True)
    currentDT = DT.datetime.now()
    
    print(f"✅ Logged in as {client.user} (id: {client.user.id}) Commands synced! Time: {currentDT.strftime('%Y-%m-%d %H:%M:%S')}")
    
    
    # ✅ Start any background tasks
    client.loop.create_task(change_status())

    
    
    
if __name__ == "__main__":
    client.run(TOKEN)
