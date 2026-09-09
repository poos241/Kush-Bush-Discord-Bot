export interface LinkedAccount {

    guild_id: string;

    discord_id: string;

    vrchat_id: string;

    vrchat_username: string;

    display_name: string;

    verified: number;

    friend_status:
        | "none"
        | "pending"
        | "sent"
        | "accepted";

    group_status:
        | "none"
        | "invited"
        | "joined";

    roles_synced: number;

    created_at: number;

    updated_at: number;
}