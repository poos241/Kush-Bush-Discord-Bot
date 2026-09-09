import math
import discord
from discord.ext import commands
from config import COMMAND_HELP, COMMAND_TAGS, GUILD_IDS, extra_help, is_owner, load_json, save_json, autocomplete_commands, admin_required

# Fields & character limits
MAX_FIELDS = 25
MAX_TOTAL_CHARS = 6000

PAGE_SIZE = 5  # tags per page in tags list


# Autocomplete helper
async def autocomplete_query(ctx: discord.AutocompleteContext):
    val = ctx.value.lower()
    # Collect all category tags and command names
    categories = set()
    for cog in ctx.bot.cogs.values():
        cat = getattr(cog.__class__, "HelpCategory", None)
        if cat:
            categories.add(cat)
    cmd_names = [cmd.name for cmd in ctx.bot.application_commands]
    # Filter suggestions by substring match, limit to 25
    choices = [c for c in categories if val in c.lower()]
    choices += [c for c in cmd_names if val in c.lower()]
    return choices[:25]




class Helpinfodoc(commands.Cog):
    def __init__(self, client):
        self.bot = client

    @discord.slash_command(name="help", description="View help for commands or categories")
    @extra_help("Use `/help <command>` to get detailed help, or `/help` to pick a category.")
    async def help_command(
        self,
        ctx: discord.ApplicationContext,
        query: discord.Option(str, "Command name or category", required=False, autocomplete=autocomplete_query) # type: ignore
    ):
        """Help command: lookup by command or category."""
        # Build category → commands mapping
        category_map = {}
        for cmd in self.bot.application_commands:
            inst = getattr(cmd.callback, "__self__", None)
            cat = getattr(inst, "HelpCategory", None)
            cog_name = inst.__class__.__name__ if inst else None
            category = cat or cog_name or "Uncategorized"
            category_map.setdefault(category, []).append(cmd)

        # No query: show category picker
        if not query:
            embed = discord.Embed(
                title="📘 Help Menu",
                description="Select a category or start typing for autocomplete.",
                color=discord.Color.blurple()
            )
            view = HelpCategoryView(category_map, ctx.author.id)
            return await ctx.respond(embed=embed, view=view, ephemeral=True)

        key = query.strip().lower()
        # Category lookup
        for category, cmds in category_map.items():
            if category.lower() == key:
                embed = discord.Embed(
                    title=f"{category} Commands",
                    description=f"Commands under **{category}**",
                    color=discord.Color.green()
                )
                for cmd in cmds[:25]:
                    embed.add_field(
                        name=f"/{cmd.name}",
                        value=cmd.description or "No description",
                        inline=False
                    )
                return await ctx.respond(embed=embed, ephemeral=True)

        # Command lookup
        for cmd in self.bot.application_commands:
            if cmd.name == key:
                embed = discord.Embed(title=f"ℹ️ Help for /{cmd.name}", color=discord.Color.green())
                embed.add_field(name="Description", value=cmd.description or "⚠️ No description", inline=False)
                doc = getattr(cmd.callback, "__doc__", None)
                extra = getattr(cmd.callback, "__extra_help__", None)
                if doc:
                    embed.add_field(name="More Info", value=doc, inline=False)
                if extra:
                    embed.add_field(name="Extra Details", value=extra, inline=False)
                try:
                    usage = f"/{cmd.name} " + " ".join(
                        f"<{opt.name}>" if opt.required else f"[{opt.name}]"
                        for opt in cmd.options
                    ) if cmd.options else f"/{cmd.name}"
                    embed.add_field(name="Usage", value=usage, inline=False)
                except:
                    embed.add_field(name="Usage", value="⚠️ Could not parse usage", inline=False)
                return await ctx.respond(embed=embed, ephemeral=True)

        # Not found
        return await ctx.respond(f"❌ `{query}` not found as command or category.", ephemeral=True)



    @discord.slash_command(name="show_tags", description="List all command tags and their commands")
    @extra_help("See a list of tags and which commands are grouped under them.")
    @is_owner()
    async def show_tags(self, ctx: discord.ApplicationContext):
        """Show all known tags and their command groupings."""
        embed = discord.Embed(title="📂 Help Tags", color=discord.Color.teal())
        for tag, cmds in COMMAND_TAGS.items():
            embed.add_field(name=tag.title(), value="\n".join(f"/{c}" for c in cmds), inline=False)
        await ctx.respond(embed=embed, ephemeral=True)




    @discord.slash_command(name="diagnose_docs", description="Scan for missing descriptions/doc/help/tags")
    @extra_help("Shows commands missing description, docstring, extra_help, or tag group.")
    @is_owner()
    async def diagnose_docs(self, ctx: discord.ApplicationContext):
        """Scan all commands for missing documentation elements."""
        missing_desc = []
        missing_doc = []
        missing_extra = []
        missing_tag = []

        for cmd in self.bot.application_commands:
            name = f"/{cmd.name}"
            if not cmd.description:
                missing_desc.append(name)
            if not getattr(cmd.callback, "__doc__", None):
                missing_doc.append(name)
            if not getattr(cmd.callback, "__extra_help__", None):
                missing_extra.append(name)
            if not any(cmd.name in group for group in COMMAND_TAGS.values()):
                missing_tag.append(name)

        embed = discord.Embed(title="🛠️ Documentation Scan Results", color=discord.Color.orange())
        embed.add_field(name="❌ Missing Descriptions", value="\n".join(missing_desc) or "✅ None", inline=False)
        embed.add_field(name="❌ Missing Docstrings", value="\n".join(missing_doc) or "✅ None", inline=False)
        embed.add_field(name="❌ Missing Extra Help", value="\n".join(missing_extra) or "✅ None", inline=False)
        embed.add_field(name="❌ Missing Tags", value="\n".join(missing_tag) or "✅ None", inline=False)

        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="show_categories", description="List all command categories and their command counts")
    @extra_help("List all help categories detected from your commands and their command counts.")
    @is_owner()
    async def show_categories(self, ctx: discord.ApplicationContext):
        """Lists all help categories detected from your commands and their command count."""
        category_map = {}

        for cmd in ctx.bot.application_commands:
            callback = getattr(cmd, "callback", None)
            cog = getattr(callback, "__self__", None)
            category = getattr(cog, "HelpCategory", cog.__class__.__name__ if cog else "Uncategorized")
            category_map.setdefault(category, []).append(cmd)

        embed = discord.Embed(
            title="📂 Command Categories",
            description="Here are all detected categories and their command counts:",
            color=discord.Color.teal()
        )

        for category, cmds in sorted(category_map.items()):
            embed.add_field(name=category, value=f"{len(cmds)} command(s)", inline=False)

        await ctx.respond(embed=embed, ephemeral=True)





    @discord.slash_command(name="generate_tags", description="Smart generate command tags by grouping")
    @extra_help("Scans all slash commands and attempts to group them into smart tags.")
    @is_owner()
    async def generate_tags(self, ctx: discord.ApplicationContext):
        """Smartly group commands into categories and show tag mappings for copy-paste."""

        tag_map: dict[str, list[str]] = {}

        def infer_tag(cmd):
            name = cmd.name.lower()
            desc = (cmd.description or "").lower()

            if any(x in name or x in desc for x in ("ban", "kick", "role", "rename", "clear", "lock", "admin", "mod")):
                return "Admin"
            elif any(x in name or x in desc for x in ("xp", "level", "leaderboard")):
                return "Leveling"
            elif any(x in name or x in desc for x in ("ticket", "panel", "support", "claim")):
                return "Tickets"
            elif any(x in name or x in desc for x in ("rps", "flip", "roll", "conch", "game", "fun")):
                return "Fun"
            elif "vc" in name or "voice" in desc:
                return "Voice Tools"
            elif "auto" in name or "thread" in name:
                return "Automation"
            elif "help" in name or "doc" in name or "tag" in name:
                return "Help System"
            else:
                inst = getattr(cmd.callback, "__self__", None)
                cog = inst.__class__.__name__ if inst else "Other"
                return cog

        for cmd in self.bot.application_commands:
            tag = infer_tag(cmd)
            tag_map.setdefault(tag, []).append(cmd.name)

        embed = discord.Embed(title="🧠 Smart Tag Suggestions", color=discord.Color.purple())
        for tag, cmds in sorted(tag_map.items()):
            embed.add_field(name=f"{tag} ({len(cmds)})", value="`" + "`, `".join(cmds) + "`", inline=False)

        embed.set_footer(text="Copy these groupings into your COMMAND_TAGS config.")
        await ctx.respond(embed=embed, ephemeral=True)
    

