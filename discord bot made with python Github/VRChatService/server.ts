import express from "express";
import dotenv from "dotenv";

import meRoute from "./routes/me";

import { loginVRChat } from "./services/auth";

import statusRoute from "./services/status";

import usersRoute from "./routes/users";

import linkRoute from "./routes/link";

import verificationRoute from "./routes/verification";

import friendsRoute from "./routes/friends";

import { startFriendWatcher } from "./services/FriendWatcher";

import communityRoute from "./routes/community";



dotenv.config();

const app = express();

app.use(express.json());

app.use("/me", meRoute);

app.use("/status", statusRoute);

app.use("/user", usersRoute);

app.use("/link", linkRoute);

app.use("/verification", verificationRoute);

app.use("/friends", friendsRoute);

app.use("/community", communityRoute);



const PORT = Number(process.env.PORT) || 3000;

app.get("/", (req, res) => {

    res.json({

        success: true,

        message: "VRChat Service"

    });

});

app.listen(PORT, async () => {

    

    await loginVRChat();
    startFriendWatcher();
    console.log("");

    console.log(`Listening on ${PORT}`);

});