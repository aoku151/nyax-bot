from os import getenv
from dotenv import load_dotenv
from func.session import Sessions
import supabase as Supabase
from supabase import acreate_client, AsyncClient
from typing import Literal
from pydantic import BaseModel
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
    

class NyaXClient:
    def __init__(self, supabase_url:str, supabase_token:str, scid:str, scpass:str, session_path:str = "sessions.json"):
        self.sessions = Sessions(session_path)
        supabase, session = await sessions.get_supabase()
        self.supabase:AsyncClient = supabase
        self.session = session
        self.currentUser = await sessions.get_currentUser(supabase, session)

    
