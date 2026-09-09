import { Router } from "express";

import { UserController } from "../controllers/UserController";

const router = Router();

router.get("/:username", UserController.lookup);

export default router;