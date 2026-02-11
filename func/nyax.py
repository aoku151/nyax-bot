from os import getenv
from dotenv import load_dotenv
from func.session import Sessions
import supabase as Supabase
from supabase import acreate_client, AsyncClient
from typing import Literal
from pydantic import BaseModel
from datetime import datetime, timezone
from func.log import get_log
from func.other import crlf
import uuid
load_dotenv()

class Setting_Data(BaseModel):
    show_like:bool
    show_follow:bool
    show_follower:bool
    show_star:bool
    show_scid:bool
    show_trust_label:bool
    default_timeline_tab:Literal["all", "foryou", "following"]
    emoji:Literal["twemoji", "emojione", "default"]
    theme:literal["auto", "light", "dark"]

class Notice:
    def __init__(self, nd:dict):
        self.id:str = nd["id"]
        self.open:str = nd["open"]
        self.click:bool = nd["click"]
        self.message:str = nd["message"]

class CurrentUser:
    def __init__(self, cd:dict):
        notices:list[Notice] = []
        for i in cd["notice"]:
            notices.append(Notice(i))
        self.id:int = cd["id"]
        self.uuid:str = cd["uuid"]
        self.scid:str = cd["scid"]
        self.name:str = cd["name"]
        self.me:str = cd["me"]
        self.icon_data:str = cd["icon_data"]
        self.settings:Setting_Data = cd["settings"]
        self.like:list[str] = cd["like"]
        self.star:list[str] = cd["star"]
        self.follow:list[int] = cd["follow"]
        self.admin:bool = cd["admin"]
        self.verify:bool = cd["verify"]
        self.freeze = cd["frieze"]
        self.notice:list[Notice] = notices
        self.notice_count:int = cd["notice_count"]
        self.time:str = cd["time"]
        self.dtime:datetime = datetime.fromisoformat(cd["time"])
        self.block:list[int] = cd["block"]
        self.pin:str = cd["pin"]
    

class NyaXClient:
    async def __init__(self, supabase_url:str, supabase_token:str, scid:str, scpass:str, session_path:str = "sessions.json"):
        """
        NyaX.py
        Args:
            supabase_url (str): SupabaseのURL
            supabase_token (str): SupabaseのANON_KEY
            scid (str): Scratchのユーザー名
            scpass (str): Scratchのパスワード
            session_path (:obj:`str`, optional): セッション管理ファイルの名称。必ず初期化時に{}を書き込んでおくこと。
        """
        self.sessions:Sessions = Sessions(session_path)
        supabase, session = await sessions.get_supabase()
        self.supabase:AsyncClient = supabase
        self.session = session
        self.currentUser = CurrentUser(await sessions.get_currentUser(supabase, session))

    async def sendNotification(self, recipientId:str, message:str, openHash:str=""):
        """
        ユーザーに通知を送信します。
        Args:
            recipientId (str): 送信先のユーザーID
            message (str): 送信するメッセージ
            openHash (:obj:`str`, optional): 通知を押したときにジャンプするHash
        """
        log = get_log("sendNotification")
        try:
            if(not self.currentUser or not recipientId or not message or recipientId == currentUser["id"]):
                return
            response = (
                await self.supabase.rpc("send_notification_with_timestamp", {
                    "recipient_id": recipientId,
                    "message_text": crlf(message),
                    "open_hash": openHash
                })
                .execute()
            )
        except Exception as e:
            log.error(f"通知の送信中にエラーが発生しました。\n{e}")
    async def send_dm_message(self, dmid:str,message:str):
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
                "userid": self.currentUser.id,
                "content": crlf(message),
                "attachments": [],
                "read": [self.currentUser.id]
            }
            await supabase.rpc("append_to_dm_post", {
                "dm_id_in": dmid,
                "new_message_in": messagedict
            }).execute()
        except Exception as e:
            log.error(f"DMのメッセージ送信中にエラーが発生しました。\n{e}")

    async def send_system_dm_message(self, dmid:str, message:str):
        """
        DMにシステムメッセージを送信します。
        Args:
            dmid (str): 送信するDMのID
            message (str): メッセージ
        """
        log = get_log("send_system_dm_message")
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
            mask (:obj:`bool`, optional): 添付ファイルのリスト。送信前に別処理が必要。
        Todo:
            * リポスト時の通知処理の移植
        """
        log = get_log("send_post")
        try:
            #ポストの送信
            newPost = (
                await self.supabase.rpc("create_post_new", {
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
                    await self.supabase.table("post")
                    .select("userid")
                    .eq("id", reply_id)
                    .single()
                    .execute()
                ).data
                log.debug(parentPost)
                if(parentPost and parentPost["userid"] != self.currentUser.id):
                    replied_user_id = parentPost["userid"]
                    await sendNotification(replied_user_id, f"@{self.currentUser.id}さんがあなたのポストに返信しました。", f"#post/{newPost['id']}")
            #メンションの通知送信
            mentioned_ids = set()
            for match in re.finditer(r"@(\d+)", content):
                mentioned_id = int(match.group(1))
                if(mentioned_id != self.currentUser.id and mentioned_id != replied_user_id):
                    mentioned_ids.add(mentioned_id)
            for id in mentioned_ids:
                await sendNotification(id, f"@{self.currentUser.id}さんがあなたをメンションしました。", f"#post/{newPost['id']}")
        except Exception as e:
            log.error(f"ポスト中にエラーが発生しました。\n{e}")
