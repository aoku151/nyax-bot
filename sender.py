import os
from typing import Tuple
import uuid
import logging
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient
import aioconsole
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
from func.log import stream_handler, get_log
from func.session import Sessions
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN_SUB")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="s!", intents=intents)

async def console_input():
    while True:
        line = await aioconsole.ainput("type:")
        if line.strip() == "finish":
            main_log.info("Stop.")
            await bot.close()
            break

currentUser = None
session = None

async def get_currentUser(supabase: AsyncClient):
    log = get_log("get_currentUser")
    try:
        log.debug(session.user)
        currentUser = (
            await supabase.table("user")
            .select("*")
            .eq("uuid", session.user.id)
            .execute()
        )
        log.debug(currentUser.data[0])
        return currentUser.data[0]
    except Exception as e:
        log.error("currentUserの取得中にエラーが発生しました。")

log_channel: discord.TextChannel = None

messages = []

supabase: AsyncClient = None

@tasks.loop(seconds=60)
async def send_nyax():
    global messages
    log = get_log("send_nyax")
    try:
        mes = ""
        for i in messages:
            mes = mes + i + "\n"
        if (mes != ""):
            await supabase.rpc("create_post", {"p_content": mes, "p_reply_id": None, "p_repost_to": None, "p_attachments": None}).execute()
    except Exception as e:
        log.error(f"NyaXの送信中にエラーが発生しました。\n{e}")

async def main():
    log = main_log
    global currentUser, session, messages, supabase
    try:
        supabase = await get_supabase()
        session = await supabase.auth.get_session()

        @bot.event
        async def on_ready():
            global log_channel
            log.info(f"Discord:{bot.user}としてログインしました^o^")
            try:
                synced = await bot.tree.sync()
                log.info(f"{len(synced)}個のコマンドを同期しました。")
                log_channel = bot.get_guild(1440680053867286560).get_channel(1440680171890933863)
            except Exception as e:
                log.error(f"コマンドの同期中にエラーが発生しました。\n{e}")
            send_nyax.start()
            asyncio.create_task(console_input())
            # await supabase.rpc("create_post", {"p_content": "NyaXBotが起動しました!", "p_reply_id": None, "p_repost_to": None, "p_attachments": None}).execute()
        @bot.event
        async def on_message(message:discord.Message):
            if message.channel == log_channel:
                messages.append(message.content)
            await bot.process_commands(message)

        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        log.error(f"BOTの起動中にエラーが発生しました\n{e}")

if __name__ == "__main__":
    discord.utils.setup_logging(handler=stream_handler)
    asyncio.run(main())
