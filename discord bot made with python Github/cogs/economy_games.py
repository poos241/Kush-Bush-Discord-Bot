import random
from sys import winver
from unittest import result
import discord
from discord.ext import commands
import time
from config import GUILD_IDS, load_json, save_json

ECONOMY_FILE = "economy.json"
STARTING_BALANCE = 500
DAILY_REWARD = 250
DAILY_COOLDOWN = 86400  # 24 hours

BANK_CAP = 50_000  # max coins allowed in bank
PAY_MIN = 100
SERVER_STARTING_BANK = 5_000_000


CARD_VALUES = {
    "A": 11,
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10
}

DECK = list(CARD_VALUES.keys()) * 4



class BlackjackView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=500) 
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return str(interaction.user.id) == self.user_id

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.cog.blackjack_hit(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.cog.blackjack_stand(interaction)

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.blurple)
    async def double(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.cog.blackjack_double(interaction)

    @discord.ui.button(label="Split", style=discord.ButtonStyle.red)
    async def split(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.cog.blackjack_split(interaction)

    async def on_timeout(self):
        game = self.cog.blackjack_games.get(self.user_id)
        if not game:
            return

        # User never acted → refund
        if game["actions_taken"] == 0:
            data, user = self.cog.get_account(self.user_id)
            refund = game["bet"]
            user["balance"] += refund
            self.cog.save_economy(data)

            game["result_text"] = (
                "⏱️ **Blackjack Timed Out**\n"
                "You did not take any actions.\n"
                f"💸 **${refund} was refunded to your wallet.**"
            )
            game["net_change"] = 0

        else:
            game["result_text"] = "⏱️ Game timed out. Auto-stand."
            game["net_change"] = 0

        embed = self.cog.render_blackjack(self.user_id, final=True)

        del self.cog.blackjack_games[self.user_id]

        try:
            if self.message:
                await self.message.edit(embed=embed, view=None)
        except Exception:
            pass




class economy_games(commands.Cog):
    def __init__(self, client):
        self.bot = client
        self.blackjack_games = {}
        self.baccarat_shoe = []
        self.baccarat_history = []
        winner = None
        self.baccarat_history.append(winner)
        if len(self.baccarat_history) > 20:
            self.baccarat_history.pop(0)
            
   
        
    # ------------------------------
    # Helper: Get or create user
    # ------------------------------
    
    
    def is_admin(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    
    
    def get_server_bank(self, data):
        if "_server" not in data:
            data["_server"] = {"bank": SERVER_STARTING_BANK}
            self.save_economy(data)
        return data["_server"]
    
    
    def server_collect(self, data, amount: int):
        server = self.get_server_bank(data)
        server["bank"] += amount
        self.save_economy(data)

    
    def server_payout(self, data, amount: int) -> bool:
        server = self.get_server_bank(data)

        if server["bank"] < amount:
            return False  # house bankrupt safeguard

        server["bank"] -= amount
        self.save_economy(data)
        return True

    
    def build_baccarat_shoe(self, decks=8):
        shoe = []
        for _ in range(decks):
            for card in range(1, 14):
                value = 0 if card >= 10 else card
                shoe.extend([value] * 4)
        random.shuffle(shoe)
        return shoe
    
    
    def draw_baccarat_card(self):
        if len(self.baccarat_shoe) < 6:
            self.baccarat_shoe = self.build_baccarat_shoe()

        return self.baccarat_shoe.pop()

    def baccarat_player_draws(self, total):
        return total <= 5

    def baccarat_banker_draws(self, banker_total, player_third):
        if player_third is None:
            return banker_total <= 5

        rules = {
            0: True,
            1: True,
            2: True,
            3: player_third != 8,
            4: 2 <= player_third <= 7,
            5: 4 <= player_third <= 7,
            6: 6 <= player_third <= 7,
            7: False
        }

        return rules.get(banker_total, False)

    async def blackjack_hit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        game = self.blackjack_games.get(user_id)

        if not game or game.get("finished"):
            return

        game["actions_taken"] += 1
        hand = game["hands"][game["current"]]
        hand.append(self.draw_card())

        if self.hand_value(hand) > 21:
            await self.next_hand_or_dealer(interaction)
        else:
            await interaction.response.edit_message(
                embed=self.render_blackjack(user_id),
                view=BlackjackView(self, user_id)
            )
    
    async def blackjack_stand(self, interaction: discord.Interaction):
        await self.next_hand_or_dealer(interaction)

    async def blackjack_double(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        game = self.blackjack_games.get(user_id)

        if not game or game["actions_taken"] > 0:
            await interaction.response.send_message(
                "❗ You can only double down on your first action.",
                ephemeral=True
            )
            return

        data, user = self.get_account(user_id)

        if user["balance"] < game["bet"]:
            await interaction.response.send_message(
                "❗ Not enough balance to double down.",
                ephemeral=True
            )
            return

        user["balance"] -= game["bet"]
        game["bet"] *= 2
        game["actions_taken"] += 1

        hand = game["hands"][game["current"]]
        hand.append(self.draw_card())

        self.save_economy(data)
        await self.next_hand_or_dealer(interaction)


    async def blackjack_split(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        game = self.blackjack_games.get(user_id)
        hand = game["hands"][game["current"]]

        if len(hand) != 2 or hand[0] != hand[1]:
            await interaction.response.send_message(
                "❗ You can only split identical cards.",
                ephemeral=True
            )
            return

        data, user = self.get_account(user_id)

        if user["balance"] < game["bet"]:
            await interaction.response.send_message(
                "❗ Not enough balance to split.",
                ephemeral=True
            )
            return

        user["balance"] -= game["bet"]
        game["hands"] = [
            [hand[0], self.draw_card()],
            [hand[1], self.draw_card()]
        ]
        game["current"] = 0
        game["actions_taken"] = 0

        self.save_economy(data)

        await interaction.response.edit_message(
            embed=self.render_blackjack(user_id),
            view=BlackjackView(self, user_id)
        )


    async def next_hand_or_dealer(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        game = self.blackjack_games[user_id]

        game["current"] += 1

        if game["current"] < len(game["hands"]):
            game["actions_taken"] = 0
            await interaction.response.edit_message(
                embed=self.render_blackjack(user_id),
                view=BlackjackView(self, user_id)
            )
            return

        dealer = game["dealer"]
        while self.hand_value(dealer) < 17:
            dealer.append(self.draw_card())

        dealer_value = self.hand_value(dealer)

        data, user = self.get_account(user_id)
        net = 0
        results = []

        for hand in game["hands"]:
            value = self.hand_value(hand)

            if value > 21:
                results.append("❌ Player Busts")
                net -= game["bet"]
            elif dealer_value > 21 or value > dealer_value:
                win = int(game["bet"] * 2)
                net += win
                results.append(f"✅ Player Wins (+${win})")
            elif value == dealer_value:
                net += game["bet"]
                results.append("➖ Push (Bet Returned)")
            else:
                results.append("❌ Banker Wins")

        user["balance"] += max(net, 0)
        self.save_economy(data)

        game["finished"] = True
        game["result_text"] = "\n".join(results)
        game["net_change"] = net

        await interaction.response.edit_message(
            embed=self.render_blackjack(user_id, final=True),
            view=None
        )

        del self.blackjack_games[user_id]

    def draw_baccarat_card(self):
        card = random.randint(1, 13)
        if card >= 10:
            return 0  # 10, J, Q, K
        return card

    def baccarat_total(self, hand):
        return sum(hand) % 10

    
    def load_economy(self):
        try:
            return load_json(ECONOMY_FILE)
        except FileNotFoundError:
            save_json(ECONOMY_FILE, {})
            return {}

    def save_economy(self, data):
        save_json(ECONOMY_FILE, data)

    def get_account(self, user_id: str):
        data = self.load_economy()

        # Create account if missing
        if user_id not in data:
            data[user_id] = {
                "balance": STARTING_BALANCE,
                "bank": 0,
                "deaths": 0,
                "last_daily": 0
            }
            self.save_economy(data)
            return data, data[user_id]

        user = data[user_id]

        # 🔥 MIGRATION SAFETY (adds missing keys)
        if "balance" not in user:
            user["balance"] = STARTING_BALANCE
        if "bank" not in user:
            user["bank"] = 0
        if "deaths" not in user:
            user["deaths"] = 0
        if "last_daily" not in user:
            user["last_daily"] = 0

        self.save_economy(data)
        return data, user


    def add_money(self, user_id: str, amount: int):
        data, user = self.get_account(user_id)
        user["balance"] += amount
        self.save_economy(data)

    def remove_money(self, user_id: str, amount: int) -> bool:
        data, user = self.get_account(user_id)

        if user["balance"] < amount:
            return False

        user["balance"] -= amount
        self.save_economy(data)
        return True



    def deposit_money(self, user_id: str, amount: int) -> bool:
        data, user = self.get_account(user_id)

        if amount <= 0:
            return False

        if user["balance"] < amount:
            return False

        if user["bank"] + amount > BANK_CAP:
            return False

        user["balance"] -= amount
        user["bank"] += amount
        self.save_economy(data)
        return True

    def withdraw_money(self, user_id: str, amount: int) -> bool:
        data, user = self.get_account(user_id)

        if amount <= 0:
            return False

        if user["bank"] < amount:
            return False

        user["bank"] -= amount
        user["balance"] += amount
        self.save_economy(data)
        return True




    def get_server_net_worth(self) -> int:
        data = self.load_economy()
        total = 0

        for user in data.values():
            total += user.get("balance", 0)
            total += user.get("bank", 0)

        return total



    def render_blackjack(self, user_id, final=False):
        game = self.blackjack_games.get(user_id)

        embed = discord.Embed(
            title="🃏 Blackjack",
            color=discord.Color.dark_green()
        )

        # Safety check (prevents crashes)
        if not game:
            embed.description = "❗ This blackjack game no longer exists."
            return embed

        # Player hands
        for i, hand in enumerate(game["hands"]):
            value = self.hand_value(hand)
            prefix = "➡️ " if i == game["current"] and not final else ""

            embed.add_field(
                name=f"{prefix}Hand {i + 1}",
                value=f"{', '.join(hand)} (Value: {value})",
                inline=False
            )

        # Dealer hand
        dealer_hand = game["dealer"]
        if final:
            dealer_value = self.hand_value(dealer_hand)
            dealer_text = f"{', '.join(dealer_hand)} (Value: {dealer_value})"
        else:
            dealer_text = f"{dealer_hand[0]}, ❓" if dealer_hand else "❓"

        embed.add_field(
            name="Dealer",
            value=dealer_text,
            inline=False
        )

        # Final result section
        if final:
            embed.add_field(
                name="📊 Result",
                value=game.get("result_text", "No result."),
                inline=False
            )

            change = game.get("net_change", 0)

            if change > 0:
                change_text = f"+${change}"
            elif change < 0:
                change_text = f"-${abs(change)}"
            else:
                change_text = "➖ Push ($0)"

            embed.add_field(
                name="💰 Net Change",
                value=change_text,
                inline=False
            )

        return embed


    



    def draw_card(self):
        return random.choice(DECK)


    def hand_value(self, hand):
        value = sum(CARD_VALUES[c] for c in hand)
        aces = hand.count("A")

        while value > 21 and aces:
            value -= 10
            aces -= 1

        return value


    def is_blackjack(self, hand):
        return len(hand) == 2 and self.hand_value(hand) == 21




    @discord.slash_command(
        name="admin_bank",
        description="View the server bank",
        guild_ids=GUILD_IDS
    )
    async def admin_bank(self, interaction: discord.ApplicationContext):
        if not self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ Admins only.",
                ephemeral=True
            )
            return

        data = self.load_economy()
        server = self.get_server_bank(data)

        await interaction.response.send_message(
            f"🏦 **Server Bank Balance:** ${server['bank']:,}"
        )




    @discord.slash_command(
    name="admin_bank_add",
    description="Add money to the server bank",
    guild_ids=GUILD_IDS
    )
    async def admin_bank_add(
        self,
        interaction: discord.ApplicationContext,
        amount: int
    ):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❗ Amount must be positive.", ephemeral=True)
            return

        data = self.load_economy()
        server = self.get_server_bank(data)

        server["bank"] += amount
        self.save_economy(data)

        await interaction.response.send_message(
            f"✅ Added ${amount:,} to the server bank.\n"
            f"🏦 New Balance: ${server['bank']:,}"
        )




    @discord.slash_command(
        name="admin_bank_remove",
        description="Remove money from the server bank",
        guild_ids=GUILD_IDS
    )
    async def admin_bank_remove(
        self,
        interaction: discord.ApplicationContext,
        amount: int
    ):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return

        data = self.load_economy()
        server = self.get_server_bank(data)

        if amount <= 0 or amount > server["bank"]:
            await interaction.response.send_message("❗ Invalid amount.", ephemeral=True)
            return

        server["bank"] -= amount
        self.save_economy(data)

        await interaction.response.send_message(
            f"✅ Removed ${amount:,} from the server bank.\n"
            f"🏦 New Balance: ${server['bank']:,}"
        )




    @discord.slash_command(
        name="admin_bank_reset",
        description="Reset the server bank to starting value",
        guild_ids=GUILD_IDS
    )
    async def admin_bank_reset(self, interaction: discord.ApplicationContext):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return

        data = self.load_economy()
        data["_server"] = {"bank": SERVER_STARTING_BANK}
        self.save_economy(data)

        await interaction.response.send_message(
            f"🔄 Server bank reset to ${SERVER_STARTING_BANK:,}"
        )



    @discord.slash_command(
        name="daily",
        description="Claim your daily coins",
        guild_ids=GUILD_IDS
    )
    async def daily(self, interaction: discord.ApplicationContext):
        user_id = str(interaction.user.id)
        now = int(time.time())

        data, user = self.get_account(user_id)

        last = user["last_daily"]
        remaining = DAILY_COOLDOWN - (now - last)

        if remaining > 0:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60

            await interaction.response.send_message(
                f"⏳ You already claimed your daily.\n"
                f"Come back in **{hours}h {minutes}m**.",
                ephemeral=True
            )
            return

        user["last_daily"] = now
        user["balance"] += DAILY_REWARD
        self.save_economy(data)

        embed = discord.Embed(
            title="📅 Daily Reward",
            description=f"You received **{DAILY_REWARD} coins**!",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"New Balance: {user['balance']} coins")

        await interaction.response.send_message(embed=embed)




    # ------------------------------
    # Death Dice Command
    # ------------------------------

    @discord.slash_command(
        name="deathdice",
        description="Roll the death dice for a chance to double your money",
        guild_ids=GUILD_IDS
    )
    async def deathdice(
        self,
        interaction: discord.ApplicationContext,
        bet: int,
        bet1: int
    ):
        user_id = str(interaction.user.id)

        if bet <= 0:
            await interaction.response.send_message(
                "❗ You must bet more than 0 coins.",
                ephemeral=True
            )
            return

        data, user = self.get_account(user_id)

        if user["balance"] < bet:
            await interaction.response.send_message(
                "❗ You don’t have enough coins.",
                ephemeral=True
            )
            return

        roll = random.randint(1, 6)

        # LOSS
        if roll == 6:
            user["balance"] -= bet
            self.server_collect(data, bet)

            extra = ""
            if roll == 6:
                user["deaths"] += 1
                extra = "\n💀 **Instant Death!** Your death count increased."

            result = (
                f"🎲 You rolled a **{roll}**\n"
                f"💸 You lost **{bet} coins**.{extra}"
            )

        # WIN
        else:
            winnings = bet1 * 1
            user["balance"] += bet1
            self.server_collect(data, bet1)
            result = (
                f"🎲 You rolled a **{roll}**\n"
                f"🎉 You won **{winnings} coins!**"
            )
        ##self.save_economy(data)

        embed = discord.Embed(
            title="☠️ Death Dice",
            description=result,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Balance: {user['balance']} coins")

        await interaction.response.send_message(embed=embed)

    

    @discord.slash_command(
    name="blackjack",
    description="Play interactive blackjack",
    guild_ids=GUILD_IDS
    )
    async def blackjack(self, interaction: discord.ApplicationContext, bet: int):
        user_id = str(interaction.user.id)
        data, user = self.get_account(user_id)

        if user_id in self.blackjack_games:
            await interaction.response.send_message(
                "❗ You already have an active blackjack game.",
                ephemeral=True
            )
            return

        if bet <= 0 or user["balance"] < bet:
            await interaction.response.send_message(
                "❗ Invalid bet.",
                ephemeral=True
            )
            return

        user["balance"] -= bet
        self.server_collect(data, bet)
        ##self.save_economy(data)

        await interaction.response.defer()

        player_hand = [self.draw_card(), self.draw_card()]
        dealer_hand = [self.draw_card(), self.draw_card()]

        self.blackjack_games[user_id] = {
            "bet": bet,
            "hands": [player_hand],
            "current": 0,
            "dealer": dealer_hand,
            "actions_taken": 0,
            "finished": False,
            "result_text": "",
            "net_change": 0,
            "started_at": time.time()
        }

        embed = self.render_blackjack(user_id)
        view = BlackjackView(self, user_id)

        message = await interaction.followup.send(
            embed=embed,
            view=view,
            wait=True
        )

        view.message = message




    @discord.slash_command(
        name="baccarat",
        description="Play a game of Baccarat",
        guild_ids=GUILD_IDS
    )
    async def baccarat(
        self,
        interaction: discord.ApplicationContext,
        bet: int,
        choice: discord.Option(
            str,
            choices=["player", "banker", "tie"]
        ) # type: ignore
    ):
        user_id = str(interaction.user.id)
        data, user = self.get_account(user_id)

        if bet <= 0:
            await interaction.response.send_message("❗ Bet must be greater than 0.", ephemeral=True)
            return

        if user["balance"] < bet:
            await interaction.response.send_message("❗ You don’t have enough money.", ephemeral=True)
            return

        # Take bet
        user["balance"] -= bet
        self.server_collect(data, bet)


        # Deal cards
        player_hand = [self.draw_baccarat_card(), self.draw_baccarat_card()]
        banker_hand = [self.draw_baccarat_card(), self.draw_baccarat_card()]

        player_total = self.baccarat_total(player_hand)
        banker_total = self.baccarat_total(banker_hand)

        player_third = None

        # Determine winner
        if player_total > banker_total:
            winner = "player"
        elif banker_total > player_total:
            winner = "banker"
        else:
            winner = "tie"

        # Compare user choice to winner
        
        # Default values (IMPORTANT)
        payout = 0
        net_change = -bet  # assume loss by default

        # Player wins
        if choice == winner:
            if winner == "player":
                payout = bet * 2
            elif winner == "banker":
                payout = int(bet * 1.95)
            elif winner == "tie":
                payout = bet * 9

            # Pay from server bank
            if not self.server_payout(data, payout):
                await interaction.response.send_message(
                    "❗ The house cannot cover this bet.",
                    ephemeral=True
                )
                return

            user["balance"] += payout
            net_change = payout - bet

        # Embed result
        embed = discord.Embed(
            title="🎴 Baccarat",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="Player Hand",
            value=f"{player_hand} → **{player_total}**",
            inline=True
        )

        embed.add_field(
            name="Banker Hand",
            value=f"{banker_hand} → **{banker_total}**",
            inline=True
        )

        embed.add_field(
            name="Result",
            value=f"🏆 **{winner.capitalize()} wins**",
            inline=False
        )

        if net_change > 0:
            embed.add_field(
                name="💰 Winnings",
                value=f"+${net_change}",
                inline=False
            )
        elif net_change == 0:
            embed.add_field(
                name="➖ Push",
                value="Your bet was returned.",
                inline=False
            )
        else:
            embed.add_field(
                name="💸 Loss",
                value=f"-${bet}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    


    # ------------------------------
    # Balance Command
    # ------------------------------
    @discord.slash_command(
        name="balance",
        description="Check your wallet, bank, and server economy",
        guild_ids=GUILD_IDS
    )
    async def balance(self, interaction: discord.ApplicationContext):
        user_id = str(interaction.user.id)
        data, user = self.get_account(user_id)
        server = self.get_server_bank(data)

        embed = discord.Embed(
            title="💰 Economy Overview",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="👛 Wallet",
            value=f"${user['balance']}",
            inline=True
        )

        embed.add_field(
            name="🏦 Bank",
            value=f"${user['bank']}",
            inline=True
        )

        embed.add_field(
            name="🌐 Server Bank",
            value=f"${server['bank']}",
            inline=False
        )

        total_net = user["balance"] + user["bank"] + server["bank"]

        embed.add_field(
            name="📊 Total Server Net Worth",
            value=f"${total_net}",
            inline=False
        )

        await interaction.response.send_message(embed=embed)
        
        
        
    @discord.slash_command(
        name="bank",
        description="View your bank details and server economy",
        guild_ids=GUILD_IDS
    )
    async def bank(self, interaction: discord.ApplicationContext):
        user_id = str(interaction.user.id)
        _, user = self.get_account(user_id)

        user_net = user["balance"] + user["bank"]
        server_net = self.get_server_net_worth()

        embed = discord.Embed(
            title="🏦 Bank Overview",
            color=discord.Color.blue()
        )

        embed.add_field(name="Your Wallet", value=f"{user['balance']} coins", inline=True)
        embed.add_field(name="Your Bank", value=f"{user['bank']} coins", inline=True)
        embed.add_field(name="Your Net Worth", value=f"{user_net} coins", inline=False)

        embed.add_field(
            name="🌍 Server Total Net Worth",
            value=f"{server_net} coins",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


    @discord.slash_command(
    name="deposit",
    description="Deposit money into your bank",
    guild_ids=GUILD_IDS
    )
    async def deposit(
        self,
        interaction: discord.ApplicationContext,
        amount: str
    ):
        user_id = str(interaction.user.id)
        data, user = self.get_account(user_id)

        if amount.lower() == "all":
            amount = min(user["balance"], BANK_CAP - user["bank"])
        else:
            if not amount.isdigit():
                await interaction.response.send_message("❗ Invalid amount.", ephemeral=True)
                return
            amount = int(amount)

        if amount <= 0:
            await interaction.response.send_message("❗ Nothing to deposit.", ephemeral=True)
            return

        success = self.deposit_money(user_id, amount)

        if not success:
            await interaction.response.send_message(
                "❗ Deposit failed (insufficient funds or bank full).",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🏦 Deposited **{amount} coins**.\n"
            f"Wallet: {user['balance']} | Bank: {user['bank']}"
        )




    @discord.slash_command(
    name="withdraw",
    description="Withdraw money from your bank",
    guild_ids=GUILD_IDS
    )
    async def withdraw(
        self,
        interaction: discord.ApplicationContext,
        amount: str
    ):
        user_id = str(interaction.user.id)
        data, user = self.get_account(user_id)

        if amount.lower() == "all":
            amount = user["bank"]
        else:
            if not amount.isdigit():
                await interaction.response.send_message("❗ Invalid amount.", ephemeral=True)
                return
            amount = int(amount)

        if amount <= 0:
            await interaction.response.send_message("❗ Nothing to withdraw.", ephemeral=True)
            return

        success = self.withdraw_money(user_id, amount)

        if not success:
            await interaction.response.send_message(
                "❗ Withdrawal failed (insufficient bank balance).",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🏧 Withdrew **{amount} coins**.\n"
            f"Wallet: {user['balance']} | Bank: {user['bank']}"
        )


    @discord.slash_command(
        name="pay",
        description="Send money to another user",
        guild_ids=GUILD_IDS
    )
    async def pay(
        self,
        interaction: discord.ApplicationContext,
        member: discord.Member,
        amount: int
    ):
        sender_id = str(interaction.user.id)
        receiver_id = str(member.id)

        if amount < PAY_MIN:
            await interaction.response.send_message(
                f"❗ Minimum transfer is {PAY_MIN} coins.",
                ephemeral=True
            )
            return


        if sender_id == receiver_id:
            await interaction.response.send_message(
                "❗ You can’t pay yourself.",
                ephemeral=True
            )
            return

        data, sender = self.get_account(sender_id)
        _, receiver = self.get_account(receiver_id)

        if sender["balance"] < amount:
            await interaction.response.send_message(
                "❗ You don’t have enough money in your wallet.",
                ephemeral=True
            )
            return

        sender["balance"] -= amount
        receiver["balance"] += amount
        self.save_economy(data)

        await interaction.response.send_message(
            f"💸 **{interaction.user.mention} paid {member.mention} {amount} coins**"
        )





def setup(client):
    client.add_cog(economy_games(client))