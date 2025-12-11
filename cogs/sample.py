import discord
from discord.ext import commands
from discord import app_commands
from func.log import get_log

class NameCog(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.log = get_log(self.__class__.__name__)
		self.supabase = bot.supabase
		self.session = bot.supabase_session
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info(f"{self.__class__.__name__}が読み込まれました！")
	
async def setup(bot):
    await bot.add_cog(NameCog(bot))
