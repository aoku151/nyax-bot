import os
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient
import scapi
import asyncio
import aiohttp
import json
load_dotenv()

sp_url: str = os.getenv("SUPABASE_URL")
sp_key: str = os.getenv("SUPABASE_ANON_KEY")
sc_name: str = os.getenv("SCRATCH_USER")
sc_pass: str = os.getenv("SCRATCH_PASSWORD")
nx_auth_url = "https://mnvdpvsivqqbzbtjtpws.supabase.co/functions/v1/scratch-auth-handler"
sessions_path = "sessions.json"

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
    try:
        supabase: AsyncClient = await acreate_client(sp_url, sp_key)
        sp_jwt = getSession("sp_key")
        await supabase.auth.set_session(sp_jwt, sp_jwt)
        print("セッションは有効です。認証に成功しました!")
        return supabase
    except Exception:
        try:
            print("セッションの有効期限が切れているので、新しいセッションを作成します...")
            supabase: AsyncClient = await acreate_client(sp_url, sp_key)
            sc = await get_scratch()
            header = {"Content-Type": "application/json"}
            first = {"type": "generateCode", "username": sc_name}
            print("ログインコードを取得しています...")
            async with aiohttp.ClientSession() as session:
                async with session.post(nx_auth_url, json=first, headers=header) as res:
                    response = await res.json()
            print(f"ログインコードを取得しました!{response['code']}")
            await sc.user.post_comment(f"{response['code']}")
            second = {"type": "verifyComment", "username": sc_name, "code": response['code']}
            print("セッションを取得しています...")
            async with aiohttp.ClientSession() as session:
                async with session.post(nx_auth_url, json=second, headers=header) as res:
                    response = await res.json()
            print("セッションを取得しました!")
            await supabase.auth.set_session(response['jwt'], response['jwt'])
            setSession("sp_key", response['jwt'])
            print("セッションは有効です。認証に成功しました!")
            await sc.client_close()
            return supabase
        except Exception as e:
            print(f"NyaXのログイン中にエラーが発生しました。\n{e}")
async def get_scratch():
    try:
        print("Scratchにログインしています...")
        sc_key = getSession("sc_key")
        session = await scapi.session_login(sc_key)
        print(f"Scratchにログインしました!:{session.username}")
        return session
    except Exception:
        try:
            print("セッションが無効です。再ログインしています...")
            session = await scapi.login(sc_name, sc_pass)
            setSession("sc_key", session.session_id)
            print(f"Scratchにログインしました!:{session.username}")
            return session
        except Exception as e:
            print(f"エラー:Scratchのログインに失敗しました\n{e}")

async def main():
    try:
        supabase: AsyncClient = await get_supabase()
    except Exception as e:
        print(e)

asyncio.run(main())
