import discord
from discord.ext import commands
import time
from config import load_json, save_json, admin_required, GUILD_IDS, extra_help
import asyncio



class VCCog(commands.Cog):
    def __init__(self, client):
        self.bot = client
        self.setting_vc_sttings = load_json("vc_settings.json")
        self.setting_temp_voice_channels = load_json("temp_voice_channels.json")
        self.setting_user_temp_vc_map = load_json("user_temp_vc_map.json")
        self.setting_main_vc_map = load_json("main_vc_map.json")
        

    ##vc_settings = load_vc_settings()
    ##temp_voice_channels = load_data()
    ##user_temp_vc_map = load_user_vc_map()
    ##main_vc_map = load_main_vc_map()



    cooldownVC = {}
    COOLDOWN_SECONDS_vc1 = 60
    COOLDOWN_SECONDS_vc2 = 10
    COOLDOWN_SECONDS_vc3 = 5

    
    async def recover_temp_vcs(self):

        for vc_id, data in list(self.setting_temp_voice_channels.items()):

            guild = self.bot.get_guild(data["guild_id"])

            if guild is None:
                continue

            channel = guild.get_channel(int(vc_id))

            if channel is None:
                # Deleted while bot offline
                self.setting_temp_voice_channels.pop(vc_id)
                continue

            if len(channel.members) == 0:
                await channel.delete()
                self.setting_temp_voice_channels.pop(vc_id)

                owner = str(data["owner_id"])
                self.setting_user_temp_vc_map.pop(owner, None)

        save_json("temp_voice_channels.json", self.setting_temp_voice_channels)

    ##print(f"[DEBUG] Moved {member.name} to their own VC.")
    @commands.Cog.listener()
    async def on_voice_state_update(self,member, before, after):
        
        await self.recover_temp_vcs()
        user_id = str(member.id)
        guild = member.guild
        guild_id = str(guild.id)
        now = time.time()
        cooldownVC = {}
        COOLDOWN_SECONDS_vc1 = 60
        # --- DELETE EMPTY TEMP VC ---
        if before.channel:
            vc_id = str(before.channel.id)
            if vc_id in self.setting_temp_voice_channels and len(before.channel.members) == 0:
                await before.channel.delete()
                del self.setting_temp_voice_channels[vc_id]
                save_json("temp_voice_channels.json", self.setting_temp_voice_channels)

                for uid, cid in list(self.setting_user_temp_vc_map.items()):
                    if cid == vc_id:
                        del self.setting_user_temp_vc_map[uid]
                        save_json("user_temp_vc_map.json", self.setting_user_temp_vc_map)
                        break

        # --- ONLY CONTINUE IF JOINED MAIN VC ---
        if after.channel is None:
            return

        guild_main_vc = self.setting_main_vc_map.get(guild_id)
        if not guild_main_vc:
            return

        main_vc_id = guild_main_vc.get("main_vc_id")
        if not main_vc_id or str(after.channel.id) != str(main_vc_id):
            return

        # --- CLEANUP STALE ENTRY IF NEEDED ---
        if user_id in self.setting_user_temp_vc_map:
            old_vc = guild.get_channel(int(self.setting_user_temp_vc_map[user_id]))
            if old_vc is None:
                del self.setting_user_temp_vc_map[user_id]
                save_json("temp_voice_channels.json", self.setting_user_temp_vc_map)
            else:
                return  # User already has a valid VC

        # --- COOLDOWN CHECK ---
        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}

        if user_id in cooldownVC[guild_id]:
            elapsed = now - cooldownVC[guild_id][user_id]
            if elapsed < COOLDOWN_SECONDS_vc1:
                remaining = round(COOLDOWN_SECONDS_vc1 - elapsed, 1)
                embed = discord.Embed(
                    title="⏳ You're on cooldown!",
                    description=f"<@{user_id}>, wait **{remaining} seconds** before creating another VC.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Voice Channel System")

                # Try to send to configured message channel
                settings = self.setting_main_vc_map.get(guild_id, {})
                msg_sent = False

                if settings.get("message_channel"):
                    chan = guild.get_channel(int(settings["message_channel"]))
                    if isinstance(chan, discord.TextChannel):
                        await chan.send(embed=embed)
                        msg_sent = True

                if settings.get("dm_users", False):
                    try:
                        await member.send(embed=embed)
                        msg_sent = True
                    except discord.Forbidden:
                        pass

                if not msg_sent:
                    print(f"[WARN] Could not notify {member.display_name} of cooldown.")

                return

        cooldownVC[guild_id][user_id] = now

        # --- CREATE TEMP VC + MOVE USER ---
        settings = self.setting_main_vc_map.get(guild_id, {})

        category_id = settings.get("main_category_id")
        category = None
        if category_id:
            category = guild.get_channel(int(category_id))
        if not isinstance(category, discord.CategoryChannel):
            category = None  # Just in case the ID points to something else

        # Create the temp VC under the category (or top-level if category is None)
        temp_vc = await guild.create_voice_channel(f"{member.display_name}'s VC", category=category)
        await member.move_to(temp_vc)

        vc_id = str(temp_vc.id)
        expires_at = now + 300

        self.setting_temp_voice_channels[vc_id] = {
            "guild_id": guild.id,
            "owner_id": member.id,
            "created_at": now,
            "expires_at": expires_at,
            "locked": False,
            "allowed_users": [],
            "user_limit": None
        }

        self.setting_user_temp_vc_map[user_id] = vc_id
        save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
        


        # --- NOTIFY CREATION IN TEXT CHANNEL ---
        embed = discord.Embed(
            title="✅ VC Created",
            description=f"<@{user_id}> has been moved to their own voice channel: **{temp_vc.name}**.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Voice Channel System")

        settings = self.setting_main_vc_map.get(guild_id, {})
        if settings.get("message_channel"):
            chan = guild.get_channel(int(settings["message_channel"]))
            if isinstance(chan, discord.TextChannel):
                await chan.send(embed=embed)

        if settings.get("dm_users", False):
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                pass













    @discord.slash_command(name="createvc", description = "this is used to let a user make a vc for talking. lets you make a vc with a 60 sec cooldown", ) # type: ignore
    @extra_help("Create a temporary voice channel for yourself. You can only have one active VC at a time. Cooldown: 60 seconds.")
    @admin_required()
    async def create_temp_vc(
        self, 
        interaction: discord.ApplicationContext, # type: ignore
        *, 
        name: str
        ):
        """Create a temporary voice channel for yourself. You can only have one active VC at a time. Cooldown: 60 seconds.""" # type: ignore
        await interaction.response.defer()
        user_id = str(interaction.author.id)
        guild = interaction.guild
        guild_id = str(guild.id)
        now = time.time()
        cooldownVC = {}
        COOLDOWN_SECONDS_vc1 = 60
        
        
        if user_id in self.setting_user_temp_vc_map:
            existing_vc_id = self.setting_user_temp_vc_map[user_id]
            vc = guild.get_channel(int(existing_vc_id))
            if vc:
                await interaction.followup.send(f"❌ You already have a VC: `{vc.name}`.")
                return
            else:
                del self.setting_user_temp_vc_map[user_id]
                save_json("user_temp_vc_map.json", self.setting_user_temp_vc_map)

        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}
        user_cooldowns = cooldownVC[guild_id]

        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_vc1:
                await interaction.followup.send(f"⏳ Cooldown: Try again in {round(COOLDOWN_SECONDS_vc1 - elapsed, 1)}s.")
                return

        user_cooldowns[user_id] = now
        settings = self.setting_main_vc_map.get(guild_id, {})
        
        
        category_id = settings.get("main_category_id")
        category = None
        if category_id:
            category = guild.get_channel(int(category_id))
        if not isinstance(category, discord.CategoryChannel):
            category = None
        temp_vc = await guild.create_voice_channel(name, category=category)
        await interaction.followup.send(f"✅ Temporary VC `{name}` created!")

        vc_id = str(temp_vc.id)
        expires_at = now + 300

        self.setting_temp_voice_channels[vc_id] = {
            "guild_id": guild.id,
            "owner_id": interaction.author.id,
            "created_at": now,
            "expires_at": expires_at,
            "locked": False,
            "allowed_users": [],
            "user_limit": None
        }
        self.setting_user_temp_vc_map[user_id] = vc_id
        save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
        save_json("user_temp_vc_map.json", self.setting_user_temp_vc_map)

        # Schedule a 5-minute check if user hasn't joined
        asyncio.create_task(remove_if_user_does_not_join(interaction.author, temp_vc, delay=300)) 
        
        async def remove_if_user_does_not_join(user, vc, delay=300):
            await asyncio.sleep(delay)
            if not vc.members:
                await vc.delete(reason="User didn't join within 5 minutes")
                self.setting_temp_voice_channels.pop(str(vc.id), None)
                self.setting_user_temp_vc_map.pop(str(user.id), None)
                save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
                save_json("user_temp_vc_map.json", self.setting_user_temp_vc_map)



    


    @discord.slash_command(name="set_up_vcmaker", description="Assigns the main voice channel and category for temporary VC creation")
    @extra_help("Set up the main voice channel and category for temporary VC creation. This is where users will join to trigger the temp VC system.")
    @admin_required()
    async def set_up_vcmaker(
        self,
        interact: discord.ApplicationContext, # type: ignore
        vc: discord.Option(discord.VoiceChannel, "The main voice channel users will join to trigger temp VC"), # type: ignore
        category: discord.Option(discord.CategoryChannel, "The category where temp VCs will be created"), # type: ignore
        channel: discord.Option(discord.TextChannel, "The text channel where VC system messages will be sent"), # type: ignore
        dm_users: discord.Option(bool, "Pick True or False to set if users get a DM when making a VC", default=False) # type: ignore
    ):
        """Assigns the main voice channel and category for temporary VC creation. This is where users will join to trigger the temp VC system.""" # type: ignore
        guild_id = str(interact.guild.id)
        guild_name = str(interact.guild.name)

        self.setting_main_vc_map[guild_id] = {
            "guild_name": guild_name,
            "main_vc_id": str(vc.id),
            "main_category_id": str(category.id),
            "message_channel": str(channel.id),
            "dm_users": dm_users
        }

        save_json("main_vc_map.json", self.setting_main_vc_map)

        await interact.respond(
            f"✅ Main VC set to `{vc.name}`, main category set to `{category.name}`.\n"
            f"✅ VC system messages will be sent in {channel.mention}. DMs **{'enabled' if dm_users else 'disabled'}** for **{guild_name}**.",
            ephemeral=True
        )



    # Lock command
    @discord.slash_command(name="lock", description= "using this lets the owner of the VC lock the vc so no one but admins and owner can get in")
    @extra_help("Lock your voice channel so only you and admins can join. Cooldown: 60 seconds.")
    async def lock_channel(
        self, 
        interaction: discord.ApplicationContext
        ):
        """Lock your voice channel so only you and admins can join. Cooldown: 60 seconds."""
        await interaction.response.defer()
        user_id = interaction.author.id
        guild_id = interaction.guild.id
        now = time.time()
        cooldownVC = {}
        COOLDOWN_SECONDS_vc1 = 60
        # Ensure guild key exists
        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}

        # Reference the user_cooldowns for this guild
        user_cooldowns = cooldownVC[guild_id]

        # Check cooldown
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_vc1:
                remaining = round(COOLDOWN_SECONDS_vc1 - elapsed, 1)
                await interaction.followup.send(f"⏳ You're on cooldown {interaction.author.mention}! Try again in {remaining} seconds.")
                return

        # Set new cooldown
        user_cooldowns[user_id] = now
        voice_state = interaction.author.voice
        if voice_state and voice_state.channel:
            channel = voice_state.channel
            channel_data = self.setting_temp_voice_channels.get(str(channel.id))
            if channel_data and channel_data["owner_id"] == interaction.author.id:
                overwrite = discord.PermissionOverwrite(connect=False)
                await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
                channel_data["locked"] = True
                save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
                await interaction.send(f"Channel `{channel.name}` is now locked.")

    # Unlock command
    @discord.slash_command(name="unlock", description= "using this lets the over of the VC unlock it for anyone to join")
    @extra_help("Unlock your voice channel so anyone can join. Cooldown: 60 seconds.")
    async def unlock_channel(
        self, 
        interaction: discord.ApplicationContext
        ): 
        """Unlock your voice channel so anyone can join. Cooldown: 60 seconds.""" # type: ignore
        await interaction.response.defer()
        user_id = interaction.author.id
        guild_id = interaction.guild.id
        now = time.time()
        cooldownVC = {}
        COOLDOWN_SECONDS_vc1 = 60
        # Ensure guild key exists
        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}

        # Reference the user_cooldowns for this guild
        user_cooldowns = cooldownVC[guild_id]

        # Check cooldown
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_vc1:
                remaining = round(COOLDOWN_SECONDS_vc1 - elapsed, 1)
                await interaction.followup.send(f"⏳ You're on cooldown {interaction.author.mention}! Try again in {remaining} seconds.")
                return

        # Set new cooldown
        user_cooldowns[user_id] = now
        voice_state = interaction.author.voice
        if voice_state and voice_state.channel:
            channel = voice_state.channel
            channel_data = self.setting_temp_voice_channels.get(str(channel.id))
            if channel_data and channel_data["owner_id"] == interaction.author.id:
                await channel.set_permissions(interaction.guild.default_role, overwrite=None)
                channel_data["locked"] = False
                save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
                await interaction.send(f"Channel `{channel.name}` is now unlocked.")

    # Allow command
    @discord.slash_command(name="allow", description= "using this lets the owner of the VC invite members they want in the VC ")
    @extra_help("Allow a specific user to join your voice channel. Cooldown: 10 seconds.")
    async def allow_user(
        self,
        interaction: discord.ApplicationContext, # type: ignore 
        user: discord.Option(discord.Member, "pick the user you wish to not allow in your VC") # type: ignore
        ):
        """Allow a specific user to join your voice channel. Cooldown: 10 seconds.""" # type: ignore
        await interaction.response.defer()
        user_id = interaction.author.id
        guild_id = interaction.guild.id
        now = time.time()
        cooldownVC = {}
        COOLDOWN_SECONDS_vc2 = 10
        # Ensure guild key exists
        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}

        # Reference the user_cooldowns for this guild
        user_cooldowns = cooldownVC[guild_id]

        # Check cooldown
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_vc2:
                remaining = round(COOLDOWN_SECONDS_vc2 - elapsed, 1)
                await interaction.followup.send(f"⏳ You're on cooldown {interaction.author.mention}! Try again in {remaining} seconds.")
                return

        # Set new cooldown
        user_cooldowns[user_id] = now
        voice_state = interaction.author.voice
        if voice_state and voice_state.channel:
            channel = voice_state.channel
            channel_data = self.setting_temp_voice_channels.get(str(channel.id))
            if channel_data and channel_data["owner_id"] == interaction.author.id:
                overwrite = discord.PermissionOverwrite(connect=True)
                await channel.set_permissions(user, overwrite=overwrite)
                if user.id not in channel_data["allowed_users"]:
                    channel_data["allowed_users"].append(user.id)
                save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
                await interaction.send(f"{user.display_name} has been allowed to join `{channel.name}`.")

    # Unallow command
    @discord.slash_command(name="unallow", description= "using this lets the owner of the VC remove members from the VC they nolonger want in there")
    @extra_help("Unallow a specific user from joining your voice channel. Cooldown: 5 seconds.")
    async def unallow_user(
        self,
        interaction: discord.ApplicationContext, # type: ignore
        user: discord.Option(discord.Member, "pick the user you wish to not unallow in your VC") # type: ignore
        ):
        """Unallow a specific user from joining your voice channel. Cooldown: 5 seconds.""" # type: ignore
        await interaction.response.defer()
        user_id = interaction.author.id
        guild_id = interaction.guild.id
        now = time.time()
        cooldownVC = {}
        COOLDOWN_SECONDS_vc3 = 5
        # Ensure guild key exists
        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}

        # Reference the user_cooldowns for this guild
        user_cooldowns = cooldownVC[guild_id]

        # Check cooldown
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_vc3:
                remaining = round(COOLDOWN_SECONDS_vc3 - elapsed, 1)
                await interaction.followup.send(f"⏳ You're on cooldown {interaction.author.mention}! Try again in {remaining} seconds.")
                return

        # Set new cooldown
        user_cooldowns[user_id] = now
        voice_state = interaction.author.voice
        if voice_state and voice_state.channel:
            channel = voice_state.channel
            channel_data = self.setting_temp_voice_channels.get(str(channel.id))
            if channel_data and channel_data["owner_id"] == interaction.author.id:
                await channel.set_permissions(user, overwrite=None)
                if user.id in channel_data["allowed_users"]:
                    channel_data["allowed_users"].remove(user.id)
                save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
                await interaction.send(f"{user.display_name} has been unallowed from `{channel.name}`.")



    @discord.slash_command(name= "renamevc", description= "using this lets the owner of the VC change the name of the VC", guild_ids=GUILD_IDS)
    @extra_help("Change the name of your VC")
    async def renamevc(self, ctx, *, new_name: str):
        # Check if the user is connected to a voice channel
        if ctx.author.voice and ctx.author.voice.channel:
            voice_channel = ctx.author.voice.channel
            
            try:
                # Edit the channel name
                await voice_channel.edit(name=new_name)
                await ctx.send(f"Successfully renamed the voice channel to: **{new_name}**")
            except discord.errors.HTTPException as e:
                await ctx.send("Failed to rename. Please make sure I have the 'Manage Channels' permission and wait a few minutes before trying again.")
        else:
            await ctx.send("You must be in a voice channel to use this command!")


    




    # Set User Limit command
    @discord.slash_command(name="setlimit", description= "using this lets the owner of the VC set a limit of the number of users that can join the vc.")
    @extra_help("Set a user limit for your voice channel. Cooldown: 60 seconds.")
    async def set_user_limit(
        self,
        intraction: discord.ApplicationContext, # type: ignore 
        limit: discord.Option(int, "set the number of users that can join the VC") # type: ignore
        ):
        """Set a user limit for your voice channel. Cooldown: 60 seconds.""" # type: ignore
        await intraction.response.defer()
        user_id = intraction.author.id
        guild_id = intraction.guild.id
        now = time.time()
        cooldownVC = {}
        COOLDOWN_SECONDS_vc1 = 60
        # Ensure guild key exists
        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}

        # Reference the user_cooldowns for this guild
        user_cooldowns = cooldownVC[guild_id]

        # Check cooldown
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_vc1:
                remaining = round(COOLDOWN_SECONDS_vc1 - elapsed, 1)
                await intraction.followup.send(f"⏳ You're on cooldown {intraction.author.mention}! Try again in {remaining} seconds.")
                return

        # Set new cooldown
        user_cooldowns[user_id] = now
        voice_state = intraction.author.voice
        if voice_state and voice_state.channel:
            channel = voice_state.channel
            channel_data = self.setting_temp_voice_channels.get(str(channel.id))
            if channel_data and channel_data["owner_id"] == intraction.author.id:
                await channel.edit(user_limit=limit)
                channel_data["user_limit"] = limit
                save_json("setting_temp_voice_channels.json", self.setting_temp_voice_channels)
                await intraction.send(f"User limit for `{channel.name}` set to {limit}.")

    # Combined Command: Manage VC


