from os import getenv
from dotenv import load_dotenv
from func.session import Sessions
import supabase as Supabase
from supabase import acreate_client, AsyncClient
from typing import Literal, Any, Union, get_origin, get_args
from pydantic import BaseModel
from datetime import datetime, timezone
from func.log import get_log
from func.other import crlf
from enum import Enum, auto
import uuid
import aiohttp
import json
import regex as re
load_dotenv()

class FileUploadException(Exception):
    pass

class Setting_Data:
    def __init__(self, sd:dict):
        self.show_like:bool = sd["show_like"]
        self.show_follow:bool = sd["show_follow"]
        self.show_follower:bool = sd["show_follower"]
        self.show_star:bool = sd["show_star"]
        self.show_scid:bool = sd["show_scid"]
        self.show_trust_label:bool = sd["show_trust_label"]
        self.default_timeline_tab:Literal["all", "foryou", "following"] = sd["show_trust_label"]
        self.emoji:Literal["twemoji", "emojione", "default"] = sd["emoji"]
        self.theme:Literal["auto", "light", "dark"] = sd["theme"]
    def get_dict(self):
        return vars(self)
    def change(self, key:str, value:Union[str,bool]):
        annotations = self.__class__.__annotations__
        if key not in annotations:
            raise AttributeError(f"Attribute '{key}' does not exist")
        expected = annotations[key]
        if not self._check_type(value, expected):
            raise TypeError(
                f"{key} must be {expected}, got {type(value).__name__}: {value}"
            )
        setattr(self, key, value)
    def _check_type(self, value, expected_type):
        origin = get_origin(expected_type)

        if origin is Literal:
            return value in get_args(expected_type)
        if origin is Union:
            return any(self._check_type(value, t) for t in get_args(expected_type))
        return isinstance(value, expected_type)

class NOTICETYPE(Enum):
    MENTION = auto()
    REPOST = auto()
    REPLY = auto()
    QUOTE = auto()
    
    INVITE_DM = auto()
    DELETE_DM = auto()
    ADMIN_DM = auto()
    
    NYAXTEAM = auto()

    OTHER = auto()

class Notice:
    def __init__(self, nd:dict):
        self.id:str = nd["id"]
        self.open:str = nd["open"]
        self.click:bool = nd["click"]
        self.message:str = nd["message"]
        self.type:NOTICETYPE = NOTICETYPE.OTHER
        if "あなたのポストをリポストしました。" in nd["message"]:
            self.type = NOTICETYPE.REPOST
        elif "あなたのポストに返信しました。" in nd["message"]:
            self.type = NOTICETYPE.REPLY
        elif "あなたのポストを引用しました。" in nd["message"]:
            self.type = NOTICETYPE.QUOTE
        elif "あなたをメンションしました。" in nd["message"]:
            self.type = NOTICETYPE.MENTION
        elif "あなたのポストをリポストしました。" in nd["message"]:
            self.type = NOTICETYPE.DELETE_DM
        elif "さんから管理者権限を受け取りました。" in nd["message"]:
            self.type = NOTICETYPE.ADMIN_DM
        elif "さんがあなたをDMに招待しました。" in nd["message"]:
            self.type = NOTICETYPE.INVITE_DM
        elif "NyaXTeam" in nd["message"]:
            self.type = NOTICETYPE.NYAXTEAM

class User:
    def __init__(self, client:NyaXClient, cd:dict):
        self.nc:NyaXClient = client
        self.supabase: AsyncClient = client.supabase
        notices:list[Notice] = []
        if "notice" in cd:
            for i in cd["notice"]:
                notices.append(Notice(i))
        self.id:int = cd["id"] if "id" in cd else None
        self.uuid:str = cd["uuid"] if "uuid" in cd else None
        self.scid:str = cd["scid"] if "scid" in cd else None
        self.name:str = cd["name"] if "name" in cd else None
        self.me:str = cd["me"] if "me" in cd else None
        self.icon_data:str = cd["icon_data"] if "icon_data" in cd else None
        self.settings:Setting_Data = Setting_Data(cd["settings"]) if "settings" in cd else None
        self.like:list[str] = cd["like"] if "like" in cd else None
        self.star:list[str] = cd["star"] if "star" in cd else None
        self.follow:list[int] = cd["follow"] if "follow" in cd else None
        self.admin:bool = cd["admin"] if "admin" in cd else None
        self.verify:bool = cd["verify"] if "verify" in cd else None
        self.freeze = cd["frieze"] if "frieze" in cd else None
        self.notice:list[Notice] = notices
        self.notice_count:int = cd["notice_count"] if "notice_count" in cd else None
        self.time:str = cd["time"] if "time" in cd else None
        self.dtime:datetime = datetime.fromisoformat(cd["time"]) if "time" in cd else None
        self.block:list[int] = cd["block"] if "block" in cd else None
        self.pin:str = cd["pin"] if "pin" in cd else None
    async def all_load(self):
        user_req = (
            self.nc.supabase.table("user")
            .select("*")
        )
        if self.id != None:
            req = (
                await user_req
                .eq("id", self.id)
                .single()
                .execute()
            ).data
            self.__init__(self.nc, req)
        elif self.uuid != None:
            req = (
                await user_req
                .eq("uuid", self.uuid)
                .single()
                .execute()
            ).data
            self.__init__(self.nc, req)
    #async def get_followers(self, limit:int = 30, offset:int = 0):


