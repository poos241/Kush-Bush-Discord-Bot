import random
import discord, os, io, time, json, asyncio, zipfile
from discord.ext import commands
from discord.commands import Option



from config import admin_required, Manage_channels_required, Manage_messages_required, extra_help, GUILD_IDS
from data.DB.Storage.storage import get_ticket_config, save_ticket_config, get_active_tickets, save_active_tickets,get_ticket_records, save_ticket_records





class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
    def send_embed(self, channel, embed, view=None, file=None):
        return channel.send(embed=embed, view=view, file=file)



   # ✅ Pulls config from DB or defaults if none
    async def get_guild_config(self, guild_id):
        config = await get_ticket_config(guild_id)
        return config or {
            "ticket_category": None,
            "log_channel": None,
            "ticket_limit": 1,
            "ticket_panel": {},
            "ticket_roles": {},
            "verification_role": None
        }

    # ✅ Updates a single config key and saves to DB
    async def set_guild_config(self, guild_id, key, value):
        config = await self.get_guild_config(guild_id)
        config[key] = value
        await save_ticket_config(guild_id, config)

    # ✅ Sets active tickets (with guild_name too)
    async def set_active_tickets(self, guild_id, data, member=None, interaction=None):
        existing = await get_active_tickets(guild_id)
        existing.update({
            str(member.id): data.get(str(member.id), []),
            "guild_name": interaction.guild.name if interaction and interaction.guild else "Unknown"
        })
        await save_active_tickets(guild_id, existing)

    # ✅ Sends to log channel from config
    async def send_log(self, guild, embed):
        config = await self.get_guild_config(guild.id)
        log_channel_id = config.get("log_channel")
        if log_channel_id:
            channel = guild.get_channel(log_channel_id)
            if channel:
                await channel.send(embed=embed)

    # ✅ Appends a new ticket to user's record
    async def add_ticket(self, guild_id, user_id, channel_id):
        records = await get_ticket_records(guild_id)
        records.setdefault(str(user_id), []).append(channel_id)
        await save_ticket_records(guild_id, records)

    # ✅ Removes closed ticket from both records & active tickets
    async def remove_ticket(self, guild_id, channel_id):
        tickets = await get_ticket_records(guild_id)
        active = await get_active_tickets(guild_id)

        for uid, chans in list(tickets.items()):
            if channel_id in chans:
                chans.remove(channel_id)
                if not chans:
                    del tickets[uid]
                break

        for uid, chans in list(active.items()):
            if channel_id in chans:
                chans.remove(channel_id)
                if not chans:
                    del active[uid]
                break

        await save_ticket_records(guild_id, tickets)
        await save_active_tickets(guild_id, active)
    

    @discord.slash_command(name="ticket_config", description="Configure the ticket system.")
    @extra_help("Configure the ticket system settings such as category, log channel, limits, and panel.")
    @admin_required()
    async def ticket_config(self, ctx,
        category: Option(discord.CategoryChannel), # type: ignore
        log_channel: Option(discord.TextChannel), # type: ignore
        limit: Option(int, min_value=1), # type: ignore
        embed_message: Option(str), image_url: Option(str), # type: ignore
        dm_on_open: Option(bool), # type: ignore
        ticket_message: Option(str), # type: ignore
        button1_label: Option(str), button1_color: Option(str), # type: ignore
        button2_label: Option(str, required=False), button2_color: Option(str, required=False), # type: ignore
        button3_label: Option(str, required=False), button3_color: Option(str, required=False) # type: ignore
    ):
        cfg = await get_ticket_config(ctx.guild.id) or {}
        cfg.update({
            "guild_name": ctx.guild.name,
            "ticket_category": category.id,
            "log_channel": log_channel.id,
            "ticket_limit": limit,
            "ticket_panel": {
                "message": embed_message,
                "image_url": None if image_url.lower()=="none" else image_url,
                "buttons": [
                    {"label": L, "color": C} for L, C in (
                        (button1_label, button1_color),
                        (button2_label, button2_color),
                        (button3_label, button3_color),
                    ) if L and C
                ],
                "dm_on_open": dm_on_open,
                "ticket_message": None if ticket_message.lower()=="default" else ticket_message
            }
        })
        await save_ticket_config(ctx.guild.id, cfg)
        await ctx.respond("✅ Ticket configuration saved.", ephemeral=True)


    
    
    @discord.slash_command(name="ticket_manage_roles", description="Set roles that can view specific ticket types")
    @extra_help("Set roles that can view specific ticket types (support/staff/owner). Use role IDs or mentions, separated by commas.")
    @admin_required()
    async def ticket_manage_roles(
        self,
        ctx: discord.ApplicationContext,
        ticket_type: discord.Option(str, "Ticket type (support/staff/owner)"), # type: ignore
        roles: discord.Option(str, "Comma-separated role IDs or mentions") # type: ignore
    ):
        """Set roles that can view specific ticket types (support/staff/owner). Use role IDs or mentions, separated by commas."""
        guild_id = str(ctx.guild.id)
        cfg = await get_ticket_config(ctx.guild.id) or {}
        ids = []
        for r in roles.split(","):
            r = r.strip()
            if r.isdigit():
                ids.append(int(r))
            elif r.startswith("<@&") and r.endswith(">"):
                ids.append(int(r[3:-1]))
        cfg.setdefault("ticket_roles", {})[ticket_type.lower()] = ids
        cfg["guild_name"] = ctx.guild.name
        await save_ticket_config(ctx.guild.id, cfg)
        await ctx.respond(f"✅ Roles for `{ticket_type}` tickets set!", ephemeral=True)
    
    
    @commands.slash_command(name="ticket_open", description="Open a new support ticket")
    @extra_help("Open a new support ticket. You can only have a limited number of open tickets at a time.")
    async def ticket_open(
        self, 
        ctx: discord.ApplicationContext # type: ignore
        ):
        """Open a new support ticket."""
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        config = await self.get_guild_config(guild_id)
        active = await get_active_tickets(guild_id)

        if len(active.get(str(user_id), [])) >= config.get("ticket_limit", 1):
            await ctx.respond("⚠️ You have reached your ticket limit.", ephemeral=True)
            return

        category = ctx.guild.get_channel(config["ticket_category"])
        if not category:
            await ctx.respond("⚠️ Ticket category not set.", ephemeral=True)
            return

        channel_name = f"ticket-{ctx.user.display_name}-{random.randint(1000, 9999)}"

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await ctx.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        await self.add_ticket(guild_id, user_id, ticket_channel.id)

        embed = discord.Embed(
            title="🎫 Ticket Created",
            description=f"{ctx.author.mention}, please describe your issue. Staff will assist you shortly.",
            color=discord.Color.green()
        )
        await ticket_channel.send(embed=embed, view=ClaimView(ctx.author.id))
        await ctx.respond(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

        log_channel_id = config.get("log_channel")
        if log_channel_id:
            log_channel = ctx.guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(description=f"📂 Ticket opened: {ticket_channel.mention} by {ctx.author.mention}", color=discord.Color.green())
                await log_channel.send(embed=log_embed)
                

    
    
    @commands.slash_command(name="ticket_close", description="Close this ticket")
    @extra_help("Close the current ticket. Only the ticket opener or staff can close tickets.")
    async def ticket_close(
        self, 
        ctx: discord.ApplicationContext # type: ignore
        ):
        """Close the current ticket. Only the ticket opener or staff can close tickets."""
        if not ctx.channel.name.startswith("ticket-"):
                return await ctx.respond("⚠️ This is not a ticket channel.", ephemeral=True)

        await ctx.respond("⚠️ Are you sure you want to close this ticket?", view=CloseConfirmView(ctx.channel, ctx.author, self.bot), ephemeral=True)





    @discord.slash_command(name="set_verification_role", description="Set the role for verification button")
    @extra_help("Set the role that will be assigned when a user verifies their ticket. This role will be assigned when the verification button is clicked in a ticket.")
    @admin_required()
    async def set_verification_role(
        self,
        interaction: discord.ApplicationContext,
        role: discord.Option(discord.Role, "Role to assign on verification") # type: ignore
    ):
        """Set the role that will be assigned when a user verifies their ticket. This role will be assigned when the verification button is clicked in a ticket."""
        cfg = await get_ticket_config(interaction.guild.id) or {}
        cfg.setdefault("ticket_panel", {})
        cfg["verification_role"] = role.id
        await save_ticket_config(interaction.guild.id, {**cfg, "guild_name": interaction.guild.name})
        await interaction.respond(f"✅ Verification role set to {role.mention}", ephemeral=True)

    
    
    @discord.slash_command(name="ticket_verification", description="Send a verification button in this ticket")
    @extra_help("Add a verification button to the current ticket channel. This allows staff to verify the ticket opener and assign a role.")
    @Manage_channels_required()
    async def ticket_verification(
        self, 
        ctx: discord.ApplicationContext # type: ignore
        ):
        """Add a verification button to the current ticket channel. This allows staff to verify the ticket opener and assign a role."""
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.respond("⚠️ Not a ticket channel.", ephemeral=True)

        view = discord.ui.View()
        

        async def verify_callback(inter):
            now = discord.utils.utcnow()
            last = self.cooldowns.get(inter.user.id)
            self.cooldowns[inter.user.id] = now
            if last and (now - last).total_seconds() < 10:
                return await inter.response.send_message("⏱️ Please wait before clicking again.", ephemeral=True)

            self.cooldowns[inter.user.id] = now
            cfg = await get_ticket_config(inter.guild.id)
            role_id = cfg.get("verification_role")
            if not role_id:
                return await inter.response.send_message("⚠️ No verification role set.", ephemeral=True)

            role = inter.guild.get_role(role_id)
            if not role:
                return await inter.response.send_message("⚠️ Role no longer exists.", ephemeral=True)

            # Find ticket opener from active tickets
            active = await get_active_tickets(inter.guild.id)
            current_channel_id = str(inter.channel.id)
            def is_channel_in_chans(chans, target_id):
                if isinstance(chans, list):
                    return target_id in [str(c) for c in chans]
                return target_id == str(chans)

            opener_id = next((uid for uid, chans in active.items() if is_channel_in_chans(chans, current_channel_id)), None)

            if not opener_id:
                return await inter.response.send_message("⚠️ Could not find opener.", ephemeral=True)

            member = inter.guild.get_member(int(opener_id))
            if not member:
                return await inter.response.send_message("⚠️ Opener no longer in server.", ephemeral=True)

            await member.add_roles(role)
            await inter.response.send_message(f"✅ {member.mention} verified.", ephemeral=True)
            view.clear_items()
            ##await inter.response.edit_message(view=view)

        button = discord.ui.Button(label="✅ Verify Ticket Opener", style=discord.ButtonStyle.success)
        button.callback = verify_callback
        view.add_item(button)
        await ctx.respond("✅ Verification button added.", view=view, ephemeral=True)

        
    @discord.slash_command(name="send_ticket_panel", description="Send the ticket panel.")
    @extra_help("Send the ticket panel with buttons in the specified channel. This allows users to open tickets directly from the panel.")
    @admin_required()
    async def ticket_panel(
        self, 
        ctx, 
        target_channel: Option(discord.TextChannel, "Target channel to send panel in") # type: ignore
        ):
        """Send the ticket panel with buttons in the specified channel. This allows users to open tickets directly from the panel."""
        config = await get_ticket_config(ctx.guild.id)
        panel = config.get("ticket_panel", {})
        if not panel:
            return await ctx.respond("⚠️ Ticket panel not configured.", ephemeral=True)

        embed = discord.Embed(description=panel["message"], color=discord.Color.blurple())
        if panel.get("image_url"):
            embed.set_image(url=panel["image_url"])

        view = TicketPanelView(panel["buttons"], ctx.guild.id)
        await target_channel.send(embed=embed, view=view)
        await ctx.respond(f"✅ Ticket panel sent in {target_channel.mention}", ephemeral=True)


    @discord.slash_command(name="ticket_add_user", description="Add a user to this ticket", guild_ids=GUILD_IDS)
    @admin_required()
    async def ticket_add_user(self, ctx, member: discord.Option(discord.Member, "User to add") # type:ignore
    ):
        channel = ctx.channel
        if not channel.name.startswith("ticket-"):
            await ctx.respond("⚠️ This is not a ticket channel.", ephemeral=True)
            return

        await channel.set_permissions(member, read_messages=True, send_messages=True)
        await ctx.respond(f"✅ Added {member.mention} to the ticket.")

    @discord.slash_command(name="ticket_remove_user", description="Remove a user from this ticket", guild_ids=GUILD_IDS)
    @admin_required()
    async def ticket_remove_user(self, ctx, member: discord.Option(discord.Member, "User to remove") # type:ignore
    ):
        channel = ctx.channel
        if not channel.name.startswith("ticket-"):
            await ctx.respond("⚠️ This is not a ticket channel.", ephemeral=True)
            return

        await channel.set_permissions(member, overwrite=None)
        await ctx.respond(f"✅ Removed {member.mention} from the ticket.")


# === TICKET PANEL VIEW ===

class TicketPanelView(discord.ui.View):
    def __init__(self, buttons, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        for btn in buttons:
            style = {
                "green": discord.ButtonStyle.success,
                "red": discord.ButtonStyle.danger,
                "grey": discord.ButtonStyle.secondary,
                "blurple": discord.ButtonStyle.primary
            }.get(btn["color"], discord.ButtonStyle.secondary)

            button = discord.ui.Button(
                label=btn["label"],
                style=style,
                custom_id=f"ticket_{btn['label'].lower().replace(' ', '_')}"
            )
            button.callback = self.make_callback(btn["label"])
            self.add_item(button)

    def make_callback(self, label):
        async def callback(interaction: discord.Interaction):
            cog = interaction.client.get_cog("TicketSystem")
            if not cog:
                return await interaction.response.send_message("⚠️ Ticket system not loaded.", ephemeral=True)
            ##await cog.ticket_open(interaction)
            await ticket_open_logic(interaction, label.lower(), cog)

        return callback



# === TICKET CREATION LOGIC ===

async def ticket_open_logic(interaction, ticket_type, cog):
    guild_id = interaction.guild.id
    user_id = str(interaction.user.id)
    config = await cog.get_guild_config(guild_id)
    panel = config.get("ticket_panel", {}) 

    tickets = await get_active_tickets(guild_id)
    user_tickets = tickets.get(user_id, [])

    if len(user_tickets) >= config["ticket_limit"]:
        await interaction.response.send_message("⚠️ You have reached your ticket limit.", ephemeral=True)
        return

    category = interaction.guild.get_channel(config["ticket_category"])
    if not category:
        await interaction.response.send_message("⚠️ Ticket category not configured.", ephemeral=True)
        return

    channel_name = f"ticket-{ticket_type}-{interaction.user.display_name}".replace(" ", "-").lower()
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    role_ids = config.get("ticket_roles", {}).get(ticket_type.lower(), [])
    for role_id in role_ids:
        role = interaction.guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await interaction.guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites
    )

    tickets.setdefault(user_id, []).append(channel.id)
    await cog.set_active_tickets(guild_id, tickets, interaction.user, interaction)


    msg_text = panel.get("ticket_message") or f"{interaction.user.mention}, please describe your issue."
    embed = discord.Embed(title="🎫 Ticket Created", description=msg_text, color=discord.Color.green())
    await channel.send(embed=embed, view=ClaimView(interaction.user.id))


    if panel.get("dm_on_open"):
        try:
            await interaction.user.send(f"✅ Your ticket has been created: {channel.mention}")
        except:
            pass

    await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
    
    
    
class ClaimView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="🎟️ Claim Ticket", style=discord.ButtonStyle.primary)
    async def claim(self, button, interaction):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("You cannot claim tickets.", ephemeral=True)
        await interaction.channel.send(f"✅ Ticket claimed by {interaction.user.mention}")
        self.clear_items()
        await interaction.message.edit(view=self)

