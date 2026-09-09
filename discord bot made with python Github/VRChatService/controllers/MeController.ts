import { Request, Response } from "express";
import vrchat from "../services/vrchat";

export class MeController {

    static async getMe(req: Request, res: Response) {

        if (!vrchat.authenticated) {

            return res.status(401).json({
                success: false,
                message: "Not authenticated"
            });

        }

        const me = await vrchat.getCurrentUser();

        return res.json({
            success: true,
            data: me
        });

    }

}