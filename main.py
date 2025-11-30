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
from datetime import datetime, timezone
from discord.ext import commands, tasks
from discord import app_commands
from func.session import Sessions
from func.log import get_log, stream_handler
from func.data import dmInviteMessage, helpMessage
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
            await status_update("停止中")
            await bot.close()
            break

supabase: AsyncClient = None
currentUser = None
session = None

log_channel: discord.TextChannel = None

console_task = None

async def send_dm_message(dmid:str,message:str):
    log = get_log("send_dm_message")
    try:
        messagedict = {
            "id": str(uuid.uuid4()),
            "time": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "userid": currentUser["id"],
            "content": message,
            "attachments": [],
            "read": [currentUser["id"]]
        }
        await supabase.rpc("append_to_dm_post", {"dm_id_in": dmid, "new_message_in": messagedict}).execute()
    except Exception as e:
        log.error(f"DMのメッセージ送信中にエラーが発生しました。\n{e}")

@tasks.loop(seconds=15)
async def subscribe_dm():
    log = get_log("subscribe_dm")
    try:
        response = (
            await supabase.table("dm")
            .select("id, title, member, time")
            .contains("member", [str(currentUser["id"])])
            .order("time", desc=True)
            .execute()
        )
        dmids = []
        for i in response.data:
            dmids.append(i["id"])
        response2 = (
            await supabase.table("dm")
            .select("id, title, post, member, host_id")
            .in_("id", dmids)
            .execute()
        )
        response3 = await supabase.rpc("get_all_unread_dm_counts", {"p_user_id": currentUser["id"]}).execute()
        #log.debug(response3)
        if(response3.data):
            unread_data = {}
            for i in response3.data:
                unread_data[i["dm_id"]] = i["unread_count"]
            log.debug(unread_data)
            for i in response2.data:
                #log.debug(i)
                if(i["id"] not in unread_data):
                    continue
                ranges = unread_data[i["id"]] * -1
                for a in i["post"][ranges:]:
                    log.debug(a)
                    if("type" not in a):
                        log.debug("suc")
                        await handle_dm_message(a, i["id"])
                await supabase.rpc("mark_all_dm_messages_as_read", {"p_dm_id": i["id"], "p_user_id": currentUser["id"]}).execute()
    except Exception as e:
        log.error(f"DMの処理中にエラーが発生しました。\n{e}")

async def handle_notification_message(notification):
    log = get_log("handle_notification_message")
    try:
        if("あなたをDMに招待しました" in notification["message"]):
            dmid = notification["open"][4:]
            await send_dm_message(dmid, dmInviteMessage)
        elif("あなたをメンションしました" in notification["message"]):
            postid = notification["open"][6:]
            if("@4332さん" in notification["message"]):
            #     response = (
            #         await supabase.rpc("handle_like", {
            #             "p_post_id": postid
            #         })
            #         .execute()
            #     )
                response = (
                    await supabase.table("post")
                    .select("content, repost_to")
                    .eq("id", postid)
                    .execute()
                )
                if("/finish" in response.data[0]["content"]):
                    await supabase.rpc("handle_like", {"p_post_id": postid}).execute()
                    #console_task.cancel()
                    #await bot.close()
    except Exception as e:
        log.error(f"通知のメッセージ処理中にエラーが発生しました\n{e}")

async def handle_dm_message(msg,dmid):
    match msg["content"]:
        case "/hello":
            await send_dm_message(dmid, "こんにちは!NyaXBotです!")
        case "/help":
            await send_dm_message(dmid, helpMessage)

async def status_update(status):
    log = get_log("status_update")
    try:
        message = f"""NyaXBot
管理者:あおく
https://github.com/aoku151/nyax-bot/

ステータス:{status}"""
        updatedData = {
            "name": "非公式NyaXBot",
            "me": message,
            "settings": {
                "show_like": False,
                "show_follow": True,
                "show_follower": True,
                "show_star": False,
                "show_scid": False,
                "default_timeline_tab": "all",
                "emoji": "emojione",
                "theme": "light"
            },
            "icon_data": currentUser["icon_data"]
        }
        response = (
            await supabase.table("user")
            .update(updatedData)
            .eq("id", currentUser["id"])
            .execute()
        )
        return response
    except Exception as e:
        log.error(f"プロフィールの更新中にエラーが発生しました。\n{e}")

async def main():
    log = main_log
    global currentUser, supabase, session, console_task
    try:
        supabase, session = await sessions.get_supabase()
        # session = await supabase.auth.get_session()
        currentUser = await sessions.get_currentUser(supabase, session)
        # log.debug(currentUser)

        @bot.event
        async def on_ready():
            global log_channel, console_task
            console_task = asyncio.create_task(console_input())
            log.info(f"Discord:{bot.user}としてログインしました^o^")
            try:
                synced = await bot.tree.sync()
                log.info(f"{len(synced)}個のコマンドを同期しました。")
                log_channel = bot.get_guild(1440680053867286560).get_channel(1440680171890933863)
            except Exception as e:
                log.error(f"コマンドの同期中にエラーが発生しました。\n{e}")
            try:
                await handle_notification()
                subscribe_dm.start()
                await status_update("起動中")
            except Exception as e:
                log.error(f"初期動作の実行中にエラーが発生しました。\n{e}")
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
                result = response.data[0]
                # log.debug(result)
                notices = result["notice"]
                noti_count = 0
                for n_obj in notices:
                    notification = None
                    if(type(n_obj) is dict):
                        notification = n_obj
                    else:
                        notification = {"id": uuid.uuid4(), "message": n_obj, "open": "", "click": True}
                    if(notification["click"] is not True):
                        log.debug(notification)
                        log.debug(notification["message"])
                        # await log_channel.send(notification["message"])
                        await handle_notification_message(notification)
                        noti_count += 1
                if(noti_count != 0):
                    await supabase.rpc('mark_all_notifications_as_read', {"p_user_id":currentUser["id"]}).execute()
                if(currentUser["notice"]):
                    for i in currentUser["notice"]:
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
