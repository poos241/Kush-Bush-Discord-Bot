import { Router } from "express";

import VerificationService from "../services/VerificationService";

import vrchat from "../services/vrchat";
import { UserId } from "vrc-ts";



const router = Router();


router.get("/debug", (req, res) => {

    console.log(Object.keys(vrchat.client.friendApi));

    res.json({
        success: true
    });

});




router.get("/status/:id", async (req, res) => {

    try {

        const status = await vrchat.client.friendApi.checkFriendStatus({userId: req.params.id});
        console.dir(status, { depth: null });

        res.json(status);

    } catch (err) { 

        console.error(err);

        res.status(500).json({
            success: false
        });

    }

});

router.post("/send", async (req, res) => {

    console.log("==================================");
    console.log("/friends/send called");
    console.log(req.body);
    console.log("==================================");

    try {

        const { sessionId } = req.body;

        console.log("Looking up session:", sessionId);

        const session = VerificationService.get(sessionId);

        if (!session) {

            console.log("Session not found!");

            return res.status(404).json({
                success: false,
                message: "Session not found."
            });

        }

        console.log("Session:");
        console.log(session);

        console.log("Sending friend request to:", session.vrchatUserId);

        await vrchat.client.friendApi.sendFriendRequest({
        userId: session.vrchatUserId
    });

    console.log("Friend request sent.");
    
    session.friendRequestSent = true;

    return res.json({
        success: true,
        alreadyFriends: false,
        pending: false
    });

    } catch (err: any) {

    const msg = err?.message ?? "";
    
    if (msg.includes("already been sent a friend request")) {

        console.log("Friend request already pending.");
        
        
        //session.friendRequestSent = true;

        return res.json({
            success: true,
            pending: true,
            alreadyFriends: false
        });

    }

    if (msg.includes("Users are already friends")) {

        console.log("Already friends.");

        // session.friendRequestSent = true;

        return res.json({
            success: true,
            alreadyFriends: true,
            pending: false
        });

    }

    throw err;

    }

});

export default router;