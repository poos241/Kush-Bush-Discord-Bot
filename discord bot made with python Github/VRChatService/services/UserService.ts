import vrchat from "./vrchat";

import UserCache from "../cache/UserCache";

class UserService {

    /**
     * Returns the currently authenticated user.
     */
    async getCurrentUser() {
        return vrchat.client.currentUser;
    }

    /**
     * Searches VRChat for a user by username/display name.
     */
    async getUserByUsername(username: string) {

    const cached = UserCache.get(username.toLowerCase());

    if (cached) {

        console.log("Returning cached user:", username);

        return cached;

    }

    console.log("Searching VRChat:", username);

    const users = await vrchat.client.userApi.searchAllUsers({

        search: username,

        n: 10,

        fuzzy: false

    });

    if (!users.length)
        return null;

    UserCache.set(

        username.toLowerCase(),

        users[0],

        300

    );

    return users[0];

}

}

export default new UserService();