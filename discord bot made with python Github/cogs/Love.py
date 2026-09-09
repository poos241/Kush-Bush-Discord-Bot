import discord
from discord.ext import commands
import aiohttp

class HugBackButton(discord.ui.Button):
    def __init__(self, sender, receiver):
        super().__init__(label="🤗 Hug Back", style=discord.ButtonStyle.primary)
        self.sender = sender
        self.receiver = receiver

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.receiver:
            await interaction.response.send_message("Only the hugged person can hug back!", ephemeral=True)
            return
        gif_url = await fetch_hug_gif()
        embed = discord.Embed(
            title="Aww!",
            description=f"{self.receiver.mention} hugged back {self.sender.mention} 💞",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)
        self.view.disable_all_items()
        await interaction.message.edit(view=self.view)

class KissBackButton(discord.ui.Button):
    def __init__(self, sender, receiver):
        super().__init__(label="💋 Kiss Back", style=discord.ButtonStyle.primary)
        self.sender = sender
        self.receiver = receiver

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.receiver:
            await interaction.response.send_message("Only the kissed person can kiss back!", ephemeral=True)
            return
        gif_url = await fetch_kiss_gif()
        embed = discord.Embed(
            title="Romantic!",
            description=f"{self.receiver.mention} kissed back {self.sender.mention} 💞",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)
        self.view.disable_all_items()
        await interaction.message.edit(view=self.view)

class CuddleBackButton(discord.ui.Button):
    def __init__(self, sender, receiver):
        super().__init__(label="🤗 Cuddle Back", style=discord.ButtonStyle.primary)
        self.sender = sender
        self.receiver = receiver

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.receiver:
            await interaction.response.send_message("Only the cuddled person can cuddle back!", ephemeral=True)
            return
        gif_url = await fetch_cuddle_gif()
        embed = discord.Embed(
            title="So Cozy!",
            description=f"{self.receiver.mention} cuddled back {self.sender.mention} 💞",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)
        self.view.disable_all_items()
        await interaction.message.edit(view=self.view)

class HandholdBackButton(discord.ui.Button):
    def __init__(self, sender, receiver):
        super().__init__(label="🤝 Hold Hands Back", style=discord.ButtonStyle.primary)
        self.sender = sender
        self.receiver = receiver

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.receiver:
            await interaction.response.send_message("Only the person who received the handhold can hold back!", ephemeral=True)
            return
        gif_url = await fetch_handhold_gif()
        embed = discord.Embed(
            title="How sweet!",
            description=f"{self.receiver.mention} is holding hands back with {self.sender.mention} ❤️",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)
        self.view.disable_all_items()
        await interaction.message.edit(view=self.view)

async def fetch_hug_gif():
    url = "https://nekos.best/api/v2/hug"
    fallback = "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return fallback
            data = await resp.json()
            return data["results"][0]["url"]

async def fetch_kiss_gif():
    url = "https://nekos.best/api/v2/kiss"
    fallback = "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return fallback
            data = await resp.json()
            return data["results"][0]["url"]

async def fetch_cuddle_gif():
    url = "https://nekos.best/api/v2/cuddle"
    fallback = "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return fallback
            data = await resp.json()
            return data["results"][0]["url"]

async def fetch_handhold_gif():
    url = "https://nekos.best/api/v2/handhold"
    fallback = "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return fallback
            data = await resp.json()
            return data["results"][0]["url"]

class LoveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="hug", description="Give a warm hug to someone special! 🤗")
    async def hug(self, ctx, user: discord.User):
        if user == ctx.author:
            await ctx.send("You can't hug yourself... but here's a virtual hug 🤗")
            return

        gif_url = await fetch_hug_gif()
        embed = discord.Embed(
            title="So Sweet!",
            description=f"{ctx.author.mention} gave a warm hug to {user.mention} ❤️",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)
        view = discord.ui.View(timeout=60)
        view.add_item(HugBackButton(sender=ctx.author, receiver=user))
        view.add_item(HandholdBackButton(sender=ctx.author, receiver=user))
        view.add_item(CuddleBackButton(sender=ctx.author, receiver=user)) 
        view.add_item(KissBackButton(sender=ctx.author, receiver=user))
        await ctx.send(embed=embed, view=view)



    @discord.slash_command(name="kiss", description="Give a warm hug to someone special! 🤗")
    async def Kiss(self, ctx, user: discord.User):
        if user == ctx.author:
            await ctx.send("You can't Kiss yourself... but here's a virtual Kiss 🤗")
            return

        gif_url = await fetch_kiss_gif()
        embed = discord.Embed(
            title="So sweet!",
            description=f"{ctx.author.mention} gave a warm long kiss to {user.mention} ❤️",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)
        view = discord.ui.View(timeout=60)
        view.add_item(KissBackButton(sender=ctx.author, receiver=user))
        view.add_item(HugBackButton(sender=ctx.author, receiver=user))
        view.add_item(HandholdBackButton(sender=ctx.author, receiver=user))
        view.add_item(CuddleBackButton(sender=ctx.author, receiver=user)) 
        await ctx.send(embed=embed, view=view)




    @discord.slash_command(name="cuddle", description="Give a warm hug to someone special! 🤗")
    async def cuddle(self, ctx, user: discord.User):
        if user == ctx.author:
            await ctx.send("You can't cuddle yourself... but here's some virtual cuddle 🤗")
            return

        gif_url = await fetch_cuddle_gif()
        embed = discord.Embed(
            title="So sweet!",
            description=f"{ctx.author.mention} gave lots of cuddles to {user.mention} ❤️",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)
        view = discord.ui.View(timeout=60)
        view.add_item(HugBackButton(sender=ctx.author, receiver=user))
        view.add_item(HandholdBackButton(sender=ctx.author, receiver=user))
        view.add_item(CuddleBackButton(sender=ctx.author, receiver=user)) 
        view.add_item(KissBackButton(sender=ctx.author, receiver=user))
        await ctx.send(embed=embed, view=view)


    @discord.slash_command(name="handhold", description="Give a warm handhold to someone special! 🤝")
    async def handhold(self, ctx, user: discord.User):
        if user == ctx.author:
            await ctx.send("You can't hold your own hand... but here's a virtual squeeze 🤝")
            return

        gif_url = await fetch_handhold_gif()
        embed = discord.Embed(
            title="So sweet!",
            description=f"{ctx.author.mention} is holding hands with {user.mention} ❤️",
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif_url)

        view = discord.ui.View(timeout=60)
        view.add_item(HugBackButton(sender=ctx.author, receiver=user))
        view.add_item(HandholdBackButton(sender=ctx.author, receiver=user))
        view.add_item(CuddleBackButton(sender=ctx.author, receiver=user)) 
        view.add_item(KissBackButton(sender=ctx.author, receiver=user)) 
        view.add_item(HandholdBackButton(sender=ctx.author, receiver=user))
        
        await ctx.send(embed=embed, view=view)



def setup(bot):
    bot.add_cog(LoveCog(bot))