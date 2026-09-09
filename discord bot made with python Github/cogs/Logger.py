import asyncio
from asyncio import tasks
from collections import defaultdict
from datetime import datetime
from http import client
import discord
from discord.ext import commands
from config import GUILD_IDS, statuses, load_json, save_json, admin_required, OWNER_IDS
import discord, random, time, json, os
from discord.ext import commands, tasks
from collections import defaultdict
import datetime
import asyncio  # Make sure to import asyncio for timeout handling
import random
from  discord.ext import commands,tasks
import datetime
import sqlite3
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
import time
from collections import defaultdict



LOG_CONFIG_FILE = "logger_log_channels.json"
LOG_ARCHIVE_FILE = "logger_log_archive.json"

class Logger(commands.Cog):
    def __init__(self, client):
        self.bot = client


    

        def ensure_file_exists(path, default):
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump(default, f, indent=4)

        def load_json(path):
            ensure_file_exists(path, {})
            with open(path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}

        def save_json(path, data):
            with open(path, "w") as f:
                json.dump(data, f, indent=4)

        def get_log_channels():
            return load_json(LOG_CONFIG_FILE)

        def set_log_channel(guild_id, channel_id):
            data = get_log_channels()
            data[str(guild_id)] = channel_id
            save_json(LOG_CONFIG_FILE, data)

        def get_log_channel(guild_id):
            return get_log_channels().get(str(guild_id))

        def archive_log_entry(guild_id, entry):
            archives = load_json(LOG_ARCHIVE_FILE)
            gid = str(guild_id)
            if gid not in archives:
                archives[gid] = []
            archives[gid].append(entry)
            save_json(LOG_ARCHIVE_FILE, archives)

        CONFIG_FILE = "config.json"

        def load_config():
            if not os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'w') as f:
                    json.dump({}, f)
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)

        def save_config(config):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)

        def get_guild_config(guild_id):
            config = load_config()
            return config.get(guild_id, {})

        def update_guild_config(guild_id, key, value):
            config = load_config()
            if guild_id not in config:
                config[guild_id] = {}
            config[guild_id][key] = value
            save_config(config)

        config = load_config()



        log_preferences = {}
        voice_state_cache = defaultdict(lambda: {"last_change": None})




        def build_attachment_text(attachments):
            return "\n".join([f"[{a.filename}]({a.url})" for a in attachments]) or "None"








    


        cooldown_setup_logs = {}
        COOLDOWN_SECONDS_setup_logs= 60
        @discord.slash_command(name="setup_logs", description="Used by the admins to setup logging in the discord", guild_ids=GUILD_IDS)
        @admin_required()
        async def setup_logs(ctx):
            def check_msg(m): return m.author == ctx.author and m.channel == ctx.channel
            await ctx.response.defer()

            user_id = ctx.author.id
            now = time.time()
            
            if user_id in cooldown_setup_logs:
                elapsed = now - cooldown_setup_logs[user_id]
                if elapsed < COOLDOWN_SECONDS_setup_logs:
                    remaining = round(COOLDOWN_SECONDS_setup_logs - elapsed, 1)
                    await ctx.followup.send(f"⏳ You're on cooldown {ctx.author.mention}! Try again in {remaining} seconds.")
                    return
            # Save the current timestamp as the last use time
            cooldown_setup_logs[user_id] = now
            await ctx.send("Do you already have a log channel? (yes/no)")
            try:
                msg = await client.wait_for("message", timeout=30.0, check=check_msg)
            except asyncio.TimeoutError:
                return await ctx.send("⏰ Setup timed out.")

            if msg.content.lower() in ["yes", "y"]:
                await ctx.send("Mention the channel you want to use (e.g., #logs):")
                try:
                    msg2 = await client.wait_for("message", timeout=30.0, check=check_msg)
                    if msg2.channel_mentions:
                        chosen = msg2.channel_mentions[0]
                        set_log_channel(ctx.guild.id, chosen.id)
                        return await ctx.send(f"✅ Set {chosen.mention} as log channel.")
                    else:
                        return await ctx.send("❌ No valid channel mentioned.")
                except asyncio.TimeoutError:
                    return await ctx.send("⏰ Setup timed out.")
            else:
                category = await ctx.guild.create_category("Logs")
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
                    ctx.author: discord.PermissionOverwrite(read_messages=True),
                }
                log_chan = await ctx.guild.create_text_channel("log-archive", category=category, overwrites=overwrites)
                ##log_chan= await ctx.guid.creat_text_channel("role-logs", category=category, overwrites=overwrites)
                set_log_channel(ctx.guild.id, log_chan.id)
                await ctx.send(f"📁 Created {log_chan.mention} for logging.")


        @discord.slash_command(name="change_logchannel", description="Change the logging channel for the server", guild_ids=GUILD_IDS)
        @admin_required()
        async def change_logchannel(
            ctx, 
            channel: discord.Option(discord.TextChannel, "pick the channel to change the log_channel to ") # type: ignore
            ):
            if not ctx.author.guild_permissions.administrator:
                await ctx.respond("❌ You need administrator permissions to change the log channel.", ephemeral=True)
                return

            set_log_channel(ctx.guild.id, channel.id)

            # Set up channel permissions
            try:
                await channel.set_permissions(ctx.guild.default_role, read_messages=False)
                await channel.set_permissions(ctx.guild.me, read_messages=True, send_messages=True)

                # Create embed for confirmation
                embed = discord.Embed(
                    title="📝 Log Channel Updated",
                    description=f"Logging channel has been set to {channel.mention}",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Configured By", value=ctx.author.mention)
                embed.add_field(name="Channel ID", value=channel.id)

                await ctx.respond(embed=embed)
                await channel.send("✅ This channel has been set as the logging channel.")
            except discord.Forbidden:
                await ctx.respond("⚠️ I don't have sufficient permissions to configure the channel.", ephemeral=True)
            except Exception as e:
                await ctx.respond(f"❌ An error occurred: {str(e)}", ephemeral=True)

        @discord.slash_command(name="log_settings", description="View or modify logging settings", guild_ids=GUILD_IDS)
        @admin_required()
        async def log_settings(ctx):
            if not ctx.author.guild_permissions.administrator:
                await ctx.respond("❌ You need administrator permissions to view log settings.", ephemeral=True)
                return

            guild_id = str(ctx.guild.id)
            log_channel_id = get_log_channel(guild_id)
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None

            embed = discord.Embed(
                title="⚙️ Logging Settings",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="Current Log Channel",
                value=log_channel.mention if log_channel else "Not set",
                inline=False
            )
            embed.add_field(
                name="Archive Interval",
                value="Every 24 hours",
                inline=True
            )
            embed.add_field(
                name="Log Retention",
                value="30 days",
                inline=True
            )

            await ctx.respond(embed=embed)



    async def send_log(guild, embed):
        channel_id = get_log_channel(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)
                archive_log_entry(guild.id, {
                    "guild": guild.name,
                    "title": embed.title,
                    "description": embed.description,
                    "timestamp": str(embed.timestamp)
                })

    def build_attachment_text(attachments):
        return "\n".join([f"[{a.filename}]({a.url})" for a in attachments]) or "None"




    message_cache = {}

    # --- DATABASE SETUP & FUNCTIONS ---
    def save_message_to_db(message):
        conn = sqlite3.connect("message_log.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                channel_id INTEGER,
                author_id INTEGER,
                author_name TEXT,
                content TEXT,
                created_at TEXT,
                attachments TEXT
            )
        """)
        attachments = ",".join(a.url for a in message.attachments) if message.attachments else ""
        cursor.execute("""
            INSERT OR REPLACE INTO messages (id, guild_id, channel_id, author_id, author_name, content, created_at, attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id, message.guild.id, message.channel.id,
            message.author.id, str(message.author), message.content,
            message.created_at.isoformat(), attachments
        ))
        conn.commit()
        conn.close()

    def get_message_from_db(message_id):
        conn = sqlite3.connect("message_log.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        conn.close()
        return row


    @commands.Cog.listener()
    async def on_message_edit(before, after):
        if before.author.bot or before.content == after.content:
            return

        user_display = f"{before.author} ({before.author.display_name})"
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.orange()
        )
        embed.set_author(name=user_display, icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before", value=before.content[:1024] or "*(no content)*", inline=False)
        embed.add_field(name="After", value=after.content[:1024] or "*(no content)*", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.set_footer(text=f"User ID: {before.author.id}")
        embed.timestamp = after.edited_at or after.created_at
        await send_log(before.guild, embed)



    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        cached_message = message_cache.get(message.id)

        if not cached_message:
            row = get_message_from_db(message.id)
            if not row:
                return
            _, guild_id, channel_id, author_id, author_name, content, created_at_str, attachments_str = row

            # Rebuild dummy message object
            class FakeUser:
                def __init__(self, name, id):
                    self.name = name
                    self.display_name = name
                    self.id = id
                    self.bot = False
                    self.display_avatar = type("Obj", (), {"url": ""})()

                def __str__(self):
                    return self.name

            class FakeChannel:
                def __init__(self, id):
                    self.id = id
                    self.mention = f"<#{id}>"

            class FakeMessage:
                def __init__(self):
                    self.id = message.id
                    self.content = content
                    self.guild = message.guild
                    self.channel = FakeChannel(channel_id)
                    self.author = FakeUser(author_name, author_id)
                    self.created_at = datetime.fromisoformat(created_at_str)
                    self.attachments = []

            cached_message = FakeMessage()

        # Attempt to detect deleter
        deleter = "Unknown"
        async for entry in message.guild.audit_logs(limit=5, action=discord.AuditLogAction.message_delete):
            if entry.target.id == cached_message.author.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                deleter = f"{entry.user} ({entry.user.display_name})"
                break

        # Build log embed
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=cached_message.content[:1024] or "*(no content)*",
            color=discord.Color.red()
        )
        embed.set_author(name=str(cached_message.author), icon_url=cached_message.author.display_avatar.url)
        embed.add_field(name="Deleted By", value=deleter, inline=False)
        embed.add_field(name="Channel", value=cached_message.channel.mention)
        embed.add_field(name="Attachments", value="None", inline=False)
        embed.set_footer(text=f"User ID: {cached_message.author.id} | Message ID: {cached_message.id}")
        embed.timestamp = cached_message.created_at

        await send_log(cached_message.guild, embed)




    voice_state_cache = defaultdict(lambda: {"last_change": None})
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # Channel Join/Leave/Move
        if before.channel != after.channel:
            embed = discord.Embed(color=discord.Color.purple())
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)

            if not before.channel and after.channel:
                embed.title = "🎧 User Joined Voice Channel"
                embed.description = f"{member.mention} joined {after.channel.mention}"
            elif before.channel and not after.channel:
                embed.title = "👋 User Left Voice Channel"
                embed.description = f"{member.mention} left {before.channel.mention}"
            elif before.channel != after.channel:
                embed.title = "🔁 User Switched Voice Channels"
                embed.description = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}"

            embed.timestamp = discord.utils.utcnow()
            await send_log(member.guild, embed)

        # Only log mute/cam/etc if user is in a channel
        if after.channel:
            changes = []
            if before.self_mute != after.self_mute:
                changes.append("🔇 Muted" if after.self_mute else "🔊 Unmuted")
            if before.self_deaf != after.self_deaf:
                changes.append("🙉 Deafened" if after.self_deaf else "👂 Undeafened")
            if before.self_video != after.self_video:
                changes.append("📷 Cam On" if after.self_video else "📷 Cam Off")
            if before.self_stream != after.self_stream:
                changes.append("📺 Screen Share On" if after.self_stream else "📺 Screen Share Off")

            if changes:
                embed = discord.Embed(
                    title="🎛️ Voice State Changed",
                    description=f"{member.mention}\n" + "\n".join(changes),
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                await send_log(member.guild, embed)



    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if isinstance(channel, discord.VoiceChannel):
            embed = discord.Embed(
                title="📢 Voice Channel Created",
                description=f"New VC created: {channel.mention} (`{channel.name}`)",
                color=discord.Color.teal(),
                timestamp=discord.utils.utcnow()
            )
            await send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if isinstance(channel, discord.VoiceChannel):
            embed = discord.Embed(
                title="❌ Voice Channel Deleted",
                description=f"Deleted VC: `{channel.name}`",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            await send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        added_roles = [r for r in after.roles if r not in before.roles]
        removed_roles = [r for r in before.roles if r not in after.roles]
        if added_roles or removed_roles:
            embed = discord.Embed(
                title="🛠️ Roles Updated",
                description=f"{after.mention}",
                color=discord.Color.blurple(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            if added_roles:
                embed.add_field(name="Added Roles", value=", ".join(r.name for r in added_roles), inline=False)
            if removed_roles:
                embed.add_field(name="Removed Roles", value=", ".join(r.name for r in removed_roles), inline=False)
            await send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        embed = discord.Embed(
            title="🚫 User Banned",
            description=f"{user} has been banned.",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"User ID: {user.id}")
        await send_log(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        embed = discord.Embed(
            title="♻️ User Unbanned",
            description=f"{user} has been unbanned.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"User ID: {user.id}")
        await send_log(guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        now = discord.utils.utcnow()
        roles = ", ".join(r.name for r in member.roles if r.name != "@everyone") or "None"
        joined = member.joined_at.strftime("%Y-%m-%d %H:%M") if member.joined_at else "Unknown"
        created = member.created_at.strftime("%Y-%m-%d %H:%M")
        reason = "Left voluntarily"

        async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id and (now - entry.created_at).total_seconds() < 5:
                reason = f"Kicked by {entry.user} ({entry.user.display_name})"
                break

        embed = discord.Embed(
            title="🚪 Member Left Server",
            description=f"{member.mention} has left.",
            color=discord.Color.dark_grey(),
            timestamp=now
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Joined Server", value=joined)
        embed.add_field(name="Account Created", value=created)
        embed.add_field(name="Roles", value=roles, inline=False)
        await send_log(member.guild, embed)



    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            embed = discord.Embed(
                title="👤 Nickname Changed",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=str(before), icon_url=before.display_avatar.url)
            embed.add_field(name="Old Nickname", value=before.nick or "None", inline=True)
            embed.add_field(name="New Nickname", value=after.nick or "None", inline=True)

            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                if entry.target.id == before.id:
                    changed_by = entry.user
                    embed.add_field(name="Changed By", value=str(changed_by), inline=False)
                    break

            await send_log(before.guild, embed) 






    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.premium_tier != after.premium_tier:
            embed = discord.Embed(
                title="⭐ Server Boost Update",
                description=f"Server boost level changed from {before.premium_tier} to {after.premium_tier}",
                color=discord.Color.purple(),
                timestamp=discord.utils.utcnow()
            )
            await send_log(after, embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]

        if added or removed:
            embed = discord.Embed(
                title="😄 Emoji Updates",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            if added:
                embed.add_field(name="Added Emojis", value=", ".join(str(e) for e in added), inline=False)
            if removed:
                embed.add_field(name="Removed Emojis", value=", ".join(str(e) for e in removed), inline=False)
            await send_log(guild, embed)

    @commands.Cog.listener()
    async def on_integration_create(self, integration):
        embed = discord.Embed(
            title="🔧 Integration Added",
            description=f"New integration: {integration.name}",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Type", value=integration.type)
        await send_log(integration.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        embed = discord.Embed(
            title="👑 Role Updated",
            description=f"Role: {after.mention}",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        changed = False  # Flag to avoid double sends unless a real change happens

        # Always include role ID
        embed.add_field(name="Role ID", value=str(after.id))

        # Name change
        if before.name != after.name:
            embed.add_field(name="Name Change", value=f"`{before.name}` → `{after.name}`")
            changed = True

        # Permission changes
        if before.permissions != after.permissions:
            changed_perms = []
            for perm, value in after.permissions:
                if getattr(before.permissions, perm) != value:
                    changed_perms.append(f"{perm.replace('_', ' ').title()}: {value}")
            if changed_perms:
                embed.add_field(name="Permission Changes", value="\n".join(changed_perms), inline=False)
                changed = True

        # Color change
        if before.color != after.color:
            embed.add_field(name="Color Change", value=f"{before.color} → {after.color}")
            changed = True

        # Hoist change
        if before.hoist != after.hoist:
            embed.add_field(name="Hoisted Change", value=f"{before.hoist} → {after.hoist}")
            changed = True

        if changed:
            await send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.overwrites != after.overwrites:
            embed = discord.Embed(
                title="🔒 Channel Permissions Updated",
                description=f"Channel: {after.mention}",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )

            for target, overwrite in after.overwrites.items():
                if target not in before.overwrites or before.overwrites[target] != overwrite:
                    perms = [f"{perm}: {value}" for perm, value in overwrite if value is not None]
                    embed.add_field(name=f"Permissions for {target}", value="\n".join(perms), inline=False)

            await send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        changes = []
        if before.name != after.name:
            changes.append(f"Name: {before.name} → {after.name}")
        if before.icon != after.icon:
            changes.append("Server icon changed")
        if before.banner != after.banner:
            changes.append("Server banner changed")
        if before.verification_level != after.verification_level:
            changes.append(f"Verification Level: {before.verification_level} → {after.verification_level}")

        if changes:
            embed = discord.Embed(
                title="⚙️ Server Settings Updated",
                description="\n".join(changes),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            await send_log(after, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if isinstance(after, discord.TextChannel) and before.topic != after.topic:
            embed = discord.Embed(
                title="📝 Channel Topic Updated",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Channel", value=after.mention)
            embed.add_field(name="Old Topic", value=before.topic or "None", inline=False)
            embed.add_field(name="New Topic", value=after.topic or "None", inline=False)
            await send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        embed = discord.Embed(
            title="📨 Server Invite Created",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Created By", value=f"{invite.inviter.mention} ({invite.inviter})")
        embed.add_field(name="Channel", value=invite.channel.mention)
        embed.add_field(name="Max Uses", value=invite.max_uses or "Unlimited")
        embed.add_field(name="Expires", value=f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "Never")
        await send_log(invite.guild, embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        embed = discord.Embed(
            title="🗑️ Server Invite Deleted",
            description=f"Invite code: {invite.code}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Channel", value=invite.channel.mention)
        await send_log(invite.guild, embed)

    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage_instance):
        embed = discord.Embed(
            title="🎭 Stage Channel Created",
            description=f"New stage channel: {stage_instance.channel.mention}",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Topic", value=stage_instance.topic or "No topic set")
        await send_log(stage_instance.guild, embed)

    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage_instance):
        embed = discord.Embed(
            title="🎭 Stage Channel Ended",
            description=f"Stage ended in: {stage_instance.channel.mention}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        await send_log(stage_instance.guild, embed)

    @commands.Cog.listener()
    async def on_sticker_create(self, sticker):
        embed = discord.Embed(
            title="🎨 Sticker Added",
            description=f"New sticker: {sticker.name}",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Description", value=sticker.description or "No description")
        embed.add_field(name="Emoji", value=sticker.emoji or "No emoji")
        embed.set_thumbnail(url=sticker.url)
        await send_log(sticker.guild, embed)

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event):
        embed = discord.Embed(
            title="📅 Server Event Created",
            description=f"New event: {event.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Start Time", value=f"<t:{int(event.start_time.timestamp())}:F>")
        if event.end_time:
            embed.add_field(name="End Time", value=f"<t:{int(event.end_time.timestamp())}:F>")
        embed.add_field(name="Location", value=event.location or "No location set")
        embed.add_field(name="Description", value=event.description or "No description", inline=False)
        await send_log(event.guild, embed)



    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        embed = discord.Embed(
            title="👑 Role Created",
            description=f"New role: {role.mention}",
            color=role.color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Color", value=str(role.color))
        embed.add_field(name="Hoisted", value=str(role.hoist))
        embed.add_field(name="Mentionable", value=str(role.mentionable))

        # Add permission details
        perms = []
        for perm, value in role.permissions:
            if value:
                perms.append(perm.replace('_', ' ').title())
        if perms:
            embed.add_field(name="Permissions", value='\n'.join(perms), inline=False)

        await send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        embed = discord.Embed(
            title="👑 Role Deleted",
            description=f"Role '{role.name}' has been deleted",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Role ID", value=role.id)
        embed.add_field(name="Color", value=str(role.color))
        await send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        embed = discord.Embed(
            title="🧵 Thread Updated",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        changes = []
        if before.name != after.name:
            changes.append(f"Name: {before.name} → {after.name}")
        if before.archived != after.archived:
            changes.append(f"Archived: {before.archived} → {after.archived}")
        if before.locked != after.locked:
            changes.append(f"Locked: {before.locked} → {after.locked}")
        if before.slowmode_delay != after.slowmode_delay:
            changes.append(f"Slowmode: {before.slowmode_delay}s → {after.slowmode_delay}s")

        if changes:
            embed.description = "\n".join(changes)
            embed.add_field(name="Thread", value=after.mention)
            await send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_guild_scheduled_event_user_add(self, event, user):
        embed = discord.Embed(
            title="📅 Event RSVP Added",
            description=f"{user.mention} signed up for {event.name}",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Event Time", value=f"<t:{int(event.start_time.timestamp())}:F>")
        await send_log(event.guild, embed)

    @commands.Cog.listener()
    async def on_guild_scheduled_event_user_remove(self, event, user):
        embed = discord.Embed(
            title="📅 Event RSVP Removed",
            description=f"{user.mention} removed their RSVP from {event.name}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Event Time", value=f"<t:{int(event.start_time.timestamp())}:F>")
        await send_log(event.guild, embed)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        embed = discord.Embed(
            title="🔗 Webhook Configuration Updated",
            description=f"Webhooks were modified in {channel.mention}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        # Fetch current webhooks
        webhooks = await channel.webhooks()
        if webhooks:
            webhook_list = "\n".join([f"- {webhook.name}" for webhook in webhooks])
            embed.add_field(name="Current Webhooks", value=webhook_list)

        await send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_member_timeout(self, member, until):
        embed = discord.Embed(
            title="⏰ Member Timed Out",
            description=f"{member.mention} has been timed out",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Until", value=f"<t:{int(until.timestamp())}:F>")

        # Try to get the moderator who set the timeout
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
            if entry.target.id == member.id:
                embed.add_field(name="Moderator", value=entry.user.mention)
                if entry.reason:
                    embed.add_field(name="Reason", value=entry.reason)
                break

        await send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule):
        embed = discord.Embed(
            title="🛡️ AutoMod Rule Created",
            description=f"New automod rule: {rule.name}",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Trigger Type", value=str(rule.trigger_type))
        embed.add_field(name="Actions", value=str(rule.actions))
        embed.add_field(name="Enabled", value=str(rule.enabled))
        await send_log(rule.guild, embed)

    @commands.Cog.listener()
    async def on_automod_rule_update(self, before, after):
        embed = discord.Embed(
            title="🛡️ AutoMod Rule Updated",
            description=f"Rule: {after.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        if before.enabled != after.enabled:
            embed.add_field(name="Status Changed", value=f"{'Enabled' if after.enabled else 'Disabled'}")
        if before.trigger_type != after.trigger_type:
            embed.add_field(name="Trigger Type Changed", value=f"{before.trigger_type} → {after.trigger_type}")
        if before.actions != after.actions:
            embed.add_field(name="Actions Updated", value=str(after.actions))

        await send_log(after.guild, embed)

    async def send_log(guild, message):
            config = get_guild_config(guild.id)
            log_channel_id = config.get("log_channel")
            if log_channel_id:
                channel = guild.get_channel(log_channel_id)
                if channel:
                    await channel.send(embed=message)
    
    @tasks.loop(hours=24)
    async def archive_logs():
        """Archive logs every 24 hours and compress old logs"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = f"logs/archive_{timestamp}.json"

        if not os.path.exists("logs"):
            os.makedirs("logs")

        # Archive current logs
        if os.path.exists(LOG_ARCHIVE_FILE):
            with open(LOG_ARCHIVE_FILE, "r") as f:
                current_logs = json.load(f)

            # Save to dated archive file
            with open(archive_path, "w") as f:
                json.dump(current_logs, f, indent=4)

            # Clear current logs
            with open(LOG_ARCHIVE_FILE, "w") as f:
                json.dump([], f)

        print(f"[{datetime.now()}] Logs archived to {archive_path}")






def setup(client):
    
    client.add_cog(Logger(client))