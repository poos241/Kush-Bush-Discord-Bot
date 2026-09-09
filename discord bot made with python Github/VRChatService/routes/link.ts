import { Router } from "express";
import LinkService from "../services/LinkService";
import VerificationService from "../services/VerificationService";

const router = Router();

router.get("/:guildId/:discordId", (req, res) => {

    const link = LinkService.getLink(
        req.params.guildId,
        req.params.discordId
    );

    if (!link) {

        return res.status(404).json({

            success: false

        });

    }

    res.json({

        success: true,

        account: link

    });
});

    




router.post("/confirm", async (req, res) => {

    console.log("================================");
    console.log("/link/confirm");
    console.log(req.body);
    console.log("================================");
    const { sessionId } = req.body;

    const session = VerificationService.get(sessionId);

    if (!session) {

        return res.status(404).json({
            success: false
        });

    }
    console.log("Creating database link...");
    LinkService.createLink(
    session.guildId,
    session.discordId,
    session.vrchatUserId,
    session.vrchatUsername,
    session.displayName
    );
    console.log("Database link created.");
    res.json({

        success: true

    });

});

router.delete("/", (req, res) => {

    const { guildId, discordId } = req.body;

    LinkService.deleteLink(
        guildId,
        discordId
    );

    res.json({
        success: true
    });

});

export default router;