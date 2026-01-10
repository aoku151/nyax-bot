import discord
from discord.ext import commands
from discord import app_commands

class MyBot(commands.Bot):
    def __init__(self, **options):
        super().__init__(**options)
        self.supabase = None
        self.supabase_session = None
