import time
import aiohttp
import discord
from discord.ext import commands
from discord.commands import option 
import random
import json
import aiohttp
from bisect import bisect_right
import aiosqlite
from wom import Client as WOMClient
import logging

from config import GUILD_IDS, load_json, save_json, admin_required, conch_responses, emojis, ongoing_games, player_stats, update_stats, extra_help, answers




logger = logging.getLogger("osrs_bot")
logger.setLevel(logging.DEBUG)

SKILL_ICONS = {
    "attack": "⚔️", "hitpoints": "❤️", "mining": "⛏️",
    "strength": "💪", "agility": "🤸", "smithing": "⚙️",
    "defence": "🛡️", "herblore": "🌿", "fishing": "🎣",
    "ranged": "🏹", "thieving": "🕵️", "cooking": "🍳",
    "prayer": "✝️", "crafting": "🎨", "firemaking": "🔥",
    "magic": "✨", "fletching": "🏹", "woodcutting": "🪓",
    "runecrafting": "🔮", "slayer": "🐉", "farming": "🌾",
    "construction": "🏠", "hunter": "🐾", "overall": "📊"
}




# XP table for levels 1–126 (only need thresholds until 126)
LEVEL_XP = [0]
xp = 0
for lvl in range(1, 126):
    xp += int(lvl + 300 * 2 ** (lvl / 7.0))
    LEVEL_XP.append(xp // 4)
LEVEL_XP.append(LEVEL_XP[-1])  # pad for safety

def get_virtual_level(xp_amount):
    level = bisect_right(LEVEL_XP, xp_amount) - 1
    return min(level, 126)

def xp_to_next(xp_amount):
    lvl = get_virtual_level(xp_amount)
    if lvl >= 126:
        return 0
    return LEVEL_XP[lvl + 1] - xp_amount











logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("osrs_bot")

class OSRSSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "osrs_links.db"
        self.wom = WOMClient()

    async def cog_load(self):
        await self.wom.start()  # ← 💥 Required to initialize the HTTP client
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_links (
                    discord_id TEXT,
                    rsn TEXT
                )
            """)
            await db.commit()

    async def _verify_rsn(self, rsn: str) -> bool:
        rsn_fixed = rsn.replace(" ", "_")
        try:
            data = await self.wom.players.get_details(rsn_fixed)
            logger.debug(f"✅ API success for RSN '{rsn_fixed}': {data.username}")
            return True
        except Exception as e:
            logger.debug(f"❌ API error for RSN '{rsn_fixed}': {e}", exc_info=True)
            return False






    @discord.slash_command(name="fetch_xp", description="Fetch today's XP gains for a player.")
    async def fetch_xp(
        self, 
        ctx: discord.ApplicationContext, 
        username: str, 
        period: str = "day"
        ):
        """!xp <username> [day|week|month] — get XP gained"""
        period = period.lower()
        if period not in ("day", "week", "month"):
            await ctx.send("❌ Period must be 'day', 'week', or 'month'.")
            return

        await ctx.trigger_typing()
        url = f"https://api.wiseoldman.net/v2/players/{username.replace(' ', '_')}/gained"
        params = {"period": period}

        async with aiohttp.ClientSession() as session:
            resp = await session.get(url, params=params)
            if resp.status == 404:
                return await ctx.send(f"❌ No data found for `{username}` — are they linked?")
            if resp.status != 200:
                return await ctx.send("⚠️ API error — please try again later.")
            payload = await resp.json()

        skills = payload.get("data", {}).get("skills", {})
        if not skills:
            return await ctx.send(f"❌ No {period}-XP data available — have they linked recently?")

        entries = []
        for skill, info in skills.items():
            xp = info.get("experience")
            if isinstance(xp, (int, float)) and xp > 0:
                icon = SKILL_ICONS.get(skill.lower(), "")
                entries.append((icon, skill.capitalize(), xp))

        if not entries:
            return await ctx.send(f"⚠️ `{username}` hasn’t gained any {period}-XP yet.")

        entries.sort(key=lambda e: e[2], reverse=True)

        embed = discord.Embed(
            title=f"📆 XP Gains this {period.capitalize()} for {username}",
            color=discord.Color.blue()
        )
        for icon, skill_name, xp in entries:
            embed.add_field(name=f"{icon} {skill_name}", value=f"{xp:,} XP", inline=True)

        await ctx.send(embed=embed)
            
            
            
            
            
    @discord.slash_command(name="fetch_levels", description="Fetch current skill levels for a player.")    
    async def fetch_levels(
        self, 
        ctx: discord.ApplicationContext,
        username: str
        ):
        await ctx.trigger_typing()
        url = f"https://api.wiseoldman.net/v2/players/{username.replace(' ', '_')}"
        async with aiohttp.ClientSession() as session:
            resp = await session.get(url)
            if resp.status == 404:
                return await ctx.send(f"❌ `{username}` not found or not tracked.")
            if resp.status != 200:
                return await ctx.send("⚠️ API error — please try later.")
            payload = await resp.json()

        data = payload.get("latestSnapshot", {}).get("data", {}).get("skills", {})
        if not data:
            return await ctx.send("❌ No skill data available.")

        ordered = [
            "attack", "hitpoints", "mining", "strength", "agility", "smithing",
            "defence", "herblore", "fishing", "ranged", "thieving", "cooking",
            "prayer", "crafting", "firemaking", "magic", "fletching", "woodcutting",
            "runecrafting", "slayer", "farming", "construction", "hunter"
        ]

        # Build table rows
        rows = []
        for skill in ordered:
            d = data.get(skill, {})
            xp_amt = d.get("experience", 0)
            lvl = d.get("level", get_virtual_level(xp_amt))
            virt = get_virtual_level(xp_amt)
            to_next = xp_to_next(xp_amt)
            icon = SKILL_ICONS.get(skill, "")
            level_text = f"{lvl}" + (f" (V{virt})" if virt != lvl else "")
            xp_text = f"{xp_amt:,}"
            to_next_text = f"{to_next:,}" if to_next > 0 else "-"
            rows.append((f"{icon} {skill.capitalize()}",
                        level_text, xp_text, to_next_text))

        total_xp = data.get("overall", {}).get("experience", 0)
        total_lvl = data.get("overall", {}).get("level", get_virtual_level(total_xp))
        total_virt = get_virtual_level(total_xp)
        total_to_next = xp_to_next(total_xp)
        rows.append(("🧠 Total",
                    f"{total_lvl}" + (f" (V{total_virt})" if total_virt != total_lvl else ""),
                    f"{total_xp:,}",
                    f"{total_to_next:,}" if total_to_next > 0 else "-"))

        # Build embed with inline table
        description = "`{:<15} {:<10} {:<15} {:<15}`\n".format("Skill", "Level", "XP", "To Next")
        description += "\n".join(
            "`{:<15} {:<10} {:<15} {:<15}`".format(c1, c2, c3, c4) for c1, c2, c3, c4 in rows
        )

        embed = discord.Embed(
            title=f"📊 OSRS Skills for {username}",
            description=description,
            color=discord.Color.dark_gold()
        )
        await ctx.send(embed=embed)



    @discord.slash_command(name="linkosrs", description="Link your OSRS account.")
    async def linkosrs(self, ctx: discord.ApplicationContext, rsn: str):
        rsn = rsn.strip()
        await ctx.defer()
        valid = await self._verify_rsn(rsn)
        if not valid:
            return await ctx.followup.send(f"❌ RSN `{rsn}` not found or validation failed.")
        
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                "INSERT INTO user_links (discord_id, rsn) VALUES (?, ?)",
                (str(ctx.author.id), rsn)
            )
            await db.commit()
        await ctx.followup.send(f"✅ Linked RSN `{rsn}` successfully!")

    @discord.slash_command(name="unlinkosrs", description="Unlink your OSRS account.")
    async def unlinkosrs(self, ctx: discord.ApplicationContext, rsn: str):
        rsn = rsn.strip()
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute(
                "DELETE FROM user_links WHERE discord_id = ? AND rsn = ?",
                (str(ctx.author.id), rsn)
            )
            await db.commit()
        if cursor.rowcount == 0:
            return await ctx.respond(f"❌ You didn't have RSN `{rsn}` linked.")
        await ctx.respond(f"✅ Unlinked RSN `{rsn}` from your account.")

    @discord.slash_command(name="myosrs", description="List your linked OSRS accounts.")
    async def myosrs(self, ctx: discord.ApplicationContext):
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute(
                "SELECT rsn FROM user_links WHERE discord_id = ?",
                (str(ctx.author.id),)
            )
            rows = await cursor.fetchall()
        if not rows:
            return await ctx.respond("❌ You have no linked OSRS accounts.")
        await ctx.respond("🧾 Your linked OSRS accounts: " + ", ".join(r[0] for r in rows))

    @discord.slash_command(name="getosrs", description="Get another user's linked OSRS accounts.")
    async def getosrs(self, ctx: discord.ApplicationContext, user: discord.Member):
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute(
                "SELECT rsn FROM user_links WHERE discord_id = ?",
                (str(user.id),)
            )
            rows = await cursor.fetchall()
        if not rows:
            return await ctx.respond(f"❌ {user.display_name} has no linked OSRS accounts.")
        await ctx.respond(f"🧾 {user.display_name}'s linked OSRS accounts: " + ", ".join(r[0] for r in rows))





    @discord.slash_command(name="testverify")
    async def testverify(self, ctx: discord.ApplicationContext, *, rsn: str):
        """Test the verification and log API response."""
        await ctx.send(f"Testing RSN: `{rsn}` (check console logs)")
        result = await self._verify_rsn(rsn)
        await ctx.send(f"Result: {'✅ found' if result else '❌ not found'}")

    @discord.slash_command(name="linkosrs")
    async def linkosrs(self, ctx: discord.ApplicationContext, *, rsn: str):
        await ctx.send("Running link…")
        valid = await self._verify_rsn(rsn)
        await ctx.send(f"Link check: {'✅' if valid else '❌'}")

def setup(client):
    client.add_cog(OSRSSystem(client))