'''





    @client.slash_command(name="managevc", description="used by a mod to make a VC with commands", guild_id=GUILD_IDS)
    @admin_required()
    async def manage_vc(
        ctx, 
        name: discord.Option(str, "use this to name your VC"), # type: ignore 
        lock: discord.Option(bool, "use this to set if you want to lock the VC or not", default = False), #type: ignore 
        user_limit: discord.Option(int, "use this to set the limit of users in the VC 1-100", default = 0), # type: ignore 
        user1: discord.Option(discord.Member, "pick user 1" ,default= None), # type: ignore 
        user2: discord.Option(discord.Member, "pick user 2" ,default= None), # type: ignore
        user3: discord.Option(discord.Member, "pick user 3" ,default= None), # type: ignore
        user4: discord.Option(discord.Member, "pick user 4" ,default= None), # type: ignore
        user5: discord.Option(discord.Member, "pick user 5" ,default= None), # type: ignore
        user6: discord.Option(discord.Member, "pick user 6" ,default= None), # type: ignore
        user7: discord.Option(discord.Member, "pick user 7" ,default= None), # type: ignore
        user8: discord.Option(discord.Member, "pick user 8" ,default= None), # type: ignore
        user9: discord.Option(discord.Member, "pick user 9" ,default= None), # type: ignore
        user10: discord.Option(discord.Member, "pick user 10" ,default= None), # type: ignore
    ):
        await ctx.response.defer()
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        now = time.time()

        # Ensure guild key exists
        if guild_id not in cooldownVC:
            cooldownVC[guild_id] = {}

        # Reference the user_cooldowns for this guild
        user_cooldowns = cooldownVC[guild_id]

        # Check cooldown
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_vc1:
                remaining = round(COOLDOWN_SECONDS_vc1 - elapsed, 1)
                await ctx.followup.send(f"⏳ You're on cooldown {ctx.author.mention}! Try again in {remaining} seconds.")
                return

        # Set new cooldown
        user_cooldowns[user_id] = now
        guild = ctx.guild
        
        settings = main_vc_map.get(guild_id, {})
        
        category_id = settings.get("main_category_id")
        category = None
        if category_id:
            category= guild.get_channel(int(category_id))
            
        if not isinstance(category, discord.CategoryChannel):
            category = None
        
        temp_vc = await guild.create_voice_channel(name, category=category, user_limit=user_limit)
        
        
        # Apply lock if specified
        if lock:
            overwrite = discord.PermissionOverwrite(connect=False)
            await temp_vc.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        # Allow specific users if provided
        allowed_users_ids = []
        for user in [user1, user2, user3, user4, user5, user6, user7, user8, user9, user10, ]:
            if user:
                overwrite = discord.PermissionOverwrite(connect=True)
                await temp_vc.set_permissions(user, overwrite=overwrite)
                allowed_users_ids.append(user.id)

        # Save the channel data
        temp_voice_channels[str(temp_vc.id)] = {
            "guild_id": guild.id,
            "owner_id": ctx.author.id,
            "locked": lock,
            "allowed_users": allowed_users_ids,
            "user_limit": user_limit
        }
        save_data(temp_voice_channels)
        await ctx.followup.send(f"Temporary voice channel `{name}` created!")
'''
def setup(client):
    client.add_cog(VCCog(client))

########## Voice chat things ##########