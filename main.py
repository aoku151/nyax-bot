# 設定系
from os import getenv
from dotenv import load_dotenv
load_dotenv()
from func.data import dmInviteMessage, helpMessage, header
# Discord系
import discord
from discord.ext import commands, tasks
from discord import app_commands
from func.discord import MyBot
# 非同期系
import asyncio
# Scratch系
import scapi
# HTTPリクエスト系
import aiohttp
import json
# コンソール系
import logging
from func.log import get_log, stream_handler
import aioconsole
import signal
# Supabase系
from supabase import acreate_client, AsyncClient
from func.session import Sessions
import supabase as Supabase
# ファイル操作系
import aioboto3
from func.r2 import upload_fileobj
from func.miq import create_quote_image
import io
from os import listdir
from PIL import Image, ImageDraw, ImageFont
# 汎用系
from typing import Tuple
import uuid
import re
from datetime import datetime, timezone
from func.other import crlf

# トークンとか
DISCORD_TOKEN: str = getenv("DISCORD_TOKEN")
SUPABASE_URL: str = getenv("SUPABASE_URL")
SUPABASE_ANON_KEY: str = getenv("SUPABASE_ANON_KEY")
defaultDmId: str = getenv("DEFAULT_DM_ID")
sessions_path = "sessions.json"
sessions = Sessions(sessions_path)

# Discord Botの設定
intents = discord.Intents.all()
bot = MyBot(command_prefix="!", intents=intents)

main_log = get_log("Main")

shutdown_event = asyncio.Event()

Can_Stop = [
    6999,
    5355,
    2872,
    7549,
    2525
]

def handle_sigterm():
    shutdown_event.set()

# Raspberry Pi Connectで^Cが使えないため
async def console_input():
    while True:
        line = await aioconsole.ainput("type:")
        if line.strip() == "finish":
            await bot_stop()
            break

# NyaXBotを停止する関数(扱い注意)
async def bot_stop():
    main_log.info("Stop.")
    await status_update("停止中")
    await bot.close()

# グローバル変数
supabase: AsyncClient = None
currentUser = None
session = None
log_channel: discord.TextChannel = None
console_task = None

async def sendNotification(recipientId:str, message:str, openHash:str=""):
    """
    ユーザーに通知を送信します。
    Args:
        recipientId (str): 送信先のユーザーID
        message (str): 送信するメッセージ
        openHash (:obj:`str`, optional): 通知を押したときにジャンプするHash
    """
    log = get_log("sendNotification")
    try:
        if(not currentUser or not recipientId or not message or recipientId == currentUser["id"]):
            return
        response = (
            await supabase.rpc("send_notification_with_timestamp", {
                "recipient_id": recipientId,
                "message_text": crlf(message),
                "open_hash": openHash
            })
            .execute()
        )
    except Exception as e:
        log.error(f"通知の送信中にエラーが発生しました。\n{e}")

async def send_dm_message(dmid:str,message:str):
    """
    DMにメッセージを送信します。
    Args:
        dmid (str): 送信するDMのID
        message (str): メッセージ
    """
    log = get_log("send_dm_message")
    try:
        messagedict = {
            "id": str(uuid.uuid4()),
            "time": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "userid": currentUser["id"],
            "content": crlf(message),
            "attachments": [],
            "read": [currentUser["id"]]
        }
        await supabase.rpc("append_to_dm_post", {
            "dm_id_in": dmid,
            "new_message_in": messagedict
        }).execute()
    except Exception as e:
        log.error(f"DMのメッセージ送信中にエラーが発生しました。\n{e}")

async def send_system_dm_message(dmid:str, message:str):
    log = get_log("send_dm_message")
    try:
        messagedict = {
            "id": str(uuid.uuid4()),
            "time": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "type": "system",
            "content": crlf(message)
        }
        await supabase.rpc("append_to_dm_post", {
            "dm_id_in": dmid,
            "new_message_in": messagedict
        }).execute()
    except Exception as e:
        log.error(f"DMのシステムメッセージ送信中にエラーが発生しました。")

