import discord
from discord.ext import commands
from discord import app_commands

class MyBot(commands.Bot):
    def __init__(self, supabase, supabase_session, **options):
        super().__init__(**options)
        self.supabase = supabase
        self.supabase_session = supabase_session
        
