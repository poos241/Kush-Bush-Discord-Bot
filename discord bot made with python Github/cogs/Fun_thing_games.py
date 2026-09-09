import time
import aiohttp
import discord
from discord.ext import commands
from discord.commands import option 
import random
import json
import aiohttp
from bisect import bisect_right


from config import GUILD_IDS, load_json, save_json, admin_required, conch_responses, emojis, ongoing_games, player_stats, update_stats, extra_help, answers



RPS_DATA_FILE = "rps_data.json"


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



class FunCog(commands.Cog):
    def __init__(self, client):
        self.bot = client
        self.db = load_json(RPS_DATA_FILE)

    def save_db(self):
        save_json(RPS_DATA_FILE, self.db)

 
      
 

    @discord.slash_command(
        name="flip_coin",
        description="Flip a coin and get heads or tails."
    )
    @extra_help("Flip a coin and get either heads or tails. Usage: /flip_coin")
    async def flip_coin(
        self, 
        interaction: discord.ApplicationContext
        ):
        """Flips a coin and returns heads or tails."""  # type: ignore
        result = random.choice(["Heads", "Tails"])
        await interaction.respond(f"🪙 It's **{result}**!")
        
        
        

    @discord.slash_command(name="conch", description="Ask the Magic Conch Shell a question.")
    @extra_help("Ask the Magic Conch Shell a question and it will give you a random answer. Usage: /conch")
    async def conch(
        self,
        interaction: discord.ApplicationContext
    ):
        """Ask the Magic Conch Shell a question and it will give you a random answer."""  # type: ignore
        cooldownconch = {}
        COOLDOWN_SECONDS_Conch = 60
        await interaction.response.defer()
        user_id = interaction.author.id
        guild_id = interaction.guild.id
        now = time.time()

        # Ensure guild key exists
        if guild_id not in cooldownconch:
            cooldownconch[guild_id] = {}

        # Reference the user_cooldowns for this guild
        user_cooldowns = cooldownconch[guild_id]

        # Check cooldown
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS_Conch:
                remaining = round(COOLDOWN_SECONDS_Conch - elapsed, 1)
                await interaction.followup.send(f"⏳ You're on cooldown {interaction.author.mention}! Try again in {remaining} seconds.")
                return

        # Set new cooldown
        user_cooldowns[user_id] = now
        """
        Responds with a random answer like the Magic Conch Shell.
        Usage: /conch
        """
        response = random.choice(conch_responses)
        await interaction.followup.send(f"🔮 Magic Conch Shell says: '{response}'")    
        
    @discord.slash_command(name="roll", description="lets the user roll a dice for things like dnd")  # Note: fixed `guild_id` -> `guild_ids`
    @extra_help("Rolls a dice for DND or other games. You can specify the number of dice, the number of sides on each die, and a modifier to add or subtract from the total roll.")
    async def roll(
        self,
        interaction: discord.ApplicationContext,
        number_of_dice: discord.Option(int, "How many dice to roll", default=1),  # type: ignore
        dice_sides: discord.Option(int, "How many sides each die has", default=20),  # type: ignore
        modifier: discord.Option(int, "Modifier to add or subtract", default=0)  # type: ignore
    ):
        """Rolls a dice for DND or other games."""  
        cooldown = {}
        COOLDOWN_SECONDS = 60

        await interaction.response.defer()

        user_id = interaction.author.id
        guild_id = interaction.guild.id
        now = time.time()

        # Ensure guild key exists
        if guild_id not in cooldown:
            cooldown[guild_id] = {}

        user_cooldowns = cooldown[guild_id]

        # Cooldown check
        if user_id in user_cooldowns:
            elapsed = now - user_cooldowns[user_id]
            if elapsed < COOLDOWN_SECONDS:
                remaining = round(COOLDOWN_SECONDS - elapsed, 1)
                await interaction.followup.send(f"⏳ You're on cooldown {interaction.author.mention}! Try again in {remaining} seconds.")
                return

        # Set cooldown
        user_cooldowns[user_id] = now

        def roll_dice(num, sides, mod):
            rolls = [random.randint(1, sides) for _ in range(num)]
            total = sum(rolls) + mod
            return rolls, total

        rolls, total = roll_dice(number_of_dice, dice_sides, modifier)
        rolls_str = ', '.join(map(str, rolls))
        modifier_str = f" + {modifier}" if modifier >= 0 else f" - {abs(modifier)}"

        embed = discord.Embed(
            title="🎲 DND Dice Roll System",
            description="Here's your result:",
            color=discord.Color.red()
        )
        embed.add_field(
            name=f"🎲 You rolled {number_of_dice}d{dice_sides}{modifier_str}",
            value=f"🧮 Rolls: {rolls_str}\n🔢 Total: **{total}**",
            inline=False
        )

        await interaction.followup.send(embed=embed)
  


    @discord.slash_command(
        name="8ball",
        description="Ask any question to the bot.",
    )
    @extra_help("Ask the bot a question and it will give you a random answer. Usage: /8ball <question>")
    @option("question", description="The question you want to ask the bot")  # type: ignore
    async def eight_ball(self, interaction: discord.ApplicationContext,  *, question: str) -> None:
        """
        Ask any question to the bot.

        :param context: The hybrid command context.
        :param question: The question that should be asked by the user.
        """
       
        embed = discord.Embed(
            title="**:8ball: Magic 8 Ball :8ball:**",
            description=f"{random.choice(answers)}",
            color=0xBEBEFE,
        )
        embed.set_footer(text=f"The question was: {question}")
        await interaction.send(embed=embed)


    @discord.slash_command(name="randomfact", description="Get a random fact.")
    @extra_help("Get a random fact from the internet. Usage: /randomfact")
    async def randomfact(self, interaction: discord.ApplicationContext) -> None:
        """
        Get a random fact.

        :param context: The hybrid command context.
        """
        await interaction.defer() 
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://uselessfacts.jsph.pl/random.json?language=en"
            ) as request:
                if request.status == 200:
                    data = await request.json()
                    embed = discord.Embed(description=data["text"], color=0xD75BF4)
                else:
                    embed = discord.Embed(
                        title="Error!",
                        description="There is something wrong with the API, please try again later",
                        color=0xE02B2B,
                    )
                await interaction.followup.send(embed=embed)
    
    
    


    # Slash command to start a Rock-Paper-Scissors game
    @discord.slash_command(name="rps", description="Challenge someone to a game of Rock-Paper-Scissors, or play against the bot!")
    @extra_help("Challenge someone to a game of Rock-Paper-Scissors, or play against the bot. Usage: /rps <choice> [opponent]")
    @option("choice", description="Your choice for the game", choices=["rock", "paper", "scissors"]) # type: ignore
    @option("opponent", description="The person you want to challenge (optional)", required=False, type=discord.User) # type: ignore
    async def rps(
        self,
        interaction: discord.ApplicationContext, 
        choice: str, 
        opponent: discord.User = None
        ):
            """Start a Rock-Paper-Scissors game with an opponent or the bot."""  
            user_choice = choice.lower()

            # Check if user challenges the bot
            if opponent is None or opponent.bot:
                bot_choice = random.choice(list(emojis.keys()))
                if user_choice == bot_choice:
                    result = "It's a tie!"
                elif (user_choice == "rock" and bot_choice == " ") or \
                        (user_choice == "scissors" and bot_choice == "paper") or \
                        (user_choice == "paper" and bot_choice == "rock"):
                    result = "You win!"
                    update_stats(interaction.author.id, "bot")
                else:
                    result = "The bot wins!"
                    update_stats("bot", interaction.author.id)

                # Create embed for result
                embed = discord.Embed(title="Rock-Paper-Scissors Game", color=discord.Color.green())
                embed.add_field(name=f"{interaction.author.display_name}'s Choice", value=f"{emojis[user_choice]} {user_choice.capitalize()}", inline=True)
                embed.add_field(name="Bot's Choice", value=f"{emojis[bot_choice]} {bot_choice.capitalize()}", inline=True)
                embed.add_field(name="Result", value=result, inline=False)
                embed.set_author(name=interaction.author.display_name, icon_url=interaction.author.avatar.url)

                await interaction.respond(embed=embed)
                return

            # If the user challenges another human opponent
            if opponent == interaction.author:
                await interaction.respond("You can't play against yourself!", ephemeral=True)
                return

            if interaction.author.id in ongoing_games or opponent.id in ongoing_games:
                await interaction.respond("One of you is already in a game. Finish it before starting a new one.", ephemeral=True)
                return

            # Store the game state
            ongoing_games[interaction.author.id] = {"opponent": opponent.id, "choice": user_choice}
            ongoing_games[opponent.id] = {"challenger": interaction.author.id}

            # Send challenge embed
            embed = discord.Embed(title="Rock-Paper-Scissors Challenge", color=discord.Color.blue())
            embed.add_field(name=f"{interaction.author.display_name} has challenged {opponent.display_name}!", value="Use `/respond_rps` to accept or `/decline_rps` to decline.", inline=False)
            embed.set_thumbnail(url=interaction.author.avatar.url)
            await interaction.respond(embed=embed)

    # Command for the opponent to respond to the RPS challenge
    @discord.slash_command(name="respond_rps", description="Respond to a Rock-Paper-Scissors challenge.", )
    @extra_help("Respond to a Rock-Paper-Scissors challenge. Use this command to play against the challenger. Usage: /respond_rps <choice>")
    @option("choice", description="Your choice for the game", choices=["rock", "paper", "scissors"]) # type: ignore
    async def respond_rps(
    self,
    interaction: discord.ApplicationContext,
    choice: str
    ):
        """Respond to a Rock-Paper-Scissors challenge from another user."""  
        user_id = interaction.author.id
        game = ongoing_games.get(user_id)

        if not game or "challenger" not in game:
            await interaction.respond("You don't have any pending challenges.", ephemeral=True)
            return

        challenger_id = game["challenger"]
        challenger_choice = ongoing_games[challenger_id]["choice"]
        opponent_choice = choice.lower()

        # Determine the outcome
        if challenger_choice == opponent_choice:
            result = "It's a tie!"
        elif (challenger_choice == "rock" and opponent_choice == "scissors") or \
                (challenger_choice == "scissors" and opponent_choice == "paper") or \
                (challenger_choice == "paper" and opponent_choice == "rock"):
            result = f"{interaction.guild.get_member(challenger_id).mention} wins!"
            update_stats(challenger_id, interaction.author.id)
        else:
            result = f"{interaction.author.mention} wins!"
            update_stats(interaction.author.id, challenger_id)

        # Create embed for result
        embed = discord.Embed(title="Rock-Paper-Scissors Game", color=discord.Color.green())
        embed.add_field(name=f"{interaction.guild.get_member(challenger_id).display_name}'s Choice", value=f"{emojis[challenger_choice]} {challenger_choice.capitalize()}", inline=True)
        embed.add_field(name=f"{interaction.author.display_name}'s Choice", value=f"{emojis[opponent_choice]} {opponent_choice.capitalize()}", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        embed.set_thumbnail(url=interaction.author.avatar.url)

        # Send result and clean up game
        await interaction.respond(embed=embed)
        del ongoing_games[challenger_id]
        del ongoing_games[user_id]

    # Command for the opponent to decline the challenge
    @discord.slash_command(name="decline_rps", description="Decline a Rock-Paper-Scissors challenge.")
    @extra_help("Decline a Rock-Paper-Scissors challenge. Use this command if you don't want to play against the challenger. Usage: /decline_rps")
    async def decline_rps(
        self,
        interaction: discord.ApplicationContext
    ):
        """Decline a Rock-Paper-Scissors challenge from another user."""
        user_id = interaction.author.id
        game = ongoing_games.get(user_id)

        if not game or "challenger" not in game:
            await interaction.respond("You don't have any pending challenges.", ephemeral=True)
            return

        challenger_id = game["challenger"]

        # Update stats for the challenger
        update_stats(challenger_id, user_id)

        # Notify about decline
        embed = discord.Embed(title="Rock-Paper-Scissors Challenge Declined", color=discord.Color.red())
        embed.add_field(name="Challenge Declined", value=f"{interaction.author.display_name} declined the challenge. {interaction.guild.get_member(challenger_id).mention} wins by default.", inline=False)
        embed.set_thumbnail(url=interaction.author.avatar.url)

        # Send decline notification and clean up game
        await interaction.respond(embed=embed)
        del ongoing_games[challenger_id]
        del ongoing_games[user_id]




    # Slash command to view the leaderboard
    @discord.slash_command(name="leaderboard_rps", description="View the Rock-Paper-Scissors leaderboard.")
    @extra_help("View the Rock-Paper-Scissors leaderboard. This shows the top players based on their wins and losses. Usage: /leaderboard_rps")
    async def leaderboard_rps(
        self,
        interaction: discord.ApplicationContext,
    ):
        """View the Rock-Paper-Scissors leaderboard."""
        if not player_stats:
            await interaction.respond("No games have been played yet.")
            return

        # Sort stats by wins
        sorted_stats = sorted(player_stats.items(), key=lambda x: x[1]["wins"], reverse=True)
        embed = discord.Embed(title="Rock-Paper-Scissors Leaderboard", color=discord.Color.gold())
        for user_id, stats in sorted_stats:
            user = interaction.guild.get_member(int(user_id)) or f"User ({user_id})"
            embed.add_field(name=str(user), value=f"Wins: {stats['wins']} | Losses: {stats['losses']}", inline=False)

        await interaction.respond(embed=embed)

    # Admin command to clear the leaderboard
    @discord.slash_command(name="clear_leaderboard_rps", description="Clear the entire leaderboard. (Admin only)")
    @extra_help("Clear the entire Rock-Paper-Scissors leaderboard. This will remove all player stats. Usage: /clear_leaderboard_rps")
    @admin_required()
    async def clear_leaderboard_rps(
        self,
        interaction: discord.ApplicationContext,
    ):
        """Clear the entire Rock-Paper-Scissors leaderboard."""
        if not interaction.author.guild_permissions.administrator:
            await interaction.respond("You do not have permission to use this command.", ephemeral=True)
            return

        global player_stats
        player_stats.clear()
        self.save_db()
        await interaction.respond("The leaderboard has been cleared.")

    # Admin command to remove a specific player from the leaderboard
    @discord.slash_command(name="remove_player_rps", description="Remove a player from the leaderboard. (Admin only)", guild_ids=GUILD_IDS)
    @extra_help("Remove a specific player from the Rock-Paper-Scissors leaderboard. This will delete their stats. Usage: /remove_player_rps <player>")
    @admin_required()
    @option("player", description="The player to remove", type=discord.Member) # type: ignore
    async def remove_player_rps(
        self,
        interaction: discord.ApplicationContext, 
        player: discord.Member
        ):
        """Remove a specific player from the leaderboard."""
        if not interaction.author.guild_permissions.administrator:
            await interaction.respond("You do not have permission to use this command.", ephemeral=True)
            return

        if str(player.id) in player_stats:
            del player_stats[str(player.id)]
            self.save_db()
            await interaction.respond(f"Removed {player.display_name} from the leaderboard.")
        else:
            await interaction.respond(f"{player.display_name} is not on the leaderboard.")

    # Admin command to manually add or edit a player's stats
    @discord.slash_command(name="add_player_stats", description="Add or edit a player's leaderboard stats. (Admin only)", guild_ids=GUILD_IDS)
    @extra_help("Add or edit a player's stats on the Rock-Paper-Scissors leaderboard. This allows you to set wins and losses manually. Usage: /add_player_stats <player> <wins> <losses>")
    @option("player", description="The player to modify", type=discord.Member) # type: ignore
    @option("wins", description="Number of wins to set", type=int) # type: ignore
    @option("losses", description="Number of losses to set", type=int) # type: ignore
    async def add_player_stats(
        self,
        interaction: discord.ApplicationContext, 
        player: discord.Member, 
        wins: int, 
        losses: int
        ): 
        """Add or edit a player's leaderboard stats."""
        if not interaction.author.guild_permissions.administrator:
            await interaction.respond("You do not have permission to use this command.", ephemeral=True)
            return

        player_stats[str(player.id)] = {"wins": wins, "losses": losses}
        self.save_db()
        await interaction.respond(f"Set {player.display_name}'s stats to Wins: {wins}, Losses: {losses}.")
        




    


    ##load_leaderboard()
        
def setup(client):
    client.add_cog(FunCog(client))