async def send_post(content:str = None, reply_id:str = None, repost_id:str = None, attachments:list = None, mask:bool = False):
    """
    ポストをします。
    Args:
        content (:obj:`str`, optional): ポストの内容。リポストの場合には指定しない。
        reply_id (:obj:`str`, optional): 返信するポストのID。返信の場合にのみ指定し、リポストと混合させない。
        repost_id (:obj:`str`, optional): リポストするポストのID。この場合には他の引数はつけない。
        attachments (:obj:`list`, optional): 添付ファイルのリスト。送信前に別処理が必要。
    Todo:
        * リポスト時の通知処理の移植
    """
    log = get_log("send_post")
    try:
        #ポストの送信
        newPost = (
            await supabase.rpc("create_post_new", {
                "p_content": crlf(content),
                "p_reply_id": reply_id,
                "p_repost_to": repost_id,
                "p_attachments": attachments,
                "p_mask": mask
            })
            .single()
            .execute()
        ).data
        #返信時の通知送信
        replied_user_id = None
        if(reply_id):
            parentPost = (
                await supabase.table("post")
                .select("userid")
                .eq("id", reply_id)
                .single()
                .execute()
            ).data
            log.debug(parentPost)
            if(parentPost and parentPost["userid"] != currentUser["id"]):
                replied_user_id = parentPost["userid"]
                await sendNotification(replied_user_id, f"@{currentUser['id']}さんがあなたのポストに返信しました。", f"#post/{newPost['id']}")
        #メンションの通知送信
        mentioned_ids = set()
        for match in re.finditer(r"@(\d+)", content):
            mentioned_id = int(match.group(1))
            if(mentioned_id != currentUser["id"] and mentioned_id != replied_user_id):
                mentioned_ids.add(mentioned_id)
        for id in mentioned_ids:
            await sendNotification(id, f"@{currentUser['id']}さんがあなたをメンションしました。", f"#post/{newPost['id']}")
    except Exception as e:
        log.error(f"ポスト中にエラーが発生しました。\n{e}")

async def get_hydrated_posts(ids:list, profile:bool = False) -> list[dict]:
    """
    ポストの詳細をまとめて取得します。
    Args:
        ids (list): 取得するポストIDのリスト
    Returns:
        list: 中身はポストの詳細
    """
    log = get_log("get_hydrated_posts")
    try:
        async with aiohttp.ClientSession() as a_session:
            async with a_session.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_hydrated_posts",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                    "Content-Type": "application/json",
                    "Content-Profile": "public"
                },
                data=json.dumps(
                    {
                        "p_post_ids": ids,
                        "p_profile": profile
                    },
                    separators=(',', ":")
                )
            ) as post:
                data = await post.json()
        if("error" in data):
            raise Exception(data["error"])
        return data
    except Exception as e:
        log.error(f"ポストの情報取得中にエラーが発生しました。\n{e}")

async def like(postId: str):
    """
    ポストにいいねします。
    Args:
        postId (str): PostID
    """
    log = get_log("like")
    try:
        await supabase.rpc("handle_like", {"p_post_id": postId}).execute()
    except Exception as e:
        log.error(f"いいね中にエラーが発生しました。\n{e}")

@tasks.loop(seconds=30)
async def subscribe_dm():
    """
    DMのメッセージを確認します。
    通常はDiscord.pyのdiscord.ext.tasksで実行します。
    """
    log = get_log("subscribe_dm")
    try:
        response = await supabase.rpc("get_all_unread_dm_counts", {"p_user_id": currentUser["id"]}).execute()
        if(response.data):
            unread_data = {}
            for i in response.data:
                unread_data[i["dm_id"]] = i["unread_count"]
            dmfilterdIds = list(unread_data.keys())
            response2 = (
                await supabase.table("dm")
                .select("id, title, post, member, host_id")
                .in_("id", dmfilterdIds)
                .execute()
            )

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

@tasks.loop(seconds=5)
async def handle_notification():
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

