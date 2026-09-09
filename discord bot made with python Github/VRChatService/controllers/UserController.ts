import { Request, Response } from "express";
import UserService from "../services/UserService";

export class UserController {

    static async lookup(req: Request, res: Response) {

        try {

            const username = req.params.username;

            if (!username || Array.isArray(username)) {
                return res.status(400).json({
                    success: false,
                    message: "Invalid username."
                });
            }

            const user = await UserService.getUserByUsername(username);

            if (!user) {
                return res.status(404).json({
                    success: false,
                    message: "User not found."
                });
            }

            return res.json({
                success: true,
                data: user
            });

        } catch (err) {

            console.error(err);

            return res.status(500).json({
                success: false,
                message: "Internal Server Error"
            });

        }

    }

}