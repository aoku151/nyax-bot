import os
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient
import scapi
import asyncio
import aiohttp
load_dotenv()

sp_url: str = os.getenv("SUPABASE_URL")
sp_key: str = os.getenv("SUPABASE_ANON_KEY")
sc_name: str = os.getenv("SCRATCH_USER")
sc_pass: str = os.getenv("SCRATCH_PASSWORD")
nx_auth_url = "https://mnvdpvsivqqbzbtjtpws.supabase.co/functions/v1/scratch-auth-handler"

async def main():
    try:
        supabase: AsyncClient = await acreate_client(sp_url, sp_key)
        session = await scapi.login(sc_name, sc_pass)
        print(session.user)

        nyax_auth_header = {"Content-Type": "application/json"}
        nyax_auth_first = {"type": "generateCode", "username": sc_name}
        async with aiohttp.ClientSession() as session:
            async with session.post(nx_auth_url, json=nyax_auth_first, headers=nyax_auth_header) as response:
                n_req = await response.json()
        print(n_req)
        code = n_req['code']
        await session.user.post_comment(f"{code}")

        nyax_auth_second = {"type": "verifyComment", "username": sc_name, "code": code}
        async with aiohttp.ClientSession() as session:
            async with session.post(nx_auth_url, json=nyax_auth_second, headers=nyax_auth_header) as response:
                n_req = await response.json()
        response = supabase.auth.set_session(n_req.jwt, n_req.jwt)
        await session.client_close()
    except Exception as e:
        print(e)

asyncio.run(main())