class CloseConfirmView(discord.ui.View):
    def __init__(self, channel, closer, bot):
        super().__init__(timeout=60)
        self.channel = channel
        self.closer = closer
        self.bot = bot

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, button, interaction):
        await interaction.response.send_message("❌ Cancelled ticket close.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def confirm(self, button, interaction):
        await close_ticket_logic(self.channel, self.closer, bot=interaction.client)
        self.stop()


    @discord.ui.button(label="Close with Reason", style=discord.ButtonStyle.primary)
    async def close_with_reason(self, button, interaction):
        await interaction.response.send_message("✏️ Type the reason to close this ticket:", ephemeral=True)
        try:
            msg = await interaction.client.wait_for("message", timeout=60, check=lambda m: m.author == interaction.user and m.channel == interaction.channel)
            await close_ticket_logic(self.channel, self.closer, msg.content, bot=interaction.client)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ Timeout. No reason set.", ephemeral=True)
        self.stop()

async def close_ticket_logic(channel, closer, reason=None, bot=None):
    from data.DB.Storage.storage import get_active_tickets, save_active_tickets
    messages = []
    async for msg in channel.history(oldest_first=True):
        messages.append(f"{msg.created_at:%Y-%m-%d %H:%M} | {msg.author.display_name}: {msg.content}")
    transcript = "\n".join(messages)
    transcript_file = discord.File(io.StringIO(transcript), filename=f"{channel.name}_transcript.txt")

    cog = bot.get_cog("TicketSystem")
    config = await get_ticket_config(channel.guild.id)
    log_channel_id = config.get("log_channel")
    if log_channel_id:
        log = channel.guild.get_channel(log_channel_id)
        if log:
            embed = discord.Embed(
            title="📁 Ticket Closed",
            description=f"By: {closer.mention}\nReason: {reason or 'No reason provided.'}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
)
            await log.send(embed=embed, file=transcript_file)

    tickets = await get_active_tickets(channel.guild.id)
    for uid, chans in list(tickets.items()):
        chans = [int(c) for c in chans] if isinstance(chans, list) else []
        if channel.id in chans:
            chans.remove(channel.id)
            if chans:
                tickets[uid] = chans
            else:
                del tickets[uid]
            break

    await save_active_tickets(channel.guild.id, tickets)

    await channel.delete()





# === SETUP ===

def setup(client):
    client.add_cog(TicketSystem(client))
