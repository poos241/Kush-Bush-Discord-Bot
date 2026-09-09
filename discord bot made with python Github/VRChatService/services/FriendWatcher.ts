import vrchat from "./vrchat";
import LinkService from "./LinkService";
//import GroupService from "./GroupService";

async function checkFriend(account: any) {

    try {

        const status =
            await vrchat.client.friendApi.checkFriendStatus({

                userId: account.vrchat_id

            });

        if (!status.isFriend)
            return;

        console.log(
            `${account.display_name} accepted friend request.`
        );

        LinkService.updateFriendStatus(
            account.guild_id,
            account.discord_id,
            "accepted"
        );

        //await GroupService.sendInvite(
        //    account.vrchat_id,            
        //);

        //LinkService.updateGroupStatus(
           // account.guild_id,
           // account.discord_id
            //"pending"
       // );

    }

    catch (err) {

        console.error(err);

    }

}

export function startFriendWatcher() {

    setInterval(async () => {

        const pending =
            LinkService.getPendingFriends();

        for (const account of pending) {

            await checkFriend(account);

        }

    }, 10000);

}