notifications_id = []
async def handle_notification_message(notification):
    """
    通知を処理します。
    Args:
        notification (dict): 通知の内容
    """
    global notifications_id
    log = get_log("handle_notification_message")
    try:
        if(notification["id"] in notifications_id):
            return
        if("あなたをDMに招待しました" in notification["message"]):
            dmid = notification["open"][4:]
            await send_dm_message(dmid, dmInviteMessage)
        elif("あなたをメンションしました" in notification["message"]):
            postid = notification["open"][6:]
            log.debug(postid)
            message = (
                await supabase.table("post")
                .select("content, repost_to")
                .eq("id", postid)
                .execute()
            ).data[0]
            isDebug = False
            for i in Can_Stop:
                if f"@{i}さん" in notification["message"]:
                    isDebug = True
            if(isDebug):
                if("/finish" in message["content"]):
                    await like(postid)
                    await supabase.rpc('mark_all_notifications_as_read', {"p_user_id":currentUser["id"]}).execute()
                    await bot_stop()
                if("/debug_user" in message["content"]):
                    mainPost = (await get_hydrated_posts([postid]))[0]
                    rep = mainPost["reply_to_post"]
                    if(rep):
                        print(rep["author"])
            if("/miq" in message["content"]):
                log.debug("MIQ")
                mainPost = (await get_hydrated_posts([postid]))[0]
                log.debug(mainPost)
                rep = mainPost["reply_to_post"]
                if(rep):
                    color = "!c" in message["content"]
                    fileid = await create_miq(rep, color)
                    if(not fileid):
                        return
                    amdata = [{
                        "type":"image",
                        "id":fileid,
                        "name": f"{rep['id']}.jpg"
                    }]
                    await send_post(content = "Make it a Quote画像を生成しました！", reply_id = postid, attachments = amdata)
                else:
                    await send_post(content = "返信を使用してください。", reply_id = postid)
            if("おはよう" in message["content"]):
                await send_post(content=f"おはようございます! {re.search(r'@[0-9]{4}', notification['message'])[0]} さん!", reply_id = postid)
            if("/invite_dm" in message["content"]):
                userid = re.search(r"[0-9]+", re.search(r"@[0-9]+さん", notification["message"])[0])[0]
                log.debug(userid)
                dm = (
                    await supabase.table('dm')
                    .select("member")
                    .eq("id", defaultDmId)
                    .execute()
                ).data[0]
                if(userid in dm["member"]):
                    return
                dm_update_res = (
                    await supabase.table("dm")
                    .update({"member": (dm["member"] + [userid])})
                    .eq("id", defaultDmId)
                    .execute()
                ).data[0]
                if("error" in dm_update_res):
                    raise Exception(dm_update_res["error"])
                await like(postid)
                await send_system_dm_message(defaultDmId, f"@{userid}さんをNyaXBotDMに招待しました。")
                # await mes_channel.send(embed=discord.Embed(
                #     title="SystemMessage",
                #     description=f"NyaXにてID:{userid}がDMに入室しました。", #あとで名前はどうにかする
                #     color=0x00ff00
                # ))
                await sendNotification(userid, f"@{currentUser['id']}さんがあなたをDMに招待しました。", f"#dm/{defaultDmId}")
    except Exception as e:
        log.error(f"通知のメッセージ処理中にエラーが発生しました\n{e}")
    finally:
        notifications_id.append(notification["id"])

async def getUserIconUrl(user):
    if(user["icon_data"]):
        icon_url = (
            await supabase.storage
            .from_("nyax")
            .get_public_url(user["icon_data"])
        )
    else:
        icon_url = f"{SUPABASE_URL}/functions/v1/getScratchUserIcon?id={user['scid']}"
    return icon_url

