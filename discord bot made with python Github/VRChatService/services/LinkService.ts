import db from "../database/database";

import { LinkedAccount } from "../models/LinkedAccount";


class LinkService {



    createLink(guildId: string,discordId: string,vrchatId: string,username: string,displayName: string) {
    console.log("INSERT LINK");
    console.log({
        guildId,
        discordId,
        vrchatId,
        username,
        displayName
    });
        db.prepare(`
        INSERT INTO linked_accounts (

        guild_id,
        discord_id,
        vrchat_id,
        vrchat_username,
        display_name,
        verified,
        friend_status,
        group_status,
        roles_synced,
        created_at,
        updated_at

    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    
    `).run(

        guildId,

        discordId,

        vrchatId,

        username,

        displayName,

        1,

        "none",

        "none",

        0,

        Date.now(),

        Date.now()
        
        

    );
    
    }
    

    getLink(guildId: string,discordId: string): LinkedAccount | undefined 
    {
        return db.prepare(`
            SELECT *
            FROM linked_accounts
            WHERE guild_id = ?
            AND discord_id = ?
        `).get(guildId, discordId) as LinkedAccount | undefined;

    }
    verify(discordId: string) {

        db.prepare(

            `
            UPDATE linked_accounts
            SET verified = 1
            WHERE discord_id = ?
            `

        ).run(discordId);

    }


    updateFriendStatus(
        guildId: string,
        discordId: string,
        status: string
    ) {

        db.prepare(`
            UPDATE linked_accounts
            SET
                friend_status = ?,
                updated_at = ?
            WHERE guild_id = ? AND discord_id = ?
        `).run(

            status,

            Date.now(),

            guildId,
            
            discordId

        );

    }

    updateGroupStatus(
        guildId: string,
        discordId: string,
        //status: string
    ) {

        db.prepare(`
            UPDATE linked_accounts
            SET
                group_status = ?,
                updated_at = ?
            WHERE guild_id = ? AND discord_id = ?
        `).run(

            //status,

            Date.now(),

            guildId,
            discordId

        );

    }
    


    updateRoleSync(
        guildId: string,
        discordId: string,
        synced: boolean
    ) {

        db.prepare(`
            UPDATE linked_accounts
            SET
                roles_synced = ?,
                updated_at = ?
            WHERE guild_id = ? AND discord_id = ?
        `).run(

            synced ? 1 : 0,

            Date.now(),

            guildId,
            discordId

        );

    }


    deleteLink(
    guildId: string,
    discordId: string
    ) {

        db.prepare(`
            DELETE FROM linked_accounts
            WHERE guild_id = ?
            AND discord_id = ?
        `).run(
            guildId,
            discordId
        );

    }

    getPendingFriends(): LinkedAccount[] {

        return db.prepare(`
            SELECT *
            FROM linked_accounts
            WHERE friend_status = ?
        `).all("pending") as LinkedAccount[];

    }
    
    getPendingGroups(): LinkedAccount[] {

        return db.prepare(`
            SELECT *
            FROM linked_accounts
            WHERE group_status = ?
        `).all("pending") as LinkedAccount[];

    }

    getFriends() {
        return db.prepare(`
            SELECT *
            FROM linked_accounts
            WHERE friend_status = 'accepted'
        `).all();
    }



}

export default new LinkService();