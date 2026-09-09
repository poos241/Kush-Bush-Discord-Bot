import crypto from "crypto";

import { VerificationSession } from "../models/VerificationSession";

class VerificationService {

    private sessions = new Map<string, VerificationSession>();

    create(guildId: string,discordId: string,vrchatUserId: string,vrchatUsername: string,displayName: string){

    const session: VerificationSession = {

        id: crypto.randomUUID(),

        guildId,

        discordId,

        vrchatUserId,

        vrchatUsername,

        displayName,

        started: Date.now(),

        expires: Date.now() + 15 * 60 * 1000,

        verified: false,

        friendRequestSent: false

    };

    this.sessions.set(session.id, session);

    return session;
    }

    get(id: string) {

        return this.sessions.get(id);

    }

    remove(id: string) {

        this.sessions.delete(id);

    }

}

export default new VerificationService();