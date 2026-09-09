import discord

from cogs.VRChat.VRC_API.vrchat_api import vrchat

from views.VerifyView import VerifyView

class VerifyModal(discord.ui.Modal):

    def __init__(self):

        super().__init__(title="Link VRChat Account")

        self.username = discord.ui.InputText(
            label="VRChat Username",
            placeholder="MusicMan420"
        )

        self.add_item(self.username)

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        data = await vrchat.start_verification(interaction.guild.id,interaction.user.id,self.username.value)

        if "error" in data:
            await interaction.followup.send(
                f"❌ Verification failed: Backend API server returned an error (404). Please contact an administrator.", 
                ephemeral=True
            )
            return

        if not data["success"]:

            return await interaction.followup.send(
                "User not found.",
                ephemeral=True
            )

        user = data["user"]

        embed = discord.Embed(
            title=user["displayName"],
            description=user["bio"],
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Status",
            value=user["status"]
        )

        embed.set_thumbnail(
            url=user["thumbnail"]
        )

        await interaction.followup.send(

            embed=embed,

            view=VerifyView(
                data["sessionId"]
            ),

            ephemeral=True

        )