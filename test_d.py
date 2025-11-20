import discord
from discord.ext import commands
from os import getenv
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)
@bot.event
async def on_ready():
    for i in bot.guilds :
        print(i.id)
        for a in i.channels :
            print(a.name)
            print(a.id)

bot.run(getenv("DISCORD_TOKEN"))
