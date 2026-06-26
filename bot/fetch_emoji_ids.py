"""
Ambil emoji ID dari free Telegram sticker packs — mapping yang BENAR
"""
import asyncio, os, json
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_ID   = int(os.environ.get("TELETHON_API_ID", "0"))
API_HASH = os.environ.get("TELETHON_API_HASH", "")
SESSION  = os.environ.get("TELETHON_SESSION", "")

PACKS = ["AnimatedEmojies", "EmojiAnimations"]

async def main():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()

    all_emoji = {}  # emoticon → doc_id

    for pack_name in PACKS:
        try:
            pack = await client(GetStickerSetRequest(InputStickerSetShortName(pack_name), hash=0))

            # Mapping yang BENAR: setiap StickerPack punya .emoticon dan list .documents (IDs)
            doc_to_emoji = {}
            for sticker_pack in pack.packs:
                for doc_id in sticker_pack.documents:
                    # Simpan emoticon pertama jika ada beberapa
                    if doc_id not in doc_to_emoji:
                        doc_to_emoji[doc_id] = sticker_pack.emoticon

            print(f"\n=== Pack: {pack_name} ({len(pack.documents)} emoji) ===")
            for doc in pack.documents:
                emoticon = doc_to_emoji.get(doc.id, "?")
                print(f"  {emoticon} → ID: {doc.id}")
                if emoticon != "?":
                    all_emoji[emoticon] = doc.id

        except Exception as e:
            print(f"  [SKIP] {pack_name}: {e}")

    with open("/tmp/emoji_ids_fixed.json", "w") as f:
        json.dump({str(k): str(v) for k, v in all_emoji.items()}, f, ensure_ascii=False, indent=2)

    # Cetak emoji yang kita butuhkan
    print("\n\n=== EMOJI YANG DIBUTUHKAN BOT ===")
    needed = {
        "⭐": "E_MENTION / E_TITLE",
        "🌟": "E_MENTION alt",
        "🔑": "E_ID / E_CHATID",
        "🌐": "E_USERNAME",
        "🖥": "E_DC",
        "💻": "E_DC alt",
        "💎": "E_PREMIUM",
        "📅": "E_DATE",
        "📆": "E_DATE alt",
        "🗓": "E_DATE alt2",
        "🎨": "E_COLOR",
        "🎉": "E_COLOR alt",
        "🚀": "E_BOT / E_ROCKET",
        "🔔": "E_BELL",
        "⏳": "E_HOURGLASS",
        "🕐": "E_CLOCK / E_LASTSEEN",
        "📋": "E_BIO / E_DESC",
        "✅": "E_VERIFIED",
        "🚫": "E_SCAM / E_FAKE",
        "🛡": "E_RESTRICT / E_NOFORWARD",
        "👥": "E_MEMBERS",
        "ℹ️": "E_INFO",
        "🔴": "E_TYPE",
    }
    for emoji, label in needed.items():
        found = all_emoji.get(emoji, "NOT FOUND")
        print(f"  {emoji} ({label}) → {found}")

    await client.disconnect()

asyncio.run(main())
