import asyncio, os, json, sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

API_ID   = int(os.environ.get("TELETHON_API_ID", "0"))
API_HASH = os.environ.get("TELETHON_API_HASH", "")
OTP_CODE = sys.argv[1] if len(sys.argv) > 1 else ""
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else ""

async def main():
    with open("/tmp/otp_state.json") as f:
        state = json.load(f)
    client = TelegramClient(StringSession(state["session"]), API_ID, API_HASH)
    await client.connect()
    try:
        await client.sign_in(state["phone"], OTP_CODE, phone_code_hash=state["phone_code_hash"])
    except SessionPasswordNeededError:
        if not PASSWORD:
            print("2FA_REQUIRED"); await client.disconnect(); return
        await client.sign_in(password=PASSWORD)
    print("SESSION_OK:" + client.session.save())
    await client.disconnect()

asyncio.run(main())
