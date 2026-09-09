import { Router } from "express";
import LinkService from "../services/LinkService";
import vrchat from "../services/vrchat";


const router = Router();

router.post("/start", async (req, res) => {

    try {

        const { discordId, guildId } = req.body;

        const account = LinkService.getLink(guildId, discordId);

        if (!account) {
            return res.status(404).json({
                success: false,
                message: "No linked account found."
            });
        }

        // TODO: send group invite here

        LinkService.updateGroupStatus(
            discordId,
            "invited"
        );

        res.json({
            success: true
        });

    } catch (err) {
        console.error(err);
        res.status(500).json({
            success: false
        });
    }
});

export default router;