import discord

from cogs.VRChat.VRC_API.vrchat_api import vrchat

from views.CommunityView import CommunityView

class VerifyView(discord.ui.View):

    def __init__(self, session_id):

        super().__init__(timeout=900)

        self.session_id = session_id

    @discord.ui.button(
        label="Yes",
        style=discord.ButtonStyle.green,
        emoji="✅"
    )
    async def yes_button(self, button, interaction):

        await interaction.response.defer(ephemeral=True)
        data = await vrchat.confirm_link(self.session_id)

        if not data["success"]:

            await interaction.followup.send(
                "Couldn't save your linked account.",
                ephemeral=True
            )

            return
        '''data = await vrchat.send_friend_request(self.session_id)

        if data.get("alreadyFriends"):

            title = "Already Friends"

            description = (
                "You're already friends with the verification account.\n\n"
                "Continuing verification..."
            )

        else:

            title = "Friend Request Sent"

            description = (
                "A friend request has been sent.\n\n"
                "Please accept it inside VRChat."
            )'''

        embed = discord.Embed(
            title="VRChat Account Linked",
            description=(
                "Your VRChat account has been linked to your Discord account.\\n\\n"
                "Would you like to join the community and receive a VRChat group invite?"
            ),
            color=discord.Color.green()
        )

        await interaction.edit_original_response(
            embed=embed,
            view=CommunityView(interaction.user.id)
        )

        
    @discord.ui.button(
        label="No",
        style=discord.ButtonStyle.red,
        emoji="❌"
    )
    async def no_button(self, button, interaction):

        await interaction.response.edit_message(

            content="Verification cancelled.",

            embed=None,

            view=None

        )