class CurrentUser(User):
    async def change_name(self, new_name:str):
        updateData:dict[str, Any] = {
            "name": new_name,
            "me": crlf(self.me),
            "settings": self.settings.get_dict(),
            "icon_data": self.icon_data
        }
        response = (
            await self.supabase.table("user")
            .update(updateData)
            .eq("id", self.id)
            .execute()
        ).data
        self.name = new_name
        return response

    async def change_me(self, new_me:str):
        updateData:dict[str, Any] = {
            "name": self.name,
            "me": crlf(new_me),
            "settings": self.settings.get_dict(),
            "icon_data": self.icon_data
        }
        response = (
            await self.supabase.table("user")
            .update(updateData)
            .eq("id", self.id)
            .execute()
        ).data
        self.me = new_me
        return response
    async def change_setting(self, key:str, new_value:Union[str,bool]):
        self.settings.change(key, new_value)
        updateData:dict[str, Any] = {
            "name": self.name,
            "me": crlf(self.me),
            "settings": self.settings.get_dict(),
            "icon_data": self.icon_data
        }
        response = (
            await self.supabase.table("user")
            .update(updateData)
            .eq("id", self.id)
            .execute()
        ).data
        return response

class Attachment:
    def __init__(self, ad:dict):
        self.id = ad["id"]
        self.name = ad["id"]
        self.type = ad["type"]

class Post:
    def __init__(self, client:NyaXClient, pd:dict):
        self.nc:NyaXClient = client
        self.supabase: AsyncClient = client.supabase
        attachments:list[Attachment] = []
        for i in pd["attachments"]:
            attachments.append(Attachment(i))
        self.id:str = pd["id"]
        self.userid:int = pd["userid"]
        self.content:str = pd["content"]
        self.attachments:list = attachments
        self.reply_id:str = pd["reply_id"]
        self.time:str = pd["time"]
        self.dtime:datetime = datetime.fromisoformat(pd["time"])
        self.repost_to:Post = Post(pd["repost_to"]) if pd["repost_to"] else None
        self.mask:bool = pd["mask"]
        self.author:dict = pd["author"]
        self.reply_to_post = pd["reply_to_post"]
        self.reposted_post:Post = Post(pd["reposted_post"])

    async def reply(self, content:str = None, attachments:list = None, mask:bool = False):
        await self.nc.send_post(
            content = content,
            reply_id = self.id,
            attachments = attachments,
            mask = mask
        )
    async def repost(self):
        await self.nc.send_post(
            repost_id = self.id
        )

    async def like(self):
        await self.supabase.rpc("handle_like", {"p_post_id": self.id}).execute()

    async def star(self):
        await self.supabase.rpc("handle_star", {"p_post_id": self.id}).execute()

class DM:
    def __init__(self, nc:NyaXClient, dd:dict):
        self.nc:NyaXClient = nc
        self.id:str = dd["id"] if "id" in dd else None
        self.title:str = dd["title"] if "title" in dd else None
        self.member:list[int] = dd["member"] if "member" in dd else None
        self.time:str = dd["time"] if "time" in dd else None
        posts:list[DM_Post] = []
        if "post" in dd:
            for pd in dd["post"]:
                posts.append(DM_Post(pd))
        self.post:list[DM_Post] = posts
        self.host_id:int = dd["host_id"] if "host_id" in dd else None

    async def send_dm_message(self, message:str):
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
                "read": [self.nc.currentUser.id]
            }
            await self.nc.supabase.rpc("append_to_dm_post", {
                "dm_id_in": self.id,
                "new_message_in": messagedict
            }).execute()
        except Exception as e:
            log.error(f"DMのメッセージ送信中にエラーが発生しました。\n{e}")

    async def send_system_dm_message(self, message:str):
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
            await self.nc.supabase.rpc("append_to_dm_post", {
                "dm_id_in": self.id,
                "new_message_in": messagedict
            }).execute()
        except Exception as e:
            log.error(f"DMのシステムメッセージ送信中にエラーが発生しました。")

