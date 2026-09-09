import { Router } from "express";
import vrchat from "../services/vrchat";

const router = Router();

router.get("/", (req, res) => {

    res.json({

        success: true,

        authenticated: vrchat.authenticated,

        loggedInUser:
            vrchat.currentUser?.displayName ?? null

    });

});



export default router;