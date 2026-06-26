"""
Step 2: Masukkan OTP dan selesaikan autentikasi, lalu cetak session string
"""
import asyncio
import os
import json
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_ID   = int(os.environ.get("TELETHON_API_ID", "0"))
API_HASH = os.environ.get("TELETHON_API_HASH", "")
OTP_CODE = sys.argv[1] if len(sys.argv) > 1 else ""
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else ""

async def main():
    with open("/tmp/otp_state.json") as f:
        state = json.load(f)

    phone            = state["phone"]
    phone_code_hash  = state["phone_code_hash"]
    session_str      = state["session"]

    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    try:
        await client.sign_in(phone, OTP_CODE, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        if not PASSWORD:
            print("2FA_REQUIRED")
            await client.disconnect()
            return
        await client.sign_in(password=PASSWORD)

    final_session = client.session.save()
    print("SESSION_OK:" + final_session)
    await client.disconnect()

asyncio.run(main())