class DM_Post:
    def __init__(self, dd:dict) -> None:
        attachments:list[Attachment] = []
        if "attachments" in dd:
            for ad in dd["attachments"]:
                attachments.append(Attachment(ad))
        self.attachments:list[Attachment] = attachments
        self.content:str = dd["content"] if "content" in dd else None
        self.id:str = dd["id"] if "id" in dd else None
        self.read:list[int] = dd["read"] if "read" in dd else None
        self.time:str = dd["time"] if "time" in dd else None
        self.dtime:datetime = datetime.fromisoformat(dd["time"])
        self.userid:int = dd["userid"] if "userid" in dd else None

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
        self.supabase_url:str = supabase_url
        self.supabase_token:str = supabase_token
        self.sessions:Sessions = Sessions(session_path)
        supabase, session = await self.sessions.get_supabase()
        self.supabase:AsyncClient = supabase
        self.session = session
        self.currentUser = CurrentUser(self, await self.sessions.get_currentUser(supabase, session))

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
            if(not self.currentUser or not recipientId or not message or recipientId == self.currentUser.id):
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

    async def send_post(self, content:str = None, reply_id:str = None, repost_id:str = None, attachments:list = None, mask:bool = False):
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
                    await self.sendNotification(replied_user_id, f"@{self.currentUser.id}さんがあなたのポストに返信しました。", f"#post/{newPost['id']}")
            if(repost_id):
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
                    if(content or attachments):
                        await self.sendNotification(replied_user_id, f"@{self.currentUser.id}さんがあなたのポストを引用しました。", f"#post/{newPost['id']}")
                    else:
                        await self.sendNotification(replied_user_id, f"@{self.currentUser.id}さんがあなたポストをリポストしました。", f"#post/{newPost['id']}")
                    
            #メンションの通知送信
            mentioned_ids = set()
            for match in re.finditer(r"@(\d+)", content):
                mentioned_id = int(match.group(1))
                if(mentioned_id != self.currentUser.id and mentioned_id != replied_user_id):
                    mentioned_ids.add(mentioned_id)
            for id in mentioned_ids:
                await self.sendNotification(id, f"@{self.currentUser.id}さんがあなたをメンションしました。", f"#post/{newPost['id']}")
            return Post(self, newPost)
        except Exception as e:
            log.error(f"ポスト中にエラーが発生しました。\n{e}")

    async def get_hydrated_posts(self, ids:list[str], profile:bool = False) -> list[Post]:
        """
        ポストの詳細をまとめて取得します
        Args:
            ids (list): 取得するポストIDのリスト
        """
        log = get_log("get_hydrated_posts")
        try:
            async with aiohttp.ClientSession() as a_session:
                async with a_session.post(
                    f"{self.supabase_url}/rest/v1/rpc/get_hydrated_posts",
                    headers = {
                        "apikey": self.supabase_token,
                        "Authorization": f"Bearer {self.supabase_token}",
                        "Content-Type": "application/json",
                        "Content-Profile": "public",
                        "Origin": "https://nyax.onrender.com"
                    },
                    data=json.dumps({
                        "p_post_ids": ids,
                        "p_profile": profile
                    }, separators=(",", ":"))
                ) as post:
                    data = await post.json()
            if "error" in data:
                raise Exception(data["error"])
            posts:list[Post] = []
            for i in data:
                posts.append(Post(self, i))
            return posts
        except Exception as e:
            log.error(f"ポストの情報取得中にエラーが発生しました。\n{e}")

    async def get_notifications(self) -> list[Notice]:
        response = (
            await self.supabase.table("user")
            .select("notice")
            .eq("id", self.currentUser.id)
            .execute()
        )
        res = response.data[0]
        notices = res["notice"]
        notices2:list[Notice] = []
        for i in notices:
            notices2.append(Notice(i if type(i) is dict else {"id": uuid.uuid4(), "message": i, "open": "", "click": True}))
        return notices2
    async def uploadFileViaEdgeFunction(self, file):
        async with aiohttp.ClientSession() as a_session:
            formData = aiohttp.FormData()
            formData.add_field("file", file)
            async with a_session.post(f"{self.supabase_url.replace(".supabase.co", ".functions.supabase.co")}/upload-file") as resp:
                result = await resp.json()
            res_data = result["data"] if "data" in result else result
            if "error" in res_data:
                raise

    async def get_dm_list(self) -> list[DM]:
        response = (
            await self.supabase.table("dm")
            .select("id, title, member,time")
            .contains("member", [self.currentUser.id])
            .order("time", desc=True)
            .execute()
        ).data
        dms:list[DM] = []
        for i in response:
            dms.append(DM(self, i))
        return dms

