export interface VerificationSession {

    id: string;

    guildId: string;

    discordId: string;

    vrchatUserId: string;

    vrchatUsername: string;

    displayName: string;

    started: number;

    expires: number;

    friendRequestSent: boolean;

    verified: boolean;

}