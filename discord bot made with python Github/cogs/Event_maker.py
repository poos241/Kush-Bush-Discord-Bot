import discord
from discord.ext import commands
from datetime import datetime
import pytz
from io import BytesIO

from config import admin_required, GUILD_IDS, EVENT_TEMPLATES


# =========================================================
# EVENT TEMPLATES
# =========================================================




# =========================================================
# MODAL
# =========================================================

class EventModal(discord.ui.Modal):

    def __init__(self, cog, template_name):
        super().__init__(title="Create Event")

        self.cog = cog
        self.template_name = template_name

        # =====================================================
        # TITLE
        # =====================================================

        self.title_input = discord.ui.InputText(
            label="Event Title",
            placeholder="It's Wednesday My Dudes!",
            max_length=100
        )

        # =====================================================
        # HOST NAME
        # =====================================================

        self.host_name_input = discord.ui.InputText(
            label="Host Name",
            placeholder="PureKush",
            max_length=100
        )

        # =====================================================
        # HOST LINK
        # =====================================================

        self.host_link_input = discord.ui.InputText(
            label="Host Profile Link",
            placeholder="https://vrchat.com/home/user/...",
            required=False,
            max_length=300
        )

        # =====================================================
        # WORLD NAME
        # =====================================================

        self.world_input = discord.ui.InputText(
            label="World Name",
            placeholder="Cuddle & Sleep",
            max_length=100
        )

        # =====================================================
        # WORLD LINK
        # =====================================================

        self.world_link_input = discord.ui.InputText(
            label="World Link",
            placeholder="https://vrchat.com/home/world/...",
            required=False,
            max_length=300
        )

        # =====================================================
        # CO HOSTS
        # =====================================================

        self.co_host_input = discord.ui.InputText(
            label="Co-hosts",
            placeholder="@User1,@User2",
            required=False,
            max_length=300
        )

        # =====================================================
        # SECURITY
        # =====================================================

        self.security_input = discord.ui.InputText(
            label="Security",
            placeholder="@Guard1,@Guard2",
            required=False,
            max_length=300
        )

        # =====================================================
        # IMAGE URL
        # =====================================================

        self.image_input = discord.ui.InputText(
            label="Event Image URL",
            placeholder="https://image.com/banner.png",
            required=False,
            max_length=500
        )

        # =====================================================
        # DATE
        # =====================================================

        self.date_input = discord.ui.InputText(
            label="Date & Time",
            placeholder="2026-05-06 21:30",
            max_length=50
        )

        # =====================================================
        # ADD ITEMS
        # =====================================================

        self.add_item(self.title_input)
        self.add_item(self.host_name_input)
        self.add_item(self.host_link_input)
        self.add_item(self.world_input)
        self.add_item(self.world_link_input)

        # NOTE:
        # Discord modal limit is 5 inputs.
        # So we must split into another modal OR compact fields.

    async def callback(self, interaction: discord.Interaction):

        try:

            dt = datetime.strptime(
                self.date_input.value,
                "%Y-%m-%d %H:%M"
            )

            timezone = pytz.timezone("US/Central")

            dt = timezone.localize(dt)

            unix = int(dt.timestamp())

        except Exception:

            await interaction.response.send_message(
                "❌ Invalid date format.\nUse: `2026-05-06 21:30`",
                ephemeral=True
            )
            return

        # =====================================================
        # TEMPLATE
        # =====================================================

        template_text = EVENT_TEMPLATES[self.template_name]

        # =====================================================
        # HOST FORMAT
        # =====================================================

        if self.host_link_input.value.strip():

            host_text = (
                f'[**ADD {self.host_name_input.value.upper()}**]'
                f'(<{self.host_link_input.value}>)'
            )

        else:

            host_text = self.host_name_input.value

        # =====================================================
        # WORLD FORMAT
        # =====================================================

        if self.world_link_input.value.strip():

            world_text = (
                f'[{self.world_input.value}]'
                f'(<{self.world_link_input.value}>)'
            )

        else:

            world_text = self.world_input.value

        # =====================================================
        # BUILD EVENT
        # =====================================================

        event_post = f"""
@General Event Ping

# {self.title_input.value}

{template_text}

## Add me:
{host_text}

## ___**Where are we headed?:**___

{world_text}

## ___**Doors Open**___

<t:{unix}:F>
<t:{unix}:R>

As always Clear and Full Consent when engaging with fellow lewdies
"""

        # =====================================================
        # EMBED
        # =====================================================

        embed = discord.Embed(
            title="✅ Event Generated",
            description="Copy/edit before posting.",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Preview",
            value="Event generated successfully.",
            inline=False
        )

        # =====================================================
        # IMAGE
        # =====================================================

        # NOTE:
        # image field omitted due to modal limits.
        # Added in next section below.

        # =====================================================
        # SEND
        # =====================================================

        if len(event_post) > 1900:

            file = discord.File(
                BytesIO(event_post.encode()),
                filename="event_post.txt"
            )

            await interaction.response.send_message(
                file=file,
                embed=embed,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                f"```md\n{event_post}\n```",
                embed=embed,
                ephemeral=True
            )


