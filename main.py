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
load_dotenv()

sp_url: str = os.getenv("SUPABASE_URL")
sp_key: str = os.getenv("SUPABASE_ANON_KEY")
sc_name: str = os.getenv("SCRATCH_USER")
sc_pass: str = os.getenv("SCRATCH_PASSWORD")
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")
nx_auth_url = "https://mnvdpvsivqqbzbtjtpws.supabase.co/functions/v1/scratch-auth-handler"
sessions_path = "sessions.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

main_log = logging.getLogger("Main")
main_log.setLevel(level=logging.DEBUG)
def get_log(name:str):
    log = logging.getLogger(name)
    log.setLevel(level=logging.DEBUG)
    return log
stream_handler = logging.StreamHandler()

def getSession(key):
    with open(sessions_path, "r") as f:
        data = json.load(f)
        return data[key]
def setSession(key, value):
    with open(sessions_path, "r") as f:
        data = json.load(f)
    data[key] = value
    with open(sessions_path, "w") as f:
        json.dump(data, f, indent=4)

async def get_supabase():
    log = get_log("get_supabase")
    try:
        supabase: AsyncClient = await acreate_client(sp_url, sp_key)
        sp_jwt = getSession("sp_key")
        sp_res = await supabase.auth.set_session(sp_jwt, sp_jwt)
        log.info("セッションは有効です。認証に成功しました!")
        session = sp_res.session
        return supabase, session
    except Exception:
        try:
            log.warning("セッションの有効期限が切れているので、新しいセッションを作成します...")
            supabase: AsyncClient = await acreate_client(sp_url, sp_key)
            sc:scapi.Session = await get_scratch()
            header = {"Content-Type": "application/json"}
            first = {"type": "generateCode", "username": sc_name}
            log.info("ログインコードを取得しています...")
            async with aiohttp.ClientSession() as session:
                async with session.post(nx_auth_url, json=first, headers=header) as res:
                    response = await res.json()
            log.info(f"ログインコードを取得しました!{response['code']}")
            await sc.user.post_comment(f"{response['code']}")
            second = {"type": "verifyComment", "username": sc_name, "code": response['code']}
            log.info("セッションを取得しています...")
            async with aiohttp.ClientSession() as session:
                async with session.post(nx_auth_url, json=second, headers=header) as res:
                    response = await res.json()
            log.info("セッションを取得しました!")
            sp_res = await supabase.auth.set_session(response['jwt'], response['jwt'])
            setSession("sp_key", response['jwt'])
            log.info("セッションは有効です。認証に成功しました!")
            await sc.client_close()
            session = sp_res.session
            return supabase, session
        except Exception as e:
            log.error(f"NyaXのログイン中にエラーが発生しました。\n{e}")
async def get_scratch():
    log = get_log("get_scratch")
    try:
        log.info("Scratchにログインしています...")
        sc_key = getSession("sc_key")
        session:scapi.Session = await scapi.session_login(sc_key)
        log.info(f"Scratchにログインしました!:{session.username}")
        return session
    except Exception:
        try:
            log.warning("セッションが無効です。再ログインしています...")
            session:scapi.Session = await scapi.login(sc_name, sc_pass)
            setSession("sc_key", session.session_id)
            log.info(f"Scratchにログインしました!:{session.username}")
            return session
        except Exception as e:
            log.error(f"エラー:Scratchのログインに失敗しました\n{e}")

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

async def main():
    log = main_log
    global currentUser, session
    try:
        supabase, session = await get_supabase()
        # session = await supabase.auth.get_session()
        currentUser = await get_currentUser(supabase)
        log.debug(currentUser)

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
            asyncio.create_task(console_input())
            await supabase.rpc("create_post", {"p_content": "NyaXBotが起動しました!", "p_reply_id": None, "p_repost_to": None, "p_attachments": None}).execute()

        async def handle_notification():
            global currentUser
            try:
                session = await supabase.auth.get_session()
                response = (
                    await supabase.table("user")
                    .select("notice")
                    .eq("id", currentUser["id"])
                    .execute()
                )
                notices = response.notice
                for n_obj in notices:
                    notification = None
                    if(type(n_obj) is dict):
                        notification = n_obj
                    else:
                        notification = {"id": uuid.uuid4(), "message": n_obj, "open": "", "click": True}
                    if(!notification.click):
                        await log_channel.send(notification.message)
                await supabase.rpc('mark_all_notifications_as_read', {"p_user_id":currentUser["id"]})
                if(currentUser.notice):
                    for i in currentUser.notice:
                        i["click"] = True
                currentUser["notice_count"] = 0
            except Exception as e:
                log.error(f"通知の取得にエラーが発生しました。{e}")

        subscribe1 = (
            await supabase.channel("nyax-feed")
            .on_postgres_changes("UPDATE", schema="public", table="user", filter=f"id=eq.{currentUser['id']}", callback=handle_notification)
            .subscribe()
        )
        
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        log.error(f"BOTの起動中にエラーが発生しました\n{e}")

if __name__ == "__main__":
    discord.utils.setup_logging(handler=stream_handler)
    asyncio.run(main())
