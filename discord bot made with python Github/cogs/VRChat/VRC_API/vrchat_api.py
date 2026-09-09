import aiohttp

BASE_URL = "http://127.0.0.1:3000"


class VRChatAPI:
    def __init__(self):
        self.BASE_URL = "http://127.0.0.1:3000"
        
        
        
    async def get_status(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/status") as response:
                return await response.json()

    async def get_me(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/me") as response:
                return await response.json()

    async def lookup_user(self, username: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/user/{username}"
            ) as response:

                return await response.json()


    
    
    
    async def start_verification(self, guild_id, user_id, username):

        async with aiohttp.ClientSession() as session:

            url = f"{self.BASE_URL}/verification/start"

            payload = {
                "guildId": str(guild_id),
                "discordId": str(user_id),
                "username": username
            }

            async with session.post(url, json=payload) as response:
                print("=" * 50)
                print("STATUS:", response.status)

                text = await response.text()

                print(text)
                print("=" * 50)
                text = await response.text()

                try:
                    return await response.json()
                except Exception:
                    return {"error": text}

    async def send_friend_request(self, session_id):

        async with aiohttp.ClientSession() as session:

            async with session.post(

                "http://127.0.0.1:3000/friends/send",

                json={

                    "sessionId": session_id

                }

            ) as response:

                return await response.json()
            
    
    async def get_linked_account(self, guild_id, discord_id):

        async with aiohttp.ClientSession() as session:

            url = (
                f"{self.BASE_URL}/link/"
                f"{guild_id}/{discord_id}"
            )

            async with session.get(url) as response:

                if response.status == 404:
                    return {"success": False}

                return await response.json()
    
    
    async def start_group_verification(self, discord_id):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:3000/community/start",
                json={"discordId": str(discord_id)}
            ) as response:
                return await response.json()
            
            
            

    async def confirm_link(self, session_id):

        async with aiohttp.ClientSession() as session:

            async with session.post(
                "http://127.0.0.1:3000/link/confirm",
                json={"sessionId": session_id}
            ) as response:

                if response.status != 200:

                    print("LINK ERROR")
                    print(await response.text())

                    return {
                        "success": False
                    }

                return await response.json()    
    
    
        
    # Helper function to look up a user's VRChat ID by their username
    async def lookup_user_id(self, username: str):
        async with aiohttp.ClientSession() as session:
            # Assuming your port 3000 server has a user lookup route
            url = "http://127.0.0" 
            try:
                async with session.get(url, params={"username": username}) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Change "id" to whatever key your backend uses to return the user ID (e.g., usr_...)
                        return data.get("id") 
                    return None
            except:
                return None

   

    async def link_account(self, session_id: str):

        async with aiohttp.ClientSession() as session:

            async with session.post(
                f"{self.BASE_URL}/link/confirm",
                json={
                    "sessionId": session_id
                }
            ) as response:

                if response.status != 200:

                    print("LINK ERROR:", response.status)
                    print(await response.text())

                    return {
                        "success": False
                    }

                return await response.json()  
            
            
    async def unlink_account(self, guild_id: int, discord_id: int):

        async with aiohttp.ClientSession() as session:

            async with session.delete(
                f"{self.BASE_URL}/link",
                json={
                    "guildId": str(guild_id),
                    "discordId": str(discord_id)
                }
            ) as response:

                return await response.json()
            
             
vrchat = VRChatAPI()