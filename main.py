import os
from typing import Tuple
import uuid
import logging
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient
import supabase as Supabase
import scapi
import asyncio
import aiohttp
import aioconsole
import json
import discord
from discord.ext import commands
from discord import app_commands
from func.session import Sessions
from func.log import get_log, stream_handler
load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")
sessions_path = "sessions.json"
sessions = Sessions(sessions_path)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

main_log = get_log("Main")

async def console_input():
    while True:
        line = await aioconsole.ainput("type:")
        if line.strip() == "finish":
            main_log.info("Stop.")
            await bot.close()
            break

currentUser = None
session = None

log_channel: discord.TextChannel = None

async def main():
    log = main_log
    global currentUser, session
    try:
        supabase, session = await sessions.get_supabase()
        # session = await supabase.auth.get_session()
        currentUser = await sessions.get_currentUser()
        # log.debug(currentUser)

        @bot.event
        async def on_ready():
            global log_channel
            log.info(f"Discord:{bot.user}としてログインしました^o^")
            try:
                synced = await bot.tree.sync()
                log.info(f"{len(synced)}個のコマンドを同期しました。")
                log_channel = bot.get_guild(1440680053867286560).get_channel(1440680171890933863)
                await handle_notification()
            except Exception as e:
                log.error(f"コマンドの同期中にエラーが発生しました。\n{e}")
            asyncio.create_task(console_input())
            # await supabase.rpc("create_post", {"p_content": "NyaXBotが起動しました!", "p_reply_id": None, "p_repost_to": None, "p_attachments": None}).execute()
            await log_channel.send("NyaXBotが起動しました!")

        nyax_feed = supabase.channel("nyax-feed")

        async def handle_notification(payload = None):
            global currentUser
            log = get_log("handle_notification")
            try:
                session = await supabase.auth.get_session()
                response = (
                    await supabase.table("user")
                    .select("notice")
                    .eq("id", currentUser["id"])
                    .execute()
                )
                log.debug(response)
                notices = response.notice
                for n_obj in notices:
                    notification = None
                    if(type(n_obj) is dict):
                        notification = n_obj
                    else:
                        notification = {"id": uuid.uuid4(), "message": n_obj, "open": "", "click": True}
                    if(notification.click is not True):
                        log.debug(nofication.message)
                        await log_channel.send(notification.message)
                await supabase.rpc('mark_all_notifications_as_read', {"p_user_id":currentUser["id"]})
                if(currentUser.notice):
                    for i in currentUser.notice:
                        i["click"] = True
                currentUser["notice_count"] = 0
            except Exception as e:
                log.error(f"通知の取得にエラーが発生しました。\n{e}")

        nyax_feed.on_postgres_changes(
            event="UPDATE",
            schema="public",
            table="user",
            filter=f"id=eq.{currentUser['id']}",
            callback=lambda payload: asyncio.create_task(handle_notification(payload))
        )
        await nyax_feed.subscribe()

        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        log.error(f"BOTの起動中にエラーが発生しました\n{e}")

if __name__ == "__main__":
    discord.utils.setup_logging(handler=stream_handler)
    asyncio.run(main())
