from discord.ext import commands

import discord

from cogs.VRChat.VRC_API.vrchat_api import vrchat

from config import GUILD_IDS,admin_required


from views.VerifyModal import VerifyModal



class VRChat(commands.Cog):
    def __init__(self, client):
        self.bot = client
       

        
    @discord.slash_command(name="vrtest", description="Tests the VRChat Service", guild_ids=GUILD_IDS)
    @admin_required()
    async def vrtest(self, ctx: discord.ApplicationContext):

        await ctx.defer()

        status = await vrchat.get_status()

        embed = discord.Embed(
            title="VRChat Service",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Authenticated",
            value=status["authenticated"],
            inline=False
        )

        embed.add_field(
            name="Logged In As",
            value=status["loggedInUser"],
            inline=False
        )

        await ctx.respond(embed=embed)
        
    @discord.slash_command(name="friend_request", description="Sends a friend request to a VRChat user", guild_ids=GUILD_IDS)
    @admin_required()
    async def friend_request(self, ctx: discord.ApplicationContext, username: str):
        await ctx.defer()

        # Step 1: Translate the text username into a VRChat User ID
        # Note: If your backend handles the lookup directly inside /friends/send, 
        # you can skip this step and pass username directly into sessionId.
        vrc_user_id = await vrchat.lookup_user_id(username)
        
        if not vrc_user_id:
            # If your API doesn't require a separate lookup step, try setting vrc_user_id = username here instead
            vrc_user_id = username 

        # Step 2: Fire your working endpoint using the ID
        try:
            result = await vrchat.send_friend_request(vrc_user_id)
            
            # Check the JSON response values your backend returns
            if not result or result.get("success") is False or "error" in result:
                error_msg = result.get("error", "Unknown API error occurred.")
                return await ctx.respond(f"❌ Failed to send friend request: **{error_msg}**")
                
            await ctx.respond(f"✅ Friend request sent successfully to VRChat user: **{username}**!")
            
        except Exception as e:
            await ctx.respond(f"⚠️ An unexpected error occurred while communicating with the API.")
            print(f"CRITICAL ERROR in friend_request command: {e}")


    
    @discord.slash_command(name="lookup", description="Lookup a VRChat user", guild_ids=GUILD_IDS)
    @admin_required()
    async def lookup(self,ctx: discord.ApplicationContext, username: str):

        await ctx.defer()

        data = await vrchat.lookup_user(username)
    
        if not data["success"]:

            return await ctx.respond("User not found.")

        user = data["data"]

        #  ALTERNATIVE: Keep "VRChat User Info" and put the bio below it
        embed = discord.Embed(
            title=user["displayName"],
            description="VRChat User Info", 
            color=discord.Color.blue()
        )
        embed.add_field(name="Bio", value=user.get("bio", "No bio provided."), inline=False)


        embed.add_field(
            name="Status",
            value=user["status"]
        )
       
        embed.add_field(
            name="Developer",
            value=user["developerType"]
        )

        embed.set_thumbnail(
            url=user["currentAvatarThumbnailImageUrl"]
        )

        await ctx.respond(embed=embed)
        
        
    @discord.slash_command(name="verify_vrchat",description="Link your VRChat account",guild_ids=GUILD_IDS)
    @admin_required()
    async def verify_vrchat(self, ctx):

        await ctx.send_modal(VerifyModal())
        
        
    @discord.slash_command(name="linked_account",description="Shows your linked VRChat account.",guild_ids=GUILD_IDS)
    @admin_required()
    async def linked_account(self, ctx):

        await ctx.defer(ephemeral=True)

        data = await vrchat.get_linked_account(ctx.guild.id,ctx.author.id)

        if not data["success"]:

            return await ctx.respond(
                "No linked account.",
                ephemeral=True
            )
        
        account = data["account"]

        embed = discord.Embed(
            title="Linked VRChat Account",
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

        await ctx.respond(embed=embed, ephemeral=True)

def setup(client):
    client.add_cog(VRChat(client))
