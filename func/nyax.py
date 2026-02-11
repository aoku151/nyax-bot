from os import getenv
from dotenv import load_dotenv
from func.session import Sessions
import supabase as Supabase
from supabase import acreate_client, AsyncClient
from typing import Literal
from pydantic import BaseModel
from datetime import datetime
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
    def __init__(self, supabase_url:str, supabase_token:str, scid:str, scpass:str, session_path:str = "sessions.json"):
        self.sessions = Sessions(session_path)
        supabase, session = await sessions.get_supabase()
        self.supabase:AsyncClient = supabase
        self.session = session
        self.currentUser = await sessions.get_currentUser(supabase, session)

    
