import discord
from discord.ext import commands, pages
from config import GUILD_IDS, is_owner
from data.DB.Storage.storage import save_levels
from data.DB.db import database
from data.DB.models import levels
from cogs.VRChat.VRC_API.vrchat_api import vrchat

class DBTools(commands.Cog):
    HelpCategory = "Admin Tools"

    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="list_tracked_guilds", description="List all guilds stored in the database")
    @is_owner() 
    async def list_tracked_guilds(self, interaction: discord.ApplicationContext):
        """Lists all guilds currently tracked in the XP system."""
        await interaction.response.defer()

        query = levels.select()
        rows = await database.fetch_all(query)

        if not rows:
            await interaction.followup.send("❌ No guilds found in the database.")
            return

        entries = []
        for row in rows:
            guild = self.bot.get_guild(int(row["guild_id"]))
            name = (guild.name if guild else None) or row["guild_name"] or "Unknown"
            member_count = f"{guild.member_count:,}" if guild else "N/A"
            gid = row["guild_id"]
            entries.append(f"**{name}**\n🆔 `{gid}` | 👥 Members: `{member_count}`")

        paginator = pages.Paginator(
            pages=[discord.Embed(title="📋 Tracked Guilds", description=chunk, color=discord.Color.green())
                for chunk in self.chunk_list(entries, 10)],
            show_disabled=True,
            show_indicator=True,
            use_default_buttons=True,
            timeout=60
        )

        await paginator.respond(interaction.interaction) 

    def chunk_list(self, items, chunk_size):
        for i in range(0, len(items), chunk_size):
            yield "\n\n".join(items[i:i+chunk_size])

    @discord.slash_command(name="delete_guild_data", description="Delete a guild's level data from the database")
    @is_owner()
    async def delete_guild_data(
        self,
        interaction: discord.ApplicationContext,
        guild_id: discord.Option(str, "Guild ID to delete", default=None)  # type: ignore
    ):
        """Deletes a guild's levels + XP timestamps by guild ID (or current server)."""
        gid = guild_id or str(interaction.guild.id)

        query = levels.delete().where(levels.c.guild_id == gid)
        result = await database.execute(query)

        if result:
            await interaction.respond(f"🗑️ Successfully deleted data for guild ID `{gid}`.")
        else:
            await interaction.respond(f"⚠️ No data found for guild ID `{gid}`.")

    
    
    @discord.slash_command(name="unlink_account", description="Remove a linked VRChat account.", guild_ids=GUILD_IDS)
    @is_owner()
    async def unlink_account(
        self,
        ctx,
        member: discord.Option(discord.Member, "Member to unlink") # type: ignore
    ):
        await ctx.defer(ephemeral=True)

        data = await vrchat.unlink_account(ctx.guild.id, member.id)
        
        if not data["success"]:
            return await ctx.followup.send(
                "No linked account found for this member.",
                ephemeral=True
            )
        
        account = data["account"]

        embed = discord.Embed(
            title="Unlinked VRChat Account",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Display Name",
            value=account["display_name"],
            inline=False
        )

        embed.add_field(
            name="VRChat ID",
            value=account["vrchat_id"],
            inline=False
        )

        embed.add_field(
            name="Verified",
            value="✅ Yes" if account["verified"] else "❌ No",
            inline=True
        )

        embed.add_field(
            name="Friend Status",
            value=account["friend_status"],
            inline=True
        )

        embed.add_field(
            name="Group Status",
            value=account["group_status"],
            inline=True
        )

        embed.add_field(
            name="Roles Synced",
            value="✅ Yes" if account["roles_synced"] else "❌ No",
            inline=True
        )


        await ctx.followup.send(embed=embed, ephemeral=True)



        
        

        
    

def setup(bot):
    bot.add_cog(DBTools(bot))
