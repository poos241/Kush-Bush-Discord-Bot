import discord
from discord.ext import commands
import os
import csv
import re
import hashlib
import shutil
from datetime import datetime
from rapidfuzz import fuzz, process
import math
import urllib.parse
import asyncio


from config import GUILD_IDS  # to make safe URLs


GAMES_DIR = {
    "C": r"C:\EmuVR\Games",
    "H": r"H:\LaunchBox\games"
}
VALID_GAME_EXTS = {".zip", ".7z", ".iso", ".bin", ".cue", ".nes", ".sfc", ".smc", ".gba", ".gb", ".gbc", ".n64", ".v64", ".z64"}  # expand as needed



# ---------- EMUVR CONFIG ----------
GAMES_DIRS = {
    "C": r"C:\EmuVR\Games",
    "H": r"H:\LaunchBox\games"
}
ART_DIR     = r"C:\EmuVR\Custom\Labels"
DRY_RUN = False
MIN_ACCEPT_SCORE = 72
VALID_GAME_EXTS = {
    ".zip",".7z",".rar",".iso",".bin",".cue",".chd",".img",".nrg",
    ".nes",".sfc",".smc",".gba",".gb",".gbc",".nds",
    ".n64",".v64",".z64",".wad",".apk",".xiso"
}


ROM_FOLDER = "roms"
BASE_URL = "http://YOUR_IP:5000/roms"  # replace YOUR_IP with LAN or public IP

ROM_INDEX = {}


def build_rom_index(GAMES_PATHS):
    """
    C:\EmuVR\Games
    H:\LaunchBox\games
    """
    GAMES_PATHS = GAMES_DIRS
    for base_path in GAMES_PATHS:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                ROM_INDEX[file.lower()] = os.path.join(root, file)
    print(f"[INFO] Indexed {len(ROM_INDEX)} ROMs")


# -----------------------------------


# ---------- HELPER FUNCTIONS ----------

def scan_drive(drive_path):
    """Blocking scan logic that runs in a thread."""
    systems_found = 0
    rom_count = 0
    total_size = 0

    for system in os.listdir(drive_path):
        system_path = os.path.join(drive_path, system)
        if not os.path.isdir(system_path):
            continue
        systems_found += 1

        for root, _, files in os.walk(system_path):
            rom_count += len(files)
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
                except (OSError, FileNotFoundError):
                    continue

    return systems_found, rom_count, total_size

def human_size(num_bytes: int, precision: int = 2) -> str:
    """Return human readable size (B, KB, MB, GB, TB, PB)."""
    if num_bytes < 0:
        num_bytes = 0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    # Avoid trailing .00 for B and KB if you prefer, here we keep 2 decimals for consistency
    return f"{size:.{precision}f} {units[i]}"

