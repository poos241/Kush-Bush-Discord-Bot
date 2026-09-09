import discord

from cogs.VRChat.VRC_API.vrchat_api import vrchat


class CommunityView(discord.ui.View):

    def __init__(self, discord_id: int):
        super().__init__(timeout=900)
        self.discord_id = discord_id

    @discord.ui.button(
        label="Join Community",
        style=discord.ButtonStyle.green,
        emoji="🎉"
    )
    async def join_button(self, button, interaction):

        await interaction.response.defer(ephemeral=True)

        data = await vrchat.start_group_verification(self.discord_id)

        if not data["success"]:
            return await interaction.followup.send(
                data.get("message", "Failed to start verification."),
                ephemeral=True
            )

        embed = discord.Embed(
            title="Community Verification Started",
            description=(
                "You are already friends with the verification account.\\n\\n"
                "A VRChat group invite has been sent.\\n\\n"
                "Accept the invite in VRChat and the bot will continue automatically."
            ),
            color=discord.Color.green()
        )

        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(
        label="Maybe Later",
        style=discord.ButtonStyle.secondary,
        emoji="⏭️"
    )
    async def later_button(self, button, interaction):

        await interaction.response.edit_message(
            content="Your VRChat account is linked. You can join the community later with `/join_community`.",
            embed=None,
            view=None
        )