import { Router } from "express";

import { MeController } from "../controllers/MeController";

const router = Router();

router.get("/", MeController.getMe);

export default router;