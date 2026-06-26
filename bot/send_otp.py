"""
Step 1: Kirim OTP ke nomor HP dan simpan state untuk step 2
"""
import asyncio
import os
import json
from telethon import TelegramClient
from telethon.sessions import StringSession

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_ID   = int(os.environ.get("TELETHON_API_ID", "0"))
API_HASH = os.environ.get("TELETHON_API_HASH", "")
PHONE    = os.environ.get("PHONE_NUMBER", "")

async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    result = await client.send_code_request(PHONE)

    # Simpan phone_code_hash ke file sementara
    with open("/tmp/otp_state.json", "w") as f:
        json.dump({
            "phone": PHONE,
            "phone_code_hash": result.phone_code_hash,
            "session": client.session.save()
        }, f)

    await client.disconnect()
    print("OTP_SENT_OK")

asyncio.run(main())
