import { Router } from "express";
import UserService from "../services/UserService";
import VerificationService from "../services/VerificationService";
import VerificationManager from "../services/VerificationManager";
console.log("verification.ts loaded");


const router = Router();


router.get("/test", (req, res) => {
    res.json({
        success: true,
        message: "Verification routes work."
    });
});

router.post("/start", async (req, res) => {

    const { guildId, discordId, username } = req.body;

    const user = await UserService.getUserByUsername(username);

    if (!user) {

        return res.json({
            success: false,
            message: "User not found."
        });

    }

    const session = VerificationService.create(

        guildId,

        discordId,

        user.id,

        username,

        user.displayName

    );

    res.json({

        success: true,

        sessionId: session.id,

        user: {

            id: user.id,

            displayName: user.displayName,

            bio: user.bio,

            status: user.status,

            thumbnail: user.currentAvatarThumbnailImageUrl

        }

    });

});
export default router;