def get_folder_size(path: str) -> int:
    """Total size in bytes of all files under path."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
            except OSError:
                # skip unreadable files
                continue
    return total

def list_games_in_folder(path: str) -> list[str]:
    """Return list of valid game file names (filtered by VALID_GAME_EXTS)."""
    try:
        entries = os.listdir(path)
    except OSError:
        return []
    files = []
    for f in entries:
        full = os.path.join(path, f)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(f)[1].lower()
        if VALID_GAME_EXTS is None or ext in VALID_GAME_EXTS:
            files.append(f)
    return files

def search_rom(game_name: str):
    """
    Fuzzy search for a ROM name in the index.
    Returns the first match path or None.
    """
    game_name = game_name.lower()
    for filename, path in ROM_INDEX.items():
        if game_name in filename:
            return path
    return None

def format_size(bytes_size: int) -> str:
    """Convert bytes into human-readable MB/GB string."""
    if bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"
    
def normalize(name: str) -> str:
    base = re.sub(r"(\([^)]*\)|\[[^\]]*\]|\{[^}]*\})", " ", name)
    base = re.sub(r"[\._\-]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip().lower()
    return base

def score_pair(g_norm: str, a_norm: str) -> int:
    s1 = fuzz.WRatio(g_norm, a_norm)
    s2 = fuzz.token_set_ratio(g_norm, a_norm)
    s3 = fuzz.partial_ratio(g_norm, a_norm)
    return int(round(0.4 * s1 + 0.4 * s2 + 0.2 * s3))

def file_hash(path, block_size=65536):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hasher.update(block)
    return hasher.hexdigest()

def safe_move(src, dst):
    base, ext = os.path.splitext(dst)
    candidate = dst
    n = 1
    while os.path.exists(candidate):
        if os.path.abspath(src) == os.path.abspath(candidate):
            return candidate
        if file_hash(src) == file_hash(candidate):
            return candidate
        candidate = f"{base} ({n}){ext}"
        n += 1
    shutil.move(src, candidate)
    return candidate

def deduplicate_artworks(arts):
    seen = {}
    removed = 0
    for art in arts[:]:
        h = file_hash(art["path"])
        if h in seen:
            if not DRY_RUN:
                os.remove(art["path"])
            arts.remove(art)
            removed += 1
        else:
            seen[h] = art
    return removed

def run_renamer():
    results = {
        "systems": 0,
        "systems_data": [],
        "ok": 0,
        "warn": 0,
        "fail": 0,
        "dups": 0,
        "log_path": "renamer_log.txt"
    }

    with open(results["log_path"], "w", encoding="utf-8") as log_file:
        for drive, paths in GAMES_DIRS.items():
            for base_path in paths:  # now we can handle multiple paths per drive
                if not os.path.exists(base_path):
                    log_file.write(f"[WARN] Path does not exist: {base_path}\n")
                    continue

                for system in sorted(os.listdir(base_path), key=str.lower):
                    sys_path = os.path.join(base_path, system)
                    if not os.path.isdir(sys_path):
                        continue

                    # process system folder here (rename artwork, count files, etc.)
                    sys_data = {
                        "system": system,
                        "ok": 0,
                        "warn": 0,
                        "fail": 0,
                        "dups_removed": 0
                    }

                    # TODO: your artwork renaming logic
                    # Example counters:
                    results["ok"] += sys_data["ok"]
                    results["warn"] += sys_data["warn"]
                    results["fail"] += sys_data["fail"]
                    results["dups"] += sys_data["dups_removed"]

                    results["systems_data"].append(sys_data)
                    results["systems"] += 1

                    log_file.write(f"[INFO] Processed system: {system} in {base_path}\n")

    return results


async def send_game_dm(user: discord.User, rom_path: str, boxart_path: str):
    try:
        # Step 1: Send boxart & embed
        embed = discord.Embed(title="Here’s your game!", color=discord.Color.blue())
        embed.add_field(name="Game", value=os.path.basename(rom_path), inline=False)

        files = []
        if os.path.exists(boxart_path):
            files.append(discord.File(boxart_path, filename=os.path.basename(boxart_path)))

        print(f"[DEBUG] Sending embed to {user}...")
        await user.send(embed=embed, files=files)
        print(f"[DEBUG] Embed sent to {user}")

        # Step 2: Send ROM as a *separate* message
        if os.path.exists(rom_path):
            rom_file = discord.File(rom_path, filename=os.path.basename(rom_path))
            print(f"[DEBUG] Sending ROM file {rom_path} to {user}...")
            await user.send(file=rom_file)
            print(f"[DEBUG] ROM file sent to {user}")

    except discord.Forbidden:
        print(f"❌ Cannot DM {user} (privacy settings).")
    except Exception as e:
        print(f"❌ Error sending DM to {user}: {e}")


class PagedView(discord.ui.View):
    def __init__(self, results, query, user_id,  per_page=15):
        super().__init__(timeout=120)  # 2 min timeout
        self.results = results
        self.query = query
        self.per_page = per_page
        self.page = 0
        self.user_id = user_id  # store who created it
        super().__init__(timeout=120)
        ##self.game = game
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id
    
    
    
    def make_embed(self):
        
        start = self.page * self.per_page
        end = start + self.per_page
        page_results = self.results[start:end]

        embed = discord.Embed(
            title=f"🎮 Search Results for: {self.query}",
            description=f"Showing results {start+1}–{min(end, len(self.results))} of {len(self.results)}",
            color=discord.Color.green()
        )

        for game in page_results:
            size = os.path.getsize(game["path"])
            art_status = "✅ Artwork Found" if game["art"] else "❌ No Artwork"

            embed.add_field(
                name=f"{game['file']} ({game['system']}, Drive {game['drive']})",
                value=(f"📂 Path: `{game['path']}`\n"
                       f"📊 Match Score: **{game['score']}**\n"
                       f"💾 Size: **{format_size(size)}**\n"
                       f"🖼 Artwork: {art_status}\n"
                       f"🔑 SHA1: `{game['hash']}`"),
                inline=False
            )

        embed.set_footer(text=f"Page {self.page+1}/{math.ceil(len(self.results)/self.per_page)}")
        return embed


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Restrict controls to command author only."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the user who ran this command can use these buttons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, button, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
    async def next(self, button, interaction: discord.Interaction):
        if (self.page + 1) * self.per_page < len(self.results):
            self.page += 1
        await interaction.response.edit_message(embed=self.make_embed(), view=self)
        
    @discord.ui.button(label="📥 Download ROM", style=discord.ButtonStyle.primary)
    async def download_button(self, button, interaction: discord.Interaction):
        try:
            size = os.path.getsize(self.game["path"])
            # Discord file size limits: 25MB for free bots, 100MB+ for verified bots with Nitro
            if size > 25 * 1024 * 1024:
                await interaction.response.send_message(
                    f"⚠️ File too large to send directly ({format_size(size)}).",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                content=f"📥 Here’s your ROM: **{self.game['file']}**",
                file=discord.File(self.game["path"])
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to send file: {e}", ephemeral=True
            )



# ---------- DISCORD COG ----------
class EmuVRCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.GAMES_DIRS = {
            "C": [r"C:\EmuVR\Games"],
            "H": [
                r"H:\LaunchBox\games",
                r"H:\Hyperspin\Emulators\Roms\Games"
            ]
        }
    @discord.slash_command(
    name="rename_game_art",
    description="Renames EmuVR artwork based on game names"
    )
    async def rename_game_art(self, ctx: discord.ApplicationContext):
        # Initial response (deferred so we have time to process)
        await ctx.defer()  

        results = run_renamer()

        embed = discord.Embed(
            title="🎮 EmuVR Artwork Renamer Results",
            description=f"Processed **{results['systems']} systems**",
            color=discord.Color.blue()
        )

        for sys_data in results["systems_data"]:
            embed.add_field(
                name=f"🖥 {sys_data['system']}",
                value=(f"✅ Renamed: **{sys_data['ok']}**\n"
                    f"⚠️ Warnings: **{sys_data['warn']}**\n"
                    f"❌ Failed: **{sys_data['fail']}**\n"
                    f"🗑 Duplicates removed: **{sys_data['dups_removed']}**"),
                inline=False
            )

        embed.add_field(
            name="📊 Totals",
            value=(f"✅ Renamed: **{results['ok']}**\n"
                f"⚠️ Warnings: **{results['warn']}**\n"
                f"❌ Failed: **{results['fail']}**\n"
                f"🗑 Duplicates removed: **{results['dups']}**"),
            inline=False
        )

        embed.set_footer(text="EmuVR Artwork Renamer")

        # Edit the deferred response with the embed
        await ctx.edit(embed=embed)

        # If a log file exists, send it as a follow-up
        if os.path.exists(results["log_path"]):
            await ctx.send_followup(
                "📜 Here’s the renaming log:",
                file=discord.File(results["log_path"])
            )



    
    @discord.slash_command(
    name="findgame",
    description="Search for a game in your EmuVR library",
    guild_ids=None  # 👈 important: None = global command (works in DMs too)
    )
    async def findgame(
        self, 
        ctx: discord.ApplicationContext, 
        query: str,
        drive: str = "all",
        system: str = None  # optional filter by system/console
        
    ):
        await ctx.respond(f"🔎 Searching for **{query}** on drive **{drive.upper()}** ...")

        found_games = []
        query_norm = normalize(query)

        # select drives
        search_dirs = []
        if drive.lower() == "all":
            search_dirs = GAMES_DIRS.items()
        else:
            if drive.upper() in GAMES_DIRS:
                search_dirs = [(drive.upper(), GAMES_DIRS[drive.upper()])]
            else:
                await ctx.respond(embed=discord.Embed(
                    title="❌ Invalid Drive",
                    description=f"Drive **{drive}** is not configured. Available: {', '.join(GAMES_DIRS.keys())} or 'all'",
                    color=discord.Color.red()
                ))
                return

        for drive_name, base_dir in search_dirs:
            for sys_name in sorted(os.listdir(base_dir), key=str.lower):
                g_dir = os.path.join(base_dir, sys_name)
                if not os.path.isdir(g_dir):
                    continue

                # system filter
                if system and sys_name.lower() != system.lower():
                    continue

                for fn in os.listdir(g_dir):
                    p = os.path.join(g_dir, fn)
                    if not os.path.isfile(p):
                        continue
                    stem, _ = os.path.splitext(fn)
                    g_norm = normalize(stem)

                    score = score_pair(query_norm, g_norm)
                    if score < max(MIN_ACCEPT_SCORE, 80):
                        continue
                    if len(query_norm.split()) > 3 and len(g_norm.split()) < 2:
                        continue

                    # --- Part 1: Artwork status ---
                    art_dir = os.path.join(ART_DIR, sys_name)
                    has_art = False
                    if os.path.isdir(art_dir):
                        for art_fn in os.listdir(art_dir):
                            art_stem, art_ext = os.path.splitext(art_fn)
                            if normalize(art_stem) == g_norm and art_ext.lower() in VALID_GAME_EXTS:
                                has_art = True
                                break

                    # --- Part 2: ROM hash ---
                    try:
                        sha1 = hashlib.sha1()
                        with open(p, "rb") as f:
                            for block in iter(lambda: f.read(65536), b""):
                                sha1.update(block)
                        rom_hash = sha1.hexdigest()[:16]  # short hash
                    except Exception:
                        rom_hash = "Error hashing"

                    found_games.append({
                        "drive": drive_name,
                        "system": sys_name,
                        "file": fn,
                        "path": p,
                        "score": score,
                        "art": has_art,
                        "hash": rom_hash
                    })

        if not found_games:
            await ctx.respond(embed=discord.Embed(
                title="❌ No Matches Found",
                description=f"Could not find any game matching **{query}** on drive **{drive}**.",
                color=discord.Color.red()
            ))
            return

        found_games.sort(key=lambda g: g["score"], reverse=True)
        best_score = found_games[0]["score"]
        filtered = [g for g in found_games if g["score"] >= best_score - 5]

        view = PagedView(filtered, query, ctx.user.id,)
        await ctx.respond(embed=view.make_embed(), view=view)



    @discord.slash_command(name="request_game", description="Request a game ROM and receive it in DMs")
    async def request_game(
        self,
        ctx: discord.ApplicationContext,
        game: discord.Option(str, "Enter the game name"), # type: ignore
        system: discord.Option(str, "Enter the system (NES, SNES, etc.)", required=False) # type: ignore
    ):
        await ctx.defer()
        boxart_path = ART_DIR
        matches = []

        rom_path = search_rom(game)
        if not rom_path:
            await ctx.respond(f"❌ Couldn’t find `{game}` in the ROM index.")
            return

        # Optional: find box art
        boxart_path = rom_path.replace(os.path.splitext(rom_path)[1], ".png")
        embed = discord.Embed(title=f"Here’s your game!", color=discord.Color.blue())
        embed.add_field(name="Game", value=os.path.basename(rom_path), inline=False)

        files = []
        if os.path.exists(boxart_path):
            files.append(discord.File(boxart_path, filename=os.path.basename(boxart_path)))

        # Send DM in safe way
        try:
            await ctx.author.send(embed=embed, files=files)
            await ctx.author.send(file=discord.File(rom_path))
            await ctx.respond("📩 Check your DMs!", ephemeral=True)
        except discord.Forbidden:
            await ctx.respond("❌ I can’t DM you (check your privacy settings).", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Error sending ROM: {e}", ephemeral=True)


    @discord.slash_command(
        name="scanlibrary",
        description="Scans all game/rom folders and reports systems, games, and total size"
    )
    async def scanlibrary(self, ctx: discord.ApplicationContext):
        await ctx.respond("🕵️ Scanning your EmuVR library... please wait!")

        system_rows: list[tuple[str, int, int]] = []  # (label, num_games, size_bytes)
        total_games = 0
        total_size_bytes = 0
        total_systems = 0

        # Loop through each root drive (C, H, etc.)
        for drive, root_path in GAMES_DIR.items():
            if not isinstance(root_path, (str, bytes, os.PathLike)) or not os.path.exists(root_path):
                # Skip invalid/missing roots silently
                continue

            # Loop through systems inside each root
            try:
                systems = sorted(os.listdir(root_path), key=str.lower)
            except OSError:
                continue

            for system in systems:
                sys_path = os.path.join(root_path, system)
                if not os.path.isdir(sys_path):
                    continue

                games = list_games_in_folder(sys_path)
                num_games = len(games)

                size_bytes = get_folder_size(sys_path)

                total_games += num_games
                total_size_bytes += size_bytes
                total_systems += 1

                label = f"{drive}: {system}"
                system_rows.append((label, num_games, size_bytes))

        # Sort systems by size (desc) to surface the big ones first (optional)
        system_rows.sort(key=lambda t: t[2], reverse=True)

        # Build paginated embeds (24 fields max per embed to stay under 25)
        embeds: list[discord.Embed] = []
        chunk_size = 24

        for i in range(0, len(system_rows), chunk_size):
            chunk = system_rows[i:i + chunk_size]
            page = (i // chunk_size) + 1
            total_pages = (len(system_rows) + chunk_size - 1) // chunk_size or 1

            embed = discord.Embed(
                title=f"🎮 EmuVR Library Scan Results (Page {page}/{total_pages})",
                color=discord.Color.green()
            )

            for label, num_games, size_b in chunk:
                embed.add_field(
                    name=f"🖥️ {label}",
                    value=(
                        f"Games: **{num_games}**\n"
                        f"Size: **{human_size(size_b)}**"
                    ),
                    inline=False
                )

            embeds.append(embed)

        # Add totals at the end (or into the last embed if there is at least one)
        totals_text = (
            f"**Systems:** {total_systems}\n"
            f"**Games:** {total_games}\n"
            f"**Size:** {human_size(total_size_bytes)}"
        )

        if not embeds:
            # No systems found — send a simple one
            empty = discord.Embed(
                title="🎮 EmuVR Library Scan Results",
                description="No systems found.",
                color=discord.Color.orange()
            )
            empty.add_field(name="📊 Totals", value=totals_text, inline=False)
            await ctx.followup.send(embed=empty)
            return

        # Put totals in the last embed (within the 25-field limit)
        embeds[-1].add_field(name="📊 Totals", value=totals_text, inline=False)

        # Send all pages
        for embed in embeds:
            await ctx.followup.send(embed=embed)

    
    
    
    @discord.slash_command(name="scan_storage", description="Scan drives and summarize ROM/system counts + storage usage")
    async def scan_storage(self, ctx):
        await ctx.defer()  # prevent interaction timeout while scanning

        embed = discord.Embed(
            title="📦 Storage Scan Results",
            color=discord.Color.blurple()
        )

        for drive_name, paths in self.GAMES_DIRS.items():
            if isinstance(paths, str):
                paths = [paths]  # normalize single path to list

            total_systems = 0
            total_roms = 0
            total_size = 0

            for path in paths:
                if not os.path.exists(path):
                    continue

                systems_found, rom_count, size = await asyncio.to_thread(scan_drive, path)
                total_systems += systems_found
                total_roms += rom_count
                total_size += size

            if total_systems == 0 and total_roms == 0:
                embed.add_field(
                    name=f"{drive_name} ❌",
                    value="No valid paths found.",
                    inline=False
                )
            else:
                size_gb = total_size / (1024**3)
                embed.add_field(
                    name=f"{drive_name}",
                    value=f"🖥️ Systems: **{total_systems}**\n🎮 ROMs: **{total_roms}**\n💾 Size: **{size_gb:.2f} GB**",
                    inline=False
                )

        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(EmuVRCog(client))
