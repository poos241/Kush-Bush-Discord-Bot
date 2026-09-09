import LinkService from "./LinkService";

class VerificationManager {

    async startCommunityVerification(
        guildId: string,
        discordId: string
    ) {

        const account = LinkService.getLink(
            guildId,
            discordId
        );

        if (!account) {

            return {
                success: false,
                message: "No linked account."
            };

        }

        switch (account.friend_status) {

            case "none":
                return await this.sendFriendRequest(account);

            case "pending":
                return {
                    success: true,
                    message: "Friend request already pending."
                };

            case "none":
                return await this.sendGroupInvite(account);

            default:
                return {
                    success: false,
                    message: "Unknown friend status."
                };

        }

    }

    async sendFriendRequest(account: any) {

        // We'll build this next

    }

    async sendGroupInvite(account: any) {

        // Then this

    }

}

export default new VerificationManager();