from os import getenv
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient
import supabase as Supabase
import asyncio
from func.session import Sessions
from func.log import get_log, stream_handler
import argparse
load_dotenv()

sessions_path = "sessions.json"
sessions = Sessions(sessions_path)

main_log = get_log("Main")

parser = argparse.ArgumentParser(description="送信するタイプ")
parser.add_argument("arg1", help="Type")

async def send_post(content:str = None, reply_id:str = None, repost_id:str = None):
    try:
        response = (
            await supabase.rpc("create_post", {
                "p_content": content,
                "p_reply_id": reply_id,
                "p_repost_to": repost_id,
                "p_attachments": None
            })
            .execute()
        )
    except Exception as e:
        log.error(f"ポスト中にエラーが発生しました。\n{e}")

async def main():
    log = main_log
    global currentUser, supabase, session
    try:
        supabase, session = await sessions.get_supabase()
        # session = await supabase.auth.get_session()
        currentUser = await sessions.get_currentUser(supabase, session)
        # log.debug(currentUser)

        args = parser.parse_args()
        if(args.arg1 == "Mon"):
            await send_post(repost_id=getenv("MONDAY_POST_ID"))
    except Exception as e:
        log.error(f"BOTの起動中にエラーが発生しました\n{e}")

if __name__ == "__main__":
    asyncio.run(main())
