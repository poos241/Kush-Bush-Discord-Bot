import dotenv from "dotenv";
import { VRChatAPI } from "vrc-ts";

dotenv.config();

class VRChatService {

    public client: VRChatAPI;

    constructor() {

        this.client = new VRChatAPI({

            username: process.env.VRCHAT_USERNAME!,

            password: process.env.VRCHAT_PASSWORD!,

            userAgent: process.env.USER_AGENT!,

            useCookies: true,

            cookiePath: "./cookies.json"

        });

    }

    get authenticated(): boolean {
        return this.client.isAuthentificated;
    }

    get currentUser() {
        return this.client.currentUser;
    }

    async getCurrentUser() {
        return this.client.currentUser;
    }

}
export default new VRChatService();