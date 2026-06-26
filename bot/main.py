import sys, os, io, logging, asyncio, html, getpass, re
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import (
    User, Channel, Chat,
    UserStatusOnline, UserStatusOffline, UserStatusRecently,
    UserStatusLastWeek, UserStatusLastMonth,
)

from config import (
    BOT_TOKEN, TELETHON_API_ID, TELETHON_API_HASH, TELETHON_SESSION,
    STORE_LINK, DC_MAP, PROFILE_COLORS, KNOWN_IDS, MONTHS_ID,
)
from card import generate_card

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── path ke .env ──────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"

_client: TelegramClient | None = None


# ── custom emoji helper ───────────────────────────────────────────────────────

def ce(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

# ID dari AnimatedEmojies (free pack — render untuk SEMUA user, tanpa Premium)
E_MENTION   = ce("4909285470598333031", "⭐")   # bintang emas  (free ✓)
E_ID        = ce("5089568170251911687", "🔑")   # kunci          (free ✓)
E_USERNAME  = ce("5188381825701021648", "🌐")   # globe          (original)
E_DC        = ce("4906902450943820893", "💻")   # komputer       (free ✓)
E_PREMIUM   = ce("4907219728767910669", "💎")   # berlian        (free ✓)
E_DATE      = ce("4913632707646325447", "📆")   # kalender       (free ✓)
E_COLOR     = ce("4908971929395791571", "🎨")   # palet warna    (free ✓)
E_BOT       = ce("4906908665761497930", "🚀")   # roket          (free ✓)
E_SCAM      = ce("6269245551586316810", "🚫")   # larangan       (original)
E_RESTRICT  = ce("5215669479509335000", "🛡")   # perisai        (original)
E_VERIFIED  = ce("5086854541194822683", "✅")   # centang        (free ✓)
E_BIO       = ce("5215209935188534658", "📋")   # clipboard      (original)
E_LASTSEEN  = ce("4909244268977062445", "⏳")   # jam/hourglass  (free ✓)
E_CHATID    = ce("5089568170251911687", "🔑")   # kunci          (free ✓)
E_TITLE     = ce("4909285470598333031", "⭐")   # bintang emas   (free ✓)
E_TYPE      = ce("6269223265001017592", "🔴")   # dot merah      (original)
E_FAKE      = ce("6269245551586316810", "🚫")   # larangan       (original)
E_NOFORWARD = ce("5215669479509335000", "🛡")   # perisai        (original)
E_MEMBERS   = ce("5089320092940895083", "👥")   # orang-orang    (free ✓)
E_DESC      = ce("5215209935188534658", "📋")   # clipboard      (original)
E_INFO      = ce("5258503720928288433", "ℹ️")   # info           (original)
E_ROCKET    = ce("4906908665761497930", "🚀")   # roket          (free ✓)
E_BELL      = ce("6271271702408204490", "🔔")   # bel            (original)
E_HOURGLASS = ce("4909244268977062445", "⏳")   # hourglass      (free ✓)
E_CLOCK     = ce("4909244268977062445", "⏳")   # hourglass/jam  (free ✓)


# ── helpers ───────────────────────────────────────────────────────────────────

def estimate_date(user_id: int) -> str:
    uid = abs(int(user_id))
    known = [(i, datetime.fromisoformat(d).replace(tzinfo=timezone.utc)) for i, d in KNOWN_IDS]
    lo, hi = known[0], known[-1]
    for i in range(len(known) - 1):
        if known[i][0] <= uid < known[i + 1][0]:
            lo, hi = known[i], known[i + 1]
            break
    t = (uid - lo[0]) / max(hi[0] - lo[0], 1)
    ts = lo[1].timestamp() + t * (hi[1].timestamp() - lo[1].timestamp())
    d = datetime.fromtimestamp(ts, tz=timezone.utc)
    return f"{d.day} {MONTHS_ID[d.month]} {d.year}"


def id_info(user_id: int) -> str:
    s = str(abs(user_id))
    return f"ID {s[0]}, {len(s)} digit"


def profile_color(user_id: int):
    return PROFILE_COLORS[abs(user_id) % 7]


def last_seen(status) -> str:
    if status is None:                          return "Tersembunyi"
    if isinstance(status, UserStatusOnline):    return "Online"
    if isinstance(status, UserStatusRecently):  return "Recently"
    if isinstance(status, UserStatusLastWeek):  return "Minggu lalu"
    if isinstance(status, UserStatusLastMonth): return "Bulan lalu"
    if isinstance(status, UserStatusOffline):
        d = status.was_online
        return f"{d.day} {MONTHS_ID[d.month]} {d.year}" if d else "Offline"
    return "Lama sekali"


async def telethon_client() -> TelegramClient:
    global _client
    if _client and _client.is_connected():
        return _client
    _client = TelegramClient(StringSession(TELETHON_SESSION), TELETHON_API_ID, TELETHON_API_HASH)
    await _client.connect()
    if await _client.is_user_authorized():
        log.info("✅ Telethon terhubung!")
    else:
        log.warning("⚠️  Telethon session tidak valid!")
    return _client


# ── fetch user ────────────────────────────────────────────────────────────────

async def fetch_user(identifier) -> dict | None:
    try:
        cl = await telethon_client()
        entity = await cl.get_entity(identifier)
        full   = await cl(GetFullUserRequest(entity))
        user   = full.users[0]
        fu     = full.full_user

        uid      = user.id
        fname    = ((user.first_name or "") + " " + (user.last_name or "")).strip() or "Unknown"
        username = f"@{user.username}" if user.username else "Tidak Ada"
        mention  = f"@{user.username}" if user.username else fname
        dc_id    = getattr(getattr(user, "photo", None), "dc_id", None)

        photo_buf = io.BytesIO()
        await cl.download_profile_photo(entity, file=photo_buf)
        photo_buf.seek(0)
        photo = photo_buf.read() or None

        cname, chex, cemoji = profile_color(uid)

        return {
            "type":       "user",
            "uid":        uid,
            "mention":    mention,
            "username":   username,
            "full_name":  fname,
            "dc":         str(dc_id) if dc_id else "?",
            "premium":    getattr(user, "premium",    False) or False,
            "bot":        getattr(user, "bot",        False) or False,
            "scam":       getattr(user, "scam",       False) or False,
            "restricted": getattr(user, "restricted", False) or False,
            "verified":   getattr(user, "verified",   False) or False,
            "bio":        getattr(fu,   "about",      None)  or "-",
            "last_seen":  last_seen(getattr(user, "status", None)),
            "est_date":   estimate_date(uid),
            "id_info":    id_info(uid),
            "cname":      cname,
            "chex":       chex,
            "cemoji":     cemoji,
            "photo":      photo,
        }
    except Exception as e:
        log.error(f"fetch_user error: {e}")
        return None


# ── fetch channel / group ────────────────────────────────────────────────────

async def fetch_chat(identifier) -> dict | None:
    try:
        cl = await telethon_client()
        entity = await cl.get_entity(identifier)

        if isinstance(entity, Channel):
            full = await cl(GetFullChannelRequest(entity))
            fu   = full.full_chat
            ch   = entity

            chat_id  = f"-100{ch.id}"
            title    = ch.title or "?"
            username = f"@{ch.username}" if getattr(ch, "username", None) else "Tidak Ada"
            tipe     = "Channel" if ch.broadcast else "Supergroup"
            dc_id    = getattr(getattr(ch, "photo", None), "dc_id", None)
            members  = getattr(fu, "participants_count", None)
            desc     = getattr(fu, "about", None) or "-"
            scam     = getattr(ch, "scam",       False) or False
            fake     = getattr(ch, "fake",       False) or False
            verified = getattr(ch, "verified",   False) or False
            restr    = getattr(ch, "restricted", False) or False
            nofwd    = getattr(ch, "noforwards", False) or False

            if scam and desc in ("-", "", None):
                desc = "⚠️ Warning: Many users reported this account as a scam or a fake account. Please be careful, especially if it asks you for money."

            return {
                "type":       "chat",
                "chat_id":    chat_id,
                "title":      title,
                "username":   username,
                "tipe":       tipe,
                "dc":         str(dc_id) if dc_id else "?",
                "members":    members,
                "desc":       desc,
                "scam":       scam,
                "fake":       fake,
                "verified":   verified,
                "restricted": restr,
                "noforwards": nofwd,
            }

        elif isinstance(entity, Chat):
            full    = await cl(GetFullChatRequest(entity.id))
            fu      = full.full_chat
            members = getattr(fu, "participants_count", None) or getattr(entity, "participants_count", None)
            desc    = getattr(fu, "about", None) or "-"

            return {
                "type":       "chat",
                "chat_id":    f"-{entity.id}",
                "title":      entity.title or "?",
                "username":   "Tidak Ada",
                "tipe":       "Grup",
                "dc":         "?",
                "members":    members,
                "desc":       desc,
                "scam":       False,
                "fake":       False,
                "verified":   False,
                "restricted": False,
                "noforwards": False,
            }

        else:
            return None

    except Exception as e:
        log.error(f"fetch_chat error: {e}")
        return None


# ── captions ──────────────────────────────────────────────────────────────────

def caption_user(d: dict, is_self: bool) -> str:
    mention  = html.escape(str(d['mention']))
    username = html.escape(str(d['username']))
    cname    = html.escape(str(d['cname']))
    cemoji   = html.escape(str(d['cemoji']))
    id_info  = html.escape(str(d['id_info']))
    est_date = html.escape(str(d['est_date']))
    dc       = html.escape(str(d['dc']))

    if is_self:
        text = (
            f"─── {E_ROCKET} <b><u>INFORMASI PROFIL</u></b> {E_ROCKET} ───\n\n"
            f"<blockquote>"
            f"──── {E_ROCKET} Berikut adalah detail profil Anda saat ini:\n\n"
            f"{E_MENTION} <b>Mention</b> » {mention}\n"
            f"{E_ID} <b>ID Kamu</b> » {d['uid']} ({id_info})\n"
            f"{E_USERNAME} <b>Username</b> » {username}\n"
            f"{E_DC} <b>DC ID</b> » {dc}\n"
            f"{E_PREMIUM} <b>Akun Premium</b> » {'Ya' if d['premium'] else 'Tidak'}\n"
            f"{E_DATE} <b>Estimasi Dibuat</b> » {est_date}\n"
            f"{E_COLOR} <b>Warna Profil</b> » {cemoji} {cname}"
            f"</blockquote>\n\n"
            f"{E_BELL} <u>Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi.</u> 🔥"
        )
        return text
    else:
        raw_bio = d["bio"]
        if d["scam"] and raw_bio in ("-", "", None):
            raw_bio = "⚠️ Warning: Many users reported this account as a scam or a fake account. Please be careful, especially if it asks you for money."
        bio_val  = html.escape(str(raw_bio))
        lastseen = html.escape(str(d['last_seen']))

        text = (
            f"─── {E_MEMBERS} <b><u>INFORMASI PROFIL TARGET</u></b> {E_MEMBERS} ───\n\n"
            f"<blockquote>"
            f"──── {E_ROCKET} Berikut adalah detail profil target:\n\n"
            f"{E_MENTION} <b>Mention</b> » {mention}\n"
            f"{E_ID} <b>ID Kamu</b> » {d['uid']} ({id_info})\n"
            f"{E_USERNAME} <b>Username</b> » {username}\n"
            f"{E_DC} <b>DC ID</b> » {dc}\n"
            f"{E_PREMIUM} <b>Akun Premium</b> » {'Ya' if d['premium'] else 'Tidak'}\n"
            f"{E_DATE} <b>Estimasi Dibuat</b> » {est_date}\n"
            f"{E_COLOR} <b>Warna Profil</b> » {cemoji} {cname}\n"
            f"{E_BOT} <b>Bot</b> » {'True' if d['bot'] else 'False'}\n"
            f"{E_SCAM} <b>Scam</b> » {'True' if d['scam'] else 'False'}\n"
            f"{E_RESTRICT} <b>Restricted</b> » {'True' if d['restricted'] else 'False'}\n"
            f"{E_VERIFIED} <b>Verified</b> » {'True' if d['verified'] else 'False'}\n"
            f"{E_BIO} <b>Bio</b> » {bio_val}\n"
            f"{E_LASTSEEN} <b>Terakhir Dilihat</b> » {lastseen}"
            f"</blockquote>\n\n"
            f"{E_BELL} <u>Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi.</u>"
        )
        return text


def caption_chat(d: dict) -> str:
    chat_id  = html.escape(str(d['chat_id']))
    title    = html.escape(str(d['title']))
    username = html.escape(str(d['username']))
    tipe     = html.escape(str(d['tipe']))
    dc       = html.escape(str(d['dc']))
    desc     = html.escape(str(d['desc']))
    members  = d['members'] if d['members'] is not None else '?'

    text = (
        f"─── {E_INFO} <b><u>INFORMASI CHAT TARGET</u></b> {E_INFO} ───\n\n"
        f"<blockquote>"
        f"──── {E_INFO} Data obrolan berhasil ditemukan:\n\n"
        f"{E_CHATID} <b>Chat ID</b> » <code>{chat_id}</code>\n"
        f"{E_TITLE} <b>Judul</b> » {title}\n"
        f"{E_USERNAME} <b>Username</b> » {username}\n"
        f"{E_TYPE} <b>Tipe</b> » {tipe}\n"
        f"{E_DC} <b>DC ID</b> » {dc}\n"
        f"{E_SCAM} <b>Scam</b> » {'True' if d['scam'] else 'False'}\n"
        f"{E_FAKE} <b>Fake</b> » {'True' if d['fake'] else 'False'}\n"
        f"{E_VERIFIED} <b>Verified</b> » {'True' if d['verified'] else 'False'}\n"
        f"{E_RESTRICT} <b>Restricted</b> » {'True' if d['restricted'] else 'False'}\n"
        f"{E_NOFORWARD} <b>Dilindungi</b> » {'True' if d['noforwards'] else 'False'}\n\n"
        f"{E_MEMBERS} <b>Jumlah Anggota</b> » {members}\n"
        f"{E_DESC} <b>Deskripsi</b> » {desc}"
        f"</blockquote>\n\n"
        f"{E_BELL} <u>Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi.</u>"
    )
    return text


def kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏪 JOIN STORE KAMI", url=STORE_LINK)]])


async def send_user_card(chat_id: int, d: dict, ctx: ContextTypes.DEFAULT_TYPE, is_self: bool):
    card = generate_card(
        mention=d["mention"], user_id=str(d["uid"]), username=d["username"],
        dc=d["dc"], is_premium=d["premium"], estimated_date=d["est_date"],
        color_name=d["cname"], color_hex=d["chex"], color_emoji=d["cemoji"],
        avatar_bytes=d["photo"],
    )
    # Kirim foto tanpa caption dulu
    await ctx.bot.send_photo(
        chat_id=chat_id,
        photo=io.BytesIO(card),
    )
    # Lalu kirim teks info sebagai pesan terpisah supaya tg-emoji render untuk semua user
    await ctx.bot.send_message(
        chat_id=chat_id,
        text=caption_user(d, is_self),
        parse_mode=ParseMode.HTML,
        reply_markup=kb(),
    )


# ── handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    log.info(f"/start dari {user.id} (@{user.username or '-'})")

    msg = await ctx.bot.send_message(
        chat_id,
        f"─── {E_HOURGLASS} <b><u>MEMPROSES DATA</u></b> {E_HOURGLASS} ───\n\n<blockquote>──── {E_CLOCK} Memproses profil Anda, mohon tunggu...</blockquote>",
        parse_mode=ParseMode.HTML,
    )
    try:
        d = await fetch_user(user.id)
        await msg.delete()
        if not d:
            await ctx.bot.send_message(chat_id, "❌ Gagal mengambil data. Coba lagi.")
            return
        await send_user_card(chat_id, d, ctx, is_self=True)
        log.info(f"✅ Kartu dikirim ke {user.id}")
    except Exception as e:
        log.error(f"cmd_start error: {e}")
        try: await msg.delete()
        except Exception: pass
        await ctx.bot.send_message(chat_id, f"❌ Error: {e}")


async def cmd_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text    = update.message.text.strip()
    chat_id = update.effective_chat.id

    if text.lstrip("-").isdigit():
        identifier = int(text)
    elif text.startswith("@"):
        identifier = text
    elif text.startswith("https://t.me/") or text.startswith("t.me/"):
        raw  = text.replace("https://", "").replace("t.me/", "").strip("/")
        slug = raw.split("/")[0]
        if slug:
            identifier = f"@{slug}"
        else:
            return
    else:
        return

    msg = await update.message.reply_text(
        f"─── {E_HOURGLASS} <b><u>MEMPROSES DATA</u></b> {E_HOURGLASS} ───\n\n<blockquote>──── {E_CLOCK} Memproses informasi target, mohon tunggu...</blockquote>",
        parse_mode=ParseMode.HTML,
    )
    try:
        cl     = await telethon_client()
        entity = await cl.get_entity(identifier)

        await msg.delete()

        if isinstance(entity, User):
            d = await fetch_user(identifier)
            if not d:
                await update.message.reply_text("❌ Pengguna tidak ditemukan atau tidak bisa diakses.")
                return
            await send_user_card(chat_id, d, ctx, is_self=False)
            log.info(f"✅ User card dikirim: {identifier}")

        elif isinstance(entity, (Channel, Chat)):
            d = await fetch_chat(identifier)
            if not d:
                await update.message.reply_text("❌ Chat tidak ditemukan atau tidak bisa diakses.")
                return
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=caption_chat(d),
                parse_mode=ParseMode.HTML,
                reply_markup=kb(),
            )
            log.info(f"✅ Chat info dikirim: {identifier}")

        else:
            await update.message.reply_text("❌ Tipe tidak dikenali.")

    except Exception as e:
        log.error(f"cmd_msg error: {e}")
        try:
            await msg.edit_text("❌ Pengguna tidak ditemukan atau tidak bisa diakses.")
        except Exception:
            pass


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.error(f"Bot error: {ctx.error}")


