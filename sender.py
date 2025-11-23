import os
from typing import Tuple
import uuid
import logging
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient
import scapi
import asyncio
import aiohttp
import aioconsole
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
load_dotenv()

sp_url: str = os.getenv("SUPABASE_URL")
sp_key: str = os.getenv("SUPABASE_ANON_KEY")
sc_name: str = os.getenv("SCRATCH_USER")
sc_pass: str = os.getenv("SCRATCH_PASSWORD")
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN_SUB")
nx_auth_url = "https://mnvdpvsivqqbzbtjtpws.supabase.co/functions/v1/scratch-auth-handler"
sessions_path = "sessions.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="s!", intents=intents)

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

async def get_supabase() -> AsyncClient:
    log = get_log("get_supabase")
    try:
        supabase: AsyncClient = await acreate_client(sp_url, sp_key)
        sp_jwt = getSession("sp_key")
        await supabase.auth.set_session(sp_jwt, sp_jwt)
        log.info("セッションは有効です。認証に成功しました!")
        return supabase
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
            await supabase.auth.set_session(response['jwt'], response['jwt'])
            setSession("sp_key", response['jwt'])
            log.info("セッションは有効です。認証に成功しました!")
            await sc.client_close()
            return supabase
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

messages = []

@tasks.loop(seconds=60)
async def send_nyax():
    global messages
    log = get_log("send_nyax")
    try:
        mes = ""
        for i in messages:
            

async def main():
    log = main_log
    global currentUser, session, messages
    try:
        supabase: AsyncClient = await get_supabase()
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
