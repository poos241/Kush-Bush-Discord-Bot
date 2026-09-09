# cogs/welcome_cog.py
import datetime
import discord
from discord.ext import commands
from config import admin_required, extra_help, load_json, replace_placeholders, save_json

welcome_file = "welcome_data.json"
goodbye_file = "goodbye_data.json"
join_time_file = "join_times.json"

class WelcomeCog(commands.Cog):
    def __init__(self, client):
        self.bot = client
        self.settings = load_json(welcome_file)
        self.goodbye_settings = load_json(goodbye_file)
        self.join_times = load_json(join_time_file)

    # ========= CONFIGURATION COMMANDS ========= #

    @discord.slash_command(name="set_welcome_channel", description="Lets Admin set the welcome channel.")
    @extra_help("Set the channel where welcome messages will be sent. You can also set an image URL, embed title, and message.")
    @admin_required()
    async def set_welcome_channel(self, ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Select welcome channel"), # type: ignore
        image_url: discord.Option(str, "Add image URL"), # type: ignore
        title: discord.Option(str, "Set embed title"), # type: ignore
        message: discord.Option(str, "Set welcome message")): # type: ignore
        """Set the channel where welcome messages will be sent. You can also set an image URL, embed title, and message."""
        gid = str(ctx.guild.id)
        self.settings[gid] = {
            "guild_name": ctx.guild.name,
            "welcome_channel_id": str(channel.id),
            "welcome_image_url": image_url,
            "welcome_embed_title": title,
            "welcome_message": message
        }
        save_json(welcome_file, self.settings)
        await ctx.respond(f"✅ Welcome channel set to {channel.mention}", ephemeral=True)

    @discord.slash_command(name="set_goodbye_channel", description="Set goodbye channel.")
    @extra_help("Set the channel where goodbye messages will be sent. You can also set an image URL, embed title, and message.")
    @admin_required()
    async def set_goodbye_channel(self, ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Select goodbye channel"), # type: ignore
        image_url: discord.Option(str, "Image URL"), # type: ignore
        title: discord.Option(str, "Embed title"), # type: ignore
        message: discord.Option(str, "Goodbye message")): # type: ignore
        """Set the channel where goodbye messages will be sent. You can also set an image URL, embed title, and message."""

        gid = str(ctx.guild.id)
        self.goodbye_settings[gid] = {
            "guild_name": ctx.guild.name,
            "goodbye_channel_id": str(channel.id),
            "goodbye_image_url": image_url,
            "goodbye_embed_title": title,
            "goodbye_message": message
        }
        save_json(goodbye_file, self.goodbye_settings)
        await ctx.respond(f"✅ Goodbye channel set to {channel.mention}", ephemeral=True)

    @discord.slash_command(name="set_auto_role", description="Set auto-role for new members.")
    @extra_help("Set a role that will be automatically assigned to new members when they join.")
    @admin_required()
    async def set_auto_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Set a role that will be automatically assigned to new members when they join."""
        gid = str(ctx.guild.id)
        self.settings.setdefault(gid, {})
        self.settings[gid]["auto_role_id"] = str(role.id)
        self.settings[gid]["auto_role_name"] = role.name
        save_json(welcome_file, self.settings)
        await ctx.respond(f"✅ Auto-role set to {role.name}", ephemeral=True)

    @discord.slash_command(name="set_manager_role", description="Only this role can toggle welcome/goodbye.")
    @extra_help("Set a role that can manage welcome and goodbye settings. Only users with this role can toggle these features.")
    @admin_required()
    async def set_manager_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Set a role that can manage welcome and goodbye settings. Only users with this role can toggle these features."""
        gid = str(ctx.guild.id)
        self.settings.setdefault(gid, {})
        self.settings[gid]["manager_role_id"] = str(role.id)
        save_json(welcome_file, self.settings)
        await ctx.respond(f"✅ Manager role set to `{role.name}`", ephemeral=True)

    def has_manager_role(self, ctx):
        gid = str(ctx.guild.id)
        settings = self.settings.get(gid, {})
        manager_role_id = settings.get("manager_role_id")
        return not manager_role_id or discord.utils.get(ctx.author.roles, id=int(manager_role_id))

    @discord.slash_command(name="toggle_welcome", description="Turn welcome on or off.")
    @extra_help("Toggle welcome messages on or off. Only users with the manager role can use this command.")
    @admin_required()
    async def toggle_welcome(self, ctx: discord.ApplicationContext, toggle: discord.Option(str, choices=["on", "off"])): # type: ignore
        """Toggle welcome messages on or off. Only users with the manager role can use this command."""
        if not self.has_manager_role(ctx):
            return await ctx.respond("❌ You don't have the manager role for this command.", ephemeral=True)

        gid = str(ctx.guild.id)
        self.settings.setdefault(gid, {})
        self.settings[gid]["welcome_enabled"] = (toggle == "on")
        save_json(welcome_file, self.settings)
        await ctx.respond(f"✅ Welcome messages are now **{toggle.upper()}**", ephemeral=True)

    @discord.slash_command(name="toggle_goodbye", description="Turn goodbye on or off.")
    @extra_help("Toggle goodbye messages on or off. Only users with the manager role can use this command.")
    @admin_required()
    async def toggle_goodbye(self, ctx: discord.ApplicationContext, toggle: discord.Option(str, choices=["on", "off"])): # type: ignore
        """Toggle goodbye messages on or off. Only users with the manager role can use this command."""
        if not self.has_manager_role(ctx):
            return await ctx.respond("❌ You don't have the manager role for this command.", ephemeral=True)

        gid = str(ctx.guild.id)
        self.goodbye_settings.setdefault(gid, {})
        self.goodbye_settings[gid]["goodbye_enabled"] = (toggle == "on")
        save_json(goodbye_file, self.goodbye_settings)
        await ctx.respond(f"✅ Goodbye messages are now **{toggle.upper()}**", ephemeral=True)

    # ========= JOIN & LEAVE EVENTS ========= #

    @commands.Cog.listener()
    async def on_member_join(self, member):
        gid = str(member.guild.id)
        uid = str(member.id)

        config = self.settings.get(gid, {})
        if not config.get("welcome_enabled", True):
            return

        now = datetime.datetime.utcnow()
        last_seen_str = self.join_times.get(gid, {}).get(uid)
        if last_seen_str:
            last_seen = datetime.datetime.fromisoformat(last_seen_str)
            if (now - last_seen).total_seconds() < 86400:
                print(f"⏱️ Skipping welcome for {uid}: joined < 24h ago")
                return

        self.join_times.setdefault(gid, {})[uid] = now.isoformat()
        save_json(join_time_file, self.join_times)

        await self.send_welcome_embed(member)

        auto_role_id = config.get("auto_role_id")
        if auto_role_id:
            role = member.guild.get_role(int(auto_role_id))
            if role:
                await member.add_roles(role, reason="Auto-role on join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        gid = str(member.guild.id)
        config = self.goodbye_settings.get(gid, {})
        if config.get("goodbye_enabled", True):
            await self.send_goodbye_embed(member)

    # ========= TESTING ========= #

    @discord.slash_command(name="testwelcome", description="Test the welcome message.")
    @extra_help("Send a test welcome message to the configured channel. Only users with the manager role can use this command.")
    @admin_required()
    async def test_welcome(self, ctx: discord.ApplicationContext):
        """Send a test welcome message to the configured channel. Only users with the manager role can use this command."""
        member = ctx.guild.get_member(ctx.user.id)
        if not member:
            return await ctx.respond("⚠️ Not found as a guild member", ephemeral=True)
        await self.send_welcome_embed(member)
        await ctx.respond("✅ Welcome message sent", ephemeral=True)

    @discord.slash_command(name="testgoodbye", description="Test the goodbye message.")
    @extra_help("Send a test goodbye message to the configured channel. Only users with the manager role can use this command.")
    @admin_required()
    async def test_goodbye(self, ctx: discord.ApplicationContext):
        """Send a test goodbye message to the configured channel. Only users with the manager role can use this command."""
        member = ctx.guild.get_member(ctx.user.id)
        if not member:
            return await ctx.respond("⚠️ Not found as a guild member", ephemeral=True)
        await self.send_goodbye_embed(member)
        await ctx.respond("✅ Goodbye message sent", ephemeral=True)

    # ========= MESSAGE SENDERS ========= #

    async def send_welcome_embed(self, member):
        gid = str(member.guild.id)
        conf = self.settings.get(gid, {})
        channel_id = conf.get("welcome_channel_id")
        channel = self.bot.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            print(f"❗ No welcome channel for guild {gid}")
            return

        embed = discord.Embed(
            title=replace_placeholders(conf.get("welcome_embed_title", f"Welcome to {member.guild.name}!"), member),
            description=replace_placeholders(conf.get("welcome_message", f"{member.mention}, welcome!"), member),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        if conf.get("welcome_image_url"):
            embed.set_image(url=conf["welcome_image_url"])

        embed.add_field(name="Member Count", value=f"{len(member.guild.members)}")
        embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d"))
        embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d %H:%M") if member.joined_at else "Unknown")
        await channel.send(embed=embed)

    async def send_goodbye_embed(self, member):
        gid = str(member.guild.id)
        conf = self.goodbye_settings.get(gid, {})
        channel_id = conf.get("goodbye_channel_id")
        channel = self.bot.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            print(f"❗ No goodbye channel for guild {gid}")
            return

        embed = discord.Embed(
            title=replace_placeholders(conf.get("goodbye_embed_title", "Goodbye!"), member),
            description=replace_placeholders(conf.get("goodbye_message", f"{member.name} left."), member),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        if conf.get("goodbye_image_url"):
            embed.set_image(url=conf["goodbye_image_url"])

        embed.add_field(name="Username", value=f"{member.name}#{member.discriminator}")
        embed.add_field(name="Display Name", value=member.display_name)
        embed.add_field(name="Member Count", value=f"{len(member.guild.members)}")
        embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown")
        embed.add_field(name="Left", value=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
        await channel.send(embed=embed)

def setup(client):
    client.add_cog(WelcomeCog(client))