async def on_startup(app):
    try:
        await telethon_client()
    except Exception as e:
        log.error(f"Telethon startup error: {e}")


# ── session setup interaktif ──────────────────────────────────────────────────

def _save_env(key: str, value: str):
    """Tulis atau update key=value di file .env."""
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _interactive_setup() -> str:
    """
    Jalankan setup interaktif: minta nomor HP → OTP → password (opsional).
    Kembalikan session string yang sudah valid.
    """
    print("\n" + "═" * 55)
    print("   🔧  SETUP TELETHON SESSION — CekID Bot")
    print("═" * 55)
    print("   Session belum ada. Ikuti langkah di bawah ini.")
    print("═" * 55 + "\n")

    api_id   = TELETHON_API_ID
    api_hash = TELETHON_API_HASH

    if not api_id or not api_hash:
        print("❌ TELETHON_API_ID / API_HASH belum diisi di .env!")
        sys.exit(1)

    # ── minta nomor HP ──────────────────────────────────────────────────────
    while True:
        phone = input("📱 Masukkan nomor HP (format: +628xxx): ").strip()
        if re.match(r"^\+?\d{8,15}$", phone):
            break
        print("   ⚠️  Format tidak valid. Contoh: +6281234567890\n")

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    print(f"\n📨 Mengirim kode OTP ke {phone} …")
    sent = await client.send_code_request(phone)
    print("✅ Kode OTP dikirim!\n")

    # ── minta kode OTP ──────────────────────────────────────────────────────
    for attempt in range(3):
        otp = input("🔢 Masukkan kode OTP yang diterima: ").strip()
        try:
            await client.sign_in(phone, otp, phone_code_hash=sent.phone_code_hash)
            break
        except PhoneCodeInvalidError:
            print(f"   ❌ Kode salah. Sisa percobaan: {2 - attempt}\n")
            if attempt == 2:
                print("❌ Terlalu banyak percobaan. Restart bot dan coba lagi.")
                await client.disconnect()
                sys.exit(1)
        except PhoneCodeExpiredError:
            print("❌ Kode OTP sudah kadaluarsa. Restart bot untuk minta kode baru.")
            await client.disconnect()
            sys.exit(1)
        except SessionPasswordNeededError:
            # ── 2FA ─────────────────────────────────────────────────────────
            print("\n🔐 Akun kamu pakai 2FA (Two-Step Verification).")
            for pw_attempt in range(3):
                pw = getpass.getpass("🔑 Masukkan password 2FA: ")
                try:
                    await client.sign_in(password=pw)
                    break
                except Exception as e:
                    print(f"   ❌ Password salah: {e}")
                    if pw_attempt == 2:
                        print("❌ Terlalu banyak percobaan. Restart dan coba lagi.")
                        await client.disconnect()
                        sys.exit(1)
            break

    session_str = client.session.save()
    await client.disconnect()

    # ── simpan ke .env ──────────────────────────────────────────────────────
    _save_env("TELETHON_SESSION", session_str)
    os.environ["TELETHON_SESSION"] = session_str

    print("\n" + "═" * 55)
    print("✅ SESSION BERHASIL DIBUAT DAN DISIMPAN KE .env!")
    print("   Mulai sekarang bot langsung jalan tanpa setup ulang.")
    print("═" * 55 + "\n")

    return session_str


# ── entry ─────────────────────────────────────────────────────────────────────

def main():
    # ── validasi konfigurasi wajib ──────────────────────────────────────────
    if not BOT_TOKEN:
        print("\n❌ BOT_TOKEN belum diisi di .env!\n   Isi dulu lalu restart.\n")
        sys.exit(1)
    if not TELETHON_API_ID or not TELETHON_API_HASH:
        print("\n❌ TELETHON_API_ID / TELETHON_API_HASH belum diisi di .env!\n")
        sys.exit(1)

    # ── setup session jika belum ada ────────────────────────────────────────
    global TELETHON_SESSION
    if not TELETHON_SESSION:
        try:
            TELETHON_SESSION = asyncio.run(_interactive_setup())
        except KeyboardInterrupt:
            print("\n\n⛔ Setup dibatalkan oleh user.")
            sys.exit(0)

    # ── jalankan bot ────────────────────────────────────────────────────────
    log.info("🤖 Memulai CekID Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_msg))
    app.add_error_handler(on_error)
    log.info("✅ Bot siap!\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
