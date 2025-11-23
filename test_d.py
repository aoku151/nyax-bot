import discord
from discord.ext import commands
from os import getenv
import asyncio
import aioconsole
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

async def console_input():
    while True:
        line = await aioconsole.ainput("type:")
        if line.strip() == "finish":
            await bot.close()
            break

async def main():
    @bot.event
    async def on_ready():
        for i in bot.guilds :
            print(i.name)
            print(i.id)
            for a in i.channels :
                print(a.name)
                print(a.id)
    await bot.start(getenv("DISCORD_TOKEN"))

discord.utils.setup_logging()
if __name__ == "__main__":
    asyncio.run(main())
