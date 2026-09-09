import readlineSync from "readline-sync";

import vrchat from "./vrchat"

import {
    EmailOtpRequired,
    TOTPRequired
} from "vrc-ts";

export async function loginVRChat() {

    console.log("==================================");
    console.log("Starting VRChat Login...");
    console.log("==================================");

    try {

        await vrchat.client.login();

        console.log("✅ Logged in!");

        console.log(vrchat.currentUser);

        return;

    }
    catch (err) {

        if (err instanceof EmailOtpRequired) {

            console.log("");
            console.log("Email verification required.");
            console.log("");

            const code = readlineSync.question("Enter Email Code: ");

            vrchat.client.EmailOTPCode = code;

            await vrchat.client.login();

            console.log("");

            console.log("✅ Logged in!");

            console.log(vrchat.currentUser);

            return;

        }

        if (err instanceof TOTPRequired) {

            console.log("");

            console.log("Authenticator App required.");

            console.log("");

            const code = readlineSync.question("Enter TOTP Code: ");

            vrchat.client.EmailOTPCode = code;

            await vrchat.client.login();

            console.log("");

            console.log("✅ Logged in!");

            console.log(vrchat.currentUser);

            return;

        }

        console.error(err);

    }

}