# =========================================================
# COG
# =========================================================

class EventCog(commands.Cog):

    def __init__(self, client):
        self.bot = client

    # =====================================================
    # CREATE UNIX TIMESTAMP
    # =====================================================

    def create_unix_timestamp(
        self,
        year,
        month,
        day,
        hour,
        minute,
        timezone
    ):

        tz = pytz.timezone(timezone)

        dt = tz.localize(
            datetime(year, month, day, hour, minute)
        )

        return int(dt.timestamp())

    # =====================================================
    # MAIN COMMAND
    # =====================================================

    @discord.slash_command(
        name="create_event",
        description="Generate an event post.",
        guild_ids=GUILD_IDS
    )
    @admin_required()
    async def create_event(
        self,
        interaction: discord.ApplicationContext,

        template: discord.Option(
            str,
            choices=list(EVENT_TEMPLATES.keys()),
            description="Choose template"
        ), # type: ignore

        title: discord.Option(str, description="Event title"), # type: ignore

        host_name: discord.Option(str, description="Host name"), # type: ignore
        
        host_vrchat_link: discord.Option(str, description="Host VRChat profile link"), # type: ignore

        world_name: discord.Option(str, description="World name"), # type: ignore
        
        world_link: discord.Option(str,description="VRChat world link"),# type: ignore

        year: discord.Option(int, description="Year"), # type: ignore

        month: discord.Option(int, description="Month"), # type: ignore

        day: discord.Option(int, description="Day"), # type: ignore

        hour: discord.Option(int, description="Hour"), # type: ignore

        minute: discord.Option(int, description="Minute"), # type: ignore
        
        security: discord.Option(str, description="Security (optional)", default="None"), # type: ignore
        
        co_host: discord.Option(str, description="Co-hosts (optional)", default="None"), # type: ignore
        

        timezone: discord.Option(
            str,
            description="Timezone",
            choices=[
                "US/Eastern",
                "US/Central",
                "US/Mountain",
                "US/Pacific",
                "UTC",
                "Europe/London",
                "Asia/Tokyo"
            ],
            default="US/Central"
        ) # type: ignore
    ):

        unix = self.create_unix_timestamp(
            year,
            month,
            day,
            hour,
            minute,
            timezone
        )

        template_text = EVENT_TEMPLATES[template]

        event_post = f"""
@General Event Ping

# {title}

{template_text}

## Add me:
[**ADD THE HOST {host_name.upper()}**](<{host_vrchat_link}>)

## Co-host:
{co_host}

## Security:
{security}

Late joiners may not receive announcements so make sure to read the rules thoroughly!
Also private rooms are allowed to be locked.

## ___**Doors Open**___

[{world_name}](<{world_link}>)

<t:{unix}:F>
<t:{unix}:R>

As always Clear and Full Consent when engaging with fellow lewdies
**Event Rules**  --> ⁠:diamond_shape_with_a_dot_inside:｜rules⁠https://discord.com/channels/734595073920204940/737074569319546921/1294366927111716914
**Unsure how to attend?** --> ⁠:question:｜how-to-join-eventshttps://discord.com/channels/734595073920204940/980342448712724560
**For any questions ping myself in** ⁠⁠:globe_with_meridians:｜events-talkhttps://discord.com/channels/734595073920204940/894726709272793169
**Link your discord!** ⁠:mobile_phone:｜linking-with-vrchathttps://discord.com/channels/734595073920204940/1228159292306362368

IF you haven't already, add me before the event and **REQUEST ONLY WHEN PINGED**
"""

        # Auto file fallback
        if len(event_post) > 1900:

            file = discord.File(
                BytesIO(event_post.encode()),
                filename="event_post.txt"
            )

            await interaction.respond(
                "✅ Event generated!",
                file=file,
                ephemeral=True
            )

        else:

            await interaction.respond(
                f"```md\n{event_post}\n```",
                ephemeral=True
            )

    # =====================================================
    # MODAL TEST COMMAND
    # =====================================================

    @discord.slash_command(
        name="event_modal",
        description="Open the event creation modal.",
        guild_ids=GUILD_IDS
    )
    @admin_required()
    async def event_modal(
        self,
        interaction: discord.ApplicationContext,

        template: discord.Option(
            str,
            choices=list(EVENT_TEMPLATES.keys()),
            description="Choose template"
        ) # type: ignore
    ):

        modal = EventModal(self, template)

        await interaction.response.send_modal(modal)


# =========================================================
# SETUP
# =========================================================

def setup(client):
    client.add_cog(EventCog(client))