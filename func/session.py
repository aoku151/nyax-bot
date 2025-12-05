from os import getenv
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient
import supabase as Supabase
import scapi
import asyncio
import aiohttp
import json
from func.log import get_log
from func.data import header
load_dotenv()

sp_url: str = getenv("SUPABASE_URL")
sp_key: str = getenv("SUPABASE_ANON_KEY")
sc_name: str = getenv("SCRATCH_USER")
sc_pass: str = getenv("SCRATCH_PASSWORD")

class Sessions:
    def __init__(self, file_path:str):
        """
        path(str) : Session PATH
        url(str) : Supabase URL
        """
        self.path:str = file_path
        self.url:str = "https://mnvdpvsivqqbzbtjtpws.supabase.co/functions/v1/scratch-auth-handler"

    def getSession(self, key:str):
        with open(self.path, "r") as f:
            return json.load(f)[key]
    
    def setSession(self, key:str, value:str):
        with open(self.path, "r") as f:
            data = json.load(f)
        data[key] = value
        with open(self.path, "w") as f:
            json.dump(data, f, indent=4)
    async def get_supabase(self):
        log = get_log("get_supabase")
        try:
            supabase: AsyncClient = await acreate_client(sp_url, sp_key)
            sp_jwt = self.getSession("sp_key")
            sp_res = await supabase.auth.set_session(sp_jwt, sp_jwt)
            log.info("セッションは有効です。認証に成功しました!")
            return supabase, sp_res.session
        except Exception:
            try:
                log.warning("セッションの有効期限が切れているので、新しいセッションを作成します...")
                supabase: AsyncClient = await acreate_client(sp_url, sp_key)
                sc: scapi.Session = await self.get_scratch()
                first = {"type": "generateCode", "username": sc_name}
                log.info("ログインコードを取得しています...")
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.url, json=first, headers=header) as res:
                        response = await res.json()
                log.info(f"ログインコードを取得しました!{response['code']}")
                await sc.user.post_comment(f"{response['code']}")
                second = {"type": "verifyComment", "username": sc_name, "code": response["code"]}
                log.info("セッションを取得しています...")
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.url, json=second, headers=header) as res:
                        response = await res.json()
                log.info("セッションを取得しました!")
                sp_res = await supabase.auth.set_session(response["jwt"], response["jwt"])
                self.setSession("sp_key", response["jwt"])
                log.info("セッションは有効です。認証に成功しました!")
                await sc.close()
                await supabase.realtime.connect()
                return supabase, sp_res.session
            except Exception as e:
                log.error(f"Nyaxのログイン中にエラーが発生しました。\n{e}")
    async def get_scratch(self):
        log = get_log("get_scratch")
        log.info("Scratchにログインしています...")
        try:
            sc_key = self.getSession("sc_key")
            session: scapi.Session = await scapi.session_login(sc_key)
            log.info(f"Scratchにログインしました!:{session.username}")
            return session
        except Exception:
            try:
                log.warning("セッションが無効です。再ログインしています...")
                session: scapi.Session = await scapi.login(sc_name, sc_pass)
                self.setSession("sc_key", session.session_id)
                log.info(f"Scratchにログインしました!:{session.username}")
                return session
            except Exception as e:
                log.error(f"Scratchのログインに失敗しました\n{e}")
    async def get_currentUser(self, client, session):
        log = get_log("get_currentUser")
        try:
            currentUser = (
                await client.table("user")
                .select("*")
                .eq("uuid", session.user.id)
                .execute()
            )
            return currentUser.data[0]
        except Exception as e:
            log.error("currentUserの取得中にエラーが発生しました。")
