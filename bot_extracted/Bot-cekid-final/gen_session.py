import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ.get("TELETHON_API_ID", "0"))
API_HASH = os.environ.get("TELETHON_API_HASH", "")


async def main():
    print("=" * 50)
    print("  GENERATE TELETHON SESSION STRING")
    print("=" * 50)
    print()

    if not API_ID or not API_HASH:
        print("❌ TELETHON_API_ID atau TELETHON_API_HASH belum diset!")
        return

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()

    session_string = client.session.save()
    print()
    print("=" * 50)
    print("✅ SESSION STRING BERHASIL DIBUAT!")
    print("=" * 50)
    print()
    print("Copy string di bawah ini dan simpan ke Replit Secrets")
    print("dengan nama: TELETHON_SESSION")
    print()
    print("--- MULAI SESSION STRING ---")
    print(session_string)
    print("--- AKHIR SESSION STRING ---")
    print()

    # Simpan ke file untuk kemudahan copy
    with open("session.txt", "w") as f:
        f.write(session_string)
    print("✅ Juga disimpan ke file: bot/session.txt")
    print()

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