async def create_miq(mes:dict, color:bool) -> str:
    """
    Make it a Quoteを作成し、SupabaseのStorageにUploadします
    Args:
        mes (dict): ポストの詳細
        color (bool): モノクロかカラーか(True: カラー, False: モノクロ)
    Returns:
        str: SupabaseのFileID
    """
    log = get_log("create_miq")
    try:
        width, height = 800, 400
        log.info(f"MIQを作成中...(w:{width}, h:{height})")
        log.info(f"{mes['author']['name']}のアイコンを取得中...")

        avatar_url_res = await getUserIconUrl(mes["author"])
        log.debug(avatar_url_res)
        miq_header = {
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }
        async with aiohttp.ClientSession() as a_session:
            async with a_session.get(avatar_url_res) as resp:
                if(resp.status == 200):
                    icon_data = await resp.read()
                    # log.debug(icon_data)
                    icon = io.BytesIO(icon_data)
                else:
                    raise Exception(await resp.json())
        # log.debug(icon)
        log.info("アイコン取得完了")
        log.info("MIQ画像を作成中...")
        if(mes["content"].startswith("!")):
            miq_quote = mes["content"][1:]
        else:
            miq_quote = mes["content"]
        img = await asyncio.to_thread(create_quote_image, width, height, icon, miq_quote, f"{mes['author']['name']}@{mes['author']['id']}", color)
        if(not img):
            return
        log.info("MIQ画像作成完了")
        log.info("アップロード中...")
        async with aiohttp.ClientSession() as a_session:
            data = aiohttp.FormData()
            data.add_field("file", img, filename=f"{mes['id']}.jpg", content_type="image/jpeg")

            async with a_session.post(f"{SUPABASE_URL.replace('.supabase.co', '.functions.supabase.co')}/upload-file", headers=miq_header, data=data) as resp:
                result = await resp.json()
        res_data = result["data"] if "data" in result else result
        if("error" in res_data):
            raise Exception(f"ファイルアップロードエラー:{res_data['error']}")
        fileid = res_data["fileId"]
        log.info(f"FileID:{fileid}で作成。")
        return fileid
    except Exception as e:
        log.error(f"Miqの作成時にエラーが発生しました。\n{e}")

async def handle_dm_message(msg:dict, dmid:str):
    """
    DMのメッセージを処理します。
    Args:
        msg (dict): DMのメッセージの詳細
        dmid (str): 応答があったDMのID
    """
    match msg["content"]:
        case "/hello":
            await send_dm_message(dmid, "こんにちは!NyaXBotです!")
        case "/help":
            await send_dm_message(dmid, helpMessage)

async def status_update(status):
    """
    ステータスを変更します。
    Args:
        status (str): ステータス名
    """
    log = get_log("status_update")
    try:
        message = f"""NyaXBot
管理者:あおく
https://github.com/aoku151/nyax-bot/

ステータス:{status}"""
        # log.debug(repr(crlf(message)))
        # log.debug(crlf(message))
        updatedData = {
            "name": "非公式NyaXBot",
            "me": crlf(f"NyaXBot  ステータス:{status}"),
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
    """
    Botメイン機構
    """
    log = main_log
    global currentUser, supabase, session
    try:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
        loop.add_signal_handler(signal.SIGINT, handle_sigterm)
        # Supabaseのログイン
        supabase, session = await sessions.get_supabase()
        # session = await supabase.auth.get_session()
        currentUser = await sessions.get_currentUser(supabase, session)
        # log.debug(currentUser)
        bot.supabase = supabase
        bot.supabase_session = session

        @bot.event
        async def on_ready():
            global log_channel, console_task, s3, s3_session
            console_task = asyncio.create_task(console_input())
            log.info(f"Discord:{bot.user}としてログインしました^o^")
            log_channel = bot.get_guild(1440680053867286560).get_channel(1440680171890933863)
            try:
                #await handle_notification()
                subscribe_dm.start()
                handle_notification.start()
                await status_update("起動中")
                # await nyax_feed.subscribe()
            except Exception as e:
                log.error(f"初期動作の実行中にエラーが発生しました。\n{e}")
            # await send_post(content="NyaXBotが起動しました!")
            await log_channel.send("NyaXBotが起動しました!")

        @bot.event
        async def setup_hook():
            try:
                for cog in listdir("cogs"):
                    if cog.endswith(".py"):
                        await bot.load_extension(f"cogs.{cog[:-3]}")
                synced = await bot.tree.sync()
                log.info(f"{len(synced)}個のコマンドを同期しました。")
            except Exception as e:
                log.error(f"コマンドの同期中にエラーが発生しました。"

        # nyax_feed.on_postgres_changes(
        #     event="UPDATE",
        #     schema="public",
        #     table="user",
        #     filter=f"id=eq.{currentUser['id']}",
        #     callback=lambda payload: asyncio.create_task(handle_notification(payload))
        # )

        bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
        await shutdown_event.wait()
        log.info("SIGTERM reived. Shutting down...")
        await bot_stop()
        await bot_task
    except Exception as e:
        log.error(f"BOTの起動中にエラーが発生しました\n{e}")

if __name__ == "__main__":
    discord.utils.setup_logging(handler=stream_handler)
    asyncio.run(main())