# UI COMPONENTS

class TagPageView(discord.ui.View):
    def __init__(self, tags: list[str]):
        super().__init__(timeout=120)
        self.tags = tags
        self.page = 0
        self.message = None
        self.add_item(TagDropdown(tags))

    async def update(self, interaction):
        total = len(self.tags)
        per = PAGE_SIZE
        idx = self.page * per
        selection = self.tags[idx:idx + per]

        embed = discord.Embed(title="📘 Help Categories", color=discord.Color.blurple())
        for tag in selection:
            embed.add_field(name=tag.title(), value=f"{len(COMMAND_TAGS[tag])} commands")
        embed.set_footer(text=f"Page {self.page+1}/{math.ceil(total/per)}")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.blurple)
    async def prev(self, button, interaction):
        self.page = (self.page - 1) % math.ceil(len(self.tags)/PAGE_SIZE)
        await self.update(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.blurple)
    async def next(self, button, interaction):
        self.page = (self.page + 1) % math.ceil(len(self.tags)/PAGE_SIZE)
        await self.update(interaction)

class TagDropdown(discord.ui.Select):
    def __init__(self, tags: list[str]):
        options = [discord.SelectOption(label=tag.title(), value=tag) for tag in tags]
        super().__init__(placeholder="Pick a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        tag = self.values[0]
        await interaction.response.send_message(
            embed=Helpinfodoc.build_tag_embed(self.view, tag, COMMAND_TAGS[tag]),
            ephemeral=True
        )


class HelpCategorySelect(discord.ui.Select):
    def __init__(self, category_map, author_id):
        options = [
            discord.SelectOption(label=cat, description=f"{len(cmds)} commands")
            for cat, cmds in category_map.items()
        ]
        super().__init__(placeholder="Pick a category...", min_values=1, max_values=1, options=options)
        self.category_map = category_map
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        category = self.values[0]
        cmds = self.category_map.get(category, [])
        embed = discord.Embed(title=f"{category} Commands", color=discord.Color.green())
        for cmd in cmds[:25]:
            embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpCategoryView(discord.ui.View):
    def __init__(self, category_map, author_id):
        super().__init__(timeout=120)
        self.add_item(HelpCategorySelect(category_map, author_id))

def setup(client):
    client.add_cog(Helpinfodoc(client))


def setup(client):
    client.add_cog(Helpinfodoc(client))