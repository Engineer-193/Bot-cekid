# ══════════════════════════════════════════════════════════════════════════════
#  CekID Bot — main.py (all-in-one, Pterodactyl ready)
#  Berisi: card generator + gen session + bot utama
#
#  Cara pakai di Pterodactyl:
#    1. Upload 4 file: main.py, config.py, requirements.txt, .env
#    2. Isi .env dengan BOT_TOKEN, TELETHON_API_ID, TELETHON_API_HASH
#    3. Di console Pterodactyl ketik:  python3 main.py --gensession
#       Ikuti instruksi → masukkan nomor HP & OTP
#       Salin TELETHON_SESSION ke file .env
#    4. Klik Start / jalankan bot normal
# ══════════════════════════════════════════════════════════════════════════════

import sys
import os
import io
import json
import math
import logging
import asyncio
import html
import getpass
import re
import random

# ── auto-install dependencies jika belum ada ──────────────────────────────────
def _ensure_deps():
    import subprocess
    pkgs = [
        "python-telegram-bot==21.11.1",
        "telethon==1.38.1",
        "Pillow==11.2.1",
        "python-dotenv==1.1.1",
    ]
    for pkg in pkgs:
        try:
            name = pkg.split("==")[0].replace("-", "_").lower()
            if name == "python_telegram_bot":
                import telegram
            elif name == "telethon":
                import telethon
            elif name == "pillow":
                from PIL import Image
            elif name == "python_dotenv":
                import dotenv
        except ImportError:
            print(f"[SETUP] Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

_ensure_deps()

# ── load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes,
)
from telegram.constants import ParseMode

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError,
)
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import (
    User, Channel, Chat,
    UserStatusOnline, UserStatusOffline, UserStatusRecently,
    UserStatusLastWeek, UserStatusLastMonth,
)

# ── import config ─────────────────────────────────────────────────────────────
try:
    from config import (
        BOT_TOKEN, TELETHON_API_ID, TELETHON_API_HASH, TELETHON_SESSION,
        STORE_LINK, DC_MAP, PROFILE_COLORS, KNOWN_IDS, MONTHS_ID, ADMIN_IDS,
    )
except ImportError:
    # fallback inline jika config.py tidak ada
    BOT_TOKEN         = os.environ.get("BOT_TOKEN", "")
    TELETHON_API_ID   = int(os.environ.get("TELETHON_API_ID", "0") or "0")
    TELETHON_API_HASH = os.environ.get("TELETHON_API_HASH", "")
    TELETHON_SESSION  = os.environ.get("TELETHON_SESSION", "")
    STORE_LINK        = "https://t.me/botallz"
    ADMIN_IDS         = []
    DC_MAP            = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}
    PROFILE_COLORS    = {
        0: ("Merah",  "#FF5951", "❤️"),
        1: ("Oranye", "#E87D3E", "🧡"),
        2: ("Ungu",   "#A479CB", "💜"),
        3: ("Hijau",  "#76C84D", "💚"),
        4: ("Cyan",   "#6CC7DC", "🩵"),
        5: ("Biru",   "#5AAFFA", "💙"),
        6: ("Pink",   "#FF5F9B", "🩷"),
    }
    KNOWN_IDS = [
        (1,              "2013-08-01"),
        (100_000_000,    "2014-01-01"),
        (500_000_000,    "2017-01-01"),
        (1_000_000_000,  "2019-01-01"),
        (2_000_000_000,  "2020-06-01"),
        (3_000_000_000,  "2021-01-01"),
        (4_000_000_000,  "2021-07-01"),
        (5_000_000_000,  "2022-01-01"),
        (6_000_000_000,  "2022-07-01"),
        (7_000_000_000,  "2023-01-01"),
        (8_000_000_000,  "2023-06-01"),
        (9_000_000_000,  "2024-01-01"),
        (10_000_000_000, "2024-07-01"),
    ]
    MONTHS_ID = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
)
log = logging.getLogger(__name__)

ENV_FILE   = Path(__file__).parent / ".env"
USERS_FILE = Path(__file__).parent / "users.json"
_client: TelegramClient | None = None


# ── User tracking ─────────────────────────────────────────────────────────────
def _load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"users": {}}


def _save_users(data: dict):
    USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def track_user(user_id: int, username: str | None, full_name: str):
    data = _load_users()
    data["users"][str(user_id)] = {
        "username": username or "",
        "name": full_name,
    }
    _save_users(data)


def get_all_user_ids() -> list[int]:
    data = _load_users()
    return [int(uid) for uid in data["users"].keys()]


# ══════════════════════════════════════════════════════════════════════════════
#  CARD GENERATOR (dari card.py, digabung di sini)
# ══════════════════════════════════════════════════════════════════════════════

W, H = 1060, 560

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Warna
BG_DEEP   = "#040d14"
BG_CARD   = "#06111b"
BG_PANEL  = "#070f18"
BLUE_DIM  = "#0a2035"
BLUE_MID  = "#0d3658"
BLUE_BORD = "#1b6da8"
BLUE_GLOW = "#2ea8e0"
BLUE_CYAN = "#4dc8f0"
CYAN_LITE = "#7ee0f8"
WHITE     = "#e8f4ff"
LABEL_COL = "#5ab8d8"
VALUE_COL = "#ddeeff"
TITLE_COL = "#c8e8ff"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _circle_avatar(img_bytes, size: int, letter: str = "?") -> Image.Image:
    out  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)
    if img_bytes:
        try:
            photo = (
                Image.open(io.BytesIO(img_bytes))
                .convert("RGBA")
                .resize((size, size), Image.LANCZOS)
            )
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
            out.paste(photo, (0, 0), mask)
            return out
        except Exception:
            pass
    draw.ellipse([0, 0, size - 1, size - 1], fill="#0d1a2a")
    draw.text(
        (size // 2, size // 2), letter.upper(),
        font=_font(size // 3, bold=True), fill="#4ab8e8", anchor="mm",
    )
    return out


def _draw_tech_corner(draw, x, y, w, h, color, size=22, thick=3):
    draw.line([(x, y + size), (x, y), (x + size, y)], fill=color, width=thick)
    draw.line([(x + w - size, y), (x + w, y), (x + w, y + size)], fill=color, width=thick)
    draw.line([(x, y + h - size), (x, y + h), (x + size, y + h)], fill=color, width=thick)
    draw.line([(x + w - size, y + h), (x + w, y + h), (x + w, y + h - size)], fill=color, width=thick)


def _draw_dot_matrix(draw, x0, y0, x1, y1, color, spacing=14, r=1):
    xi = x0
    while xi <= x1:
        yi = y0
        while yi <= y1:
            draw.ellipse([xi - r, yi - r, xi + r, yi + r], fill=color)
            yi += spacing
        xi += spacing


def _draw_glow_line(draw, x0, y0, x1, y1, color_bright, color_dim, width=2):
    draw.line([(x0, y0), (x1, y1)], fill=color_dim,    width=width + 4)
    draw.line([(x0, y0), (x1, y1)], fill=color_bright, width=width)


def _draw_barcode(draw, x, y, w, h, color):
    rng = random.Random(42)
    cx = x
    while cx < x + w:
        bar_w = rng.choice([2, 3, 4, 2, 1, 3])
        if rng.random() > 0.4:
            draw.rectangle([cx, y, cx + bar_w - 1, y + h], fill=color)
        cx += bar_w + rng.choice([1, 2, 1])


def _draw_star(draw, cx, cy, r_outer, r_inner, points, fill, outline):
    pts = []
    for i in range(points * 2):
        angle = math.radians(i * 180 / points - 90)
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=fill, outline=outline)


def generate_card(
    mention: str,
    user_id: str,
    username: str,
    dc: str,
    is_premium: bool,
    estimated_date: str,
    color_name: str,
    color_hex: str,
    color_emoji: str,
    avatar_bytes,
) -> bytes:

    img  = Image.new("RGB", (W, H), BG_DEEP)
    draw = ImageDraw.Draw(img)

    MARGIN = 18
    CX0, CY0, CX1, CY1 = MARGIN, MARGIN, W - MARGIN, H - MARGIN

    # Glow luar kartu
    for g in range(12, 0, -2):
        draw.rounded_rectangle(
            [CX0 - g, CY0 - g, CX1 + g, CY1 + g],
            radius=24 + g // 2,
            fill=None, outline=(0, 80 + g * 8, 150 + g * 6),
        )

    # Body kartu
    draw.rounded_rectangle([CX0, CY0, CX1, CY1], radius=22, fill=BG_CARD)

    # Panel kiri
    PANEL_W = 300
    draw.rounded_rectangle([CX0, CY0, CX0 + PANEL_W, CY1], radius=22, fill=BG_PANEL)
    draw.line([(CX0 + PANEL_W, CY0 + 10), (CX0 + PANEL_W, CY1 - 10)], fill=BLUE_MID,  width=3)
    draw.line([(CX0 + PANEL_W + 4, CY0 + 10), (CX0 + PANEL_W + 4, CY1 - 10)], fill=BLUE_BORD, width=1)
    _draw_dot_matrix(draw, CX0 + 8, CY0 + 8, CX0 + PANEL_W - 8, CY1 - 8, "#0a1e30", spacing=16, r=1)

    # Panel kanan
    PANEL_RX = CX0 + PANEL_W + 14

    # Judul
    title_font = _font(34, bold=True)
    for off in [(2, 2), (-1, -1), (1, -1), (-1, 1)]:
        draw.text((PANEL_RX + 20 + off[0], CY0 + 22 + off[1]), "TELEGRAM PROFILE CARD", font=title_font, fill="#001030")
    draw.text((PANEL_RX + 20, CY0 + 22), "TELEGRAM PROFILE CARD", font=title_font, fill=TITLE_COL)

    # Garis bawah judul
    line_y = CY0 + 72
    _draw_glow_line(draw, PANEL_RX + 10, line_y, CX1 - 14, line_y, BLUE_GLOW, BLUE_MID, width=2)
    _draw_glow_line(draw, PANEL_RX + 10, line_y + 5, CX1 - 14, line_y + 5, BLUE_BORD, BLUE_DIM, width=1)
    for px in [PANEL_RX + 10, CX1 - 14]:
        draw.ellipse([px - 4, line_y - 4, px + 4, line_y + 4], fill=BLUE_GLOW)
        draw.ellipse([px - 2, line_y - 2, px + 2, line_y + 2], fill=CYAN_LITE)

    # Avatar
    AV_DIAM = 168
    AV_R    = AV_DIAM // 2
    AV_CX   = CX0 + PANEL_W // 2
    AV_CY   = H // 2 - 18

    for ring_r, ring_c, ring_w in [
        (AV_R + 22, "#041222", 14),
        (AV_R + 18, "#062030", 10),
        (AV_R + 14, "#0a3050", 6),
        (AV_R + 10, "#1060a0", 4),
        (AV_R + 6,  BLUE_BORD, 3),
        (AV_R + 2,  BLUE_GLOW, 2),
    ]:
        draw.ellipse([AV_CX - ring_r, AV_CY - ring_r, AV_CX + ring_r, AV_CY + ring_r], outline=ring_c, width=ring_w)

    for angle_deg in range(0, 360, 20):
        ang = math.radians(angle_deg)
        px  = AV_CX + int((AV_R + 8) * math.cos(ang))
        py  = AV_CY + int((AV_R + 8) * math.sin(ang))
        dot_r = 2 if angle_deg % 40 == 0 else 1
        draw.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                     fill=BLUE_GLOW if angle_deg % 40 == 0 else BLUE_BORD)

    letter = (mention.lstrip("@") or "?")[0]
    av = _circle_avatar(avatar_bytes, AV_DIAM, letter=letter)
    img.paste(av, (AV_CX - AV_R, AV_CY - AV_R), av)

    draw = ImageDraw.Draw(img)

    # Logo TG kecil
    TG_CX, TG_CY, TG_R = AV_CX, AV_CY + AV_R + 26, 18
    draw.ellipse([TG_CX - TG_R - 3, TG_CY - TG_R - 3, TG_CX + TG_R + 3, TG_CY + TG_R + 3], fill=BLUE_BORD, outline=BLUE_GLOW, width=2)
    draw.ellipse([TG_CX - TG_R, TG_CY - TG_R, TG_CX + TG_R, TG_CY + TG_R], fill="#1a7fc4")
    draw.text((TG_CX, TG_CY), "✈", font=_font(18, bold=True), fill=WHITE, anchor="mm")

    # Fields
    fields = [
        ("Nama Lengkap",    str(mention)),
        ("User ID",         str(user_id)),
        ("Username",        str(username)),
        ("Data Center",     str(dc)),
        ("Akun Premium",    "Ya" if is_premium else "Tidak"),
        ("Estimasi Dibuat", str(estimated_date)),
        ("Warna Profil",    str(color_name)),
    ]

    LABEL_FONT = _font(21, bold=True)
    VALUE_FONT = _font(23, bold=True)
    COLON_FONT = _font(21, bold=True)
    FX_LABEL   = PANEL_RX + 22
    FX_COLON   = PANEL_RX + 240
    FX_VALUE   = PANEL_RX + 268
    FY_START   = line_y + 26
    F_LINE_H   = 58

    for i, (label, value) in enumerate(fields):
        fy = FY_START + i * F_LINE_H
        if i > 0:
            draw.line([(FX_LABEL, fy - 6), (CX1 - 14, fy - 6)], fill=BLUE_DIM, width=1)
        draw.ellipse([FX_LABEL - 10, fy + 8, FX_LABEL - 4, fy + 14], fill=BLUE_GLOW)
        draw.text((FX_LABEL, fy), label, font=LABEL_FONT, fill=LABEL_COL)
        draw.text((FX_COLON, fy), ":", font=COLON_FONT, fill=LABEL_COL)

        if label == "Warna Profil":
            val_color = color_hex
        elif label == "Akun Premium":
            val_color = "#4df0a0" if is_premium else VALUE_COL
        elif label in ("User ID", "Username", "Estimasi Dibuat"):
            val_color = WHITE
        else:
            val_color = VALUE_COL

        draw.text((FX_VALUE, fy), value, font=VALUE_FONT, fill=val_color)

    # Sudut tech
    _draw_tech_corner(draw, CX0, CY0, CX1 - CX0, CY1 - CY0, color=BLUE_GLOW, size=30, thick=3)
    _draw_tech_corner(draw, CX0 + 8, CY0 + 8, CX1 - CX0 - 16, CY1 - CY0 - 16, color=BLUE_MID, size=16, thick=2)

    # Garis atas bawah panel kanan
    for gap in [0, 3]:
        draw.line([(PANEL_RX + 10, CY0 + 10 + gap), (CX1 - 14, CY0 + 10 + gap)], fill=BLUE_MID if gap else BLUE_BORD, width=1)
        draw.line([(PANEL_RX + 10, CY1 - 10 - gap), (CX1 - 14, CY1 - 10 - gap)], fill=BLUE_MID if gap else BLUE_BORD, width=1)

    # Footer
    FOOTER_Y     = CY1 - 38
    footer_line_y = FOOTER_Y + 14

    draw.text((CX0 + 28, FOOTER_Y + 6), "PREMIUM ACCOUNT", font=_font(12), fill=BLUE_BORD)
    draw.line([(CX0 + 20, footer_line_y), (CX0 + PANEL_W - 20, footer_line_y)], fill=BLUE_MID, width=1)

    STAR_CX, STAR_CY = W // 2, footer_line_y
    _draw_star(draw, STAR_CX, STAR_CY, r_outer=14, r_inner=6, points=5, fill=BLUE_DIM,   outline=BLUE_BORD)
    _draw_star(draw, STAR_CX, STAR_CY, r_outer=10, r_inner=5, points=5, fill="#0a2040",  outline=BLUE_GLOW)

    draw.line([(CX0 + PANEL_W + 20, footer_line_y), (CX1 - 20, footer_line_y)], fill=BLUE_MID, width=1)
    draw.text((CX1 - 28, FOOTER_Y + 2), "SECURE • PRIVATE • PREMIUM", font=_font(10), fill=BLUE_MID, anchor="rt")
    _draw_barcode(draw, x=CX1 - 28 - 120, y=FOOTER_Y - 16, w=115, h=22, color=BLUE_MID)

    draw.text((CX0 + 14, CY0 + 14), "◈", font=_font(16), fill=BLUE_BORD)
    draw.text((CX0 + PANEL_W - 30, CY0 + 14), "◈", font=_font(16), fill=BLUE_BORD)
    draw.text((AV_CX, AV_CY - AV_R - 16), "[ PROFILE ]", font=_font(11), fill=BLUE_BORD, anchor="mm")
    draw.text((CX1 - 16, CY1 - 6), "CekID Bot | @botallz", font=_font(9), fill=BLUE_DIM, anchor="rb")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════════════
#  GEN SESSION (dari gen_session.py, digabung di sini)
# ══════════════════════════════════════════════════════════════════════════════

def _save_env(key: str, value: str):
    lines = []
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


async def _run_gensession():
    print("\n" + "═" * 55)
    print("   🔧  GENERATE TELETHON SESSION — CekID Bot")
    print("═" * 55)

    if not TELETHON_API_ID or not TELETHON_API_HASH:
        print("❌ TELETHON_API_ID / TELETHON_API_HASH belum diisi di .env!")
        sys.exit(1)

    while True:
        phone = input("📱 Masukkan nomor HP (format: +628xxx): ").strip()
        if re.match(r"^\+?\d{8,15}$", phone):
            break
        print("   ⚠️  Format tidak valid. Contoh: +6281234567890\n")

    client = TelegramClient(StringSession(), TELETHON_API_ID, TELETHON_API_HASH)
    await client.connect()

    print(f"\n📨 Mengirim kode OTP ke {phone} …")
    sent = await client.send_code_request(phone)
    print("✅ Kode OTP dikirim!\n")

    for attempt in range(3):
        otp = input("🔢 Masukkan kode OTP: ").strip()
        try:
            await client.sign_in(phone, otp, phone_code_hash=sent.phone_code_hash)
            break
        except PhoneCodeInvalidError:
            print(f"   ❌ Kode salah. Sisa percobaan: {2 - attempt}\n")
            if attempt == 2:
                print("❌ Terlalu banyak percobaan.")
                await client.disconnect()
                sys.exit(1)
        except PhoneCodeExpiredError:
            print("❌ Kode OTP kadaluarsa. Ulangi lagi.")
            await client.disconnect()
            sys.exit(1)
        except SessionPasswordNeededError:
            print("\n🔐 Akun pakai 2FA.")
            for pw_attempt in range(3):
                pw = getpass.getpass("🔑 Password 2FA: ")
                try:
                    await client.sign_in(password=pw)
                    break
                except Exception as e:
                    print(f"   ❌ Password salah: {e}")
                    if pw_attempt == 2:
                        await client.disconnect()
                        sys.exit(1)
            break

    session_str = client.session.save()
    await client.disconnect()

    _save_env("TELETHON_SESSION", session_str)
    os.environ["TELETHON_SESSION"] = session_str

    print("\n" + "═" * 55)
    print("✅ SESSION BERHASIL! Disimpan ke .env")
    print("═" * 55)
    print("\nSalin baris ini ke file .env kamu:")
    print(f"TELETHON_SESSION={session_str}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  BOT UTAMA
# ══════════════════════════════════════════════════════════════════════════════

def ce(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

E_MENTION   = ce("4909285470598333031", "⭐")
E_ID        = ce("5089568170251911687", "🔑")
E_USERNAME  = ce("5188381825701021648", "🌐")
E_DC        = ce("4906902450943820893", "💻")
E_PREMIUM   = ce("4907219728767910669", "💎")
E_DATE      = ce("4913632707646325447", "📆")
E_COLOR     = ce("4908971929395791571", "🎨")
E_BOT       = ce("4906908665761497930", "🚀")
E_SCAM      = ce("6269245551586316810", "🚫")
E_RESTRICT  = ce("5215669479509335000", "🛡")
E_VERIFIED  = ce("5086854541194822683", "✅")
E_BIO       = ce("5215209935188534658", "📋")
E_LASTSEEN  = ce("4909244268977062445", "⏳")
E_CHATID    = ce("5089568170251911687", "🔑")
E_TITLE     = ce("4909285470598333031", "⭐")
E_TYPE      = ce("6269223265001017592", "🔴")
E_FAKE      = ce("6269245551586316810", "🚫")
E_NOFORWARD = ce("5215669479509335000", "🛡")
E_MEMBERS   = ce("5089320092940895083", "👥")
E_DESC      = ce("5215209935188534658", "📋")
E_INFO      = ce("5258503720928288433", "ℹ️")
E_ROCKET    = ce("4906908665761497930", "🚀")
E_BELL      = ce("6271271702408204490", "🔔")
E_HOURGLASS = ce("4909244268977062445", "⏳")
E_CLOCK     = ce("4909244268977062445", "⏳")


def estimate_date(user_id: int) -> str:
    uid   = abs(int(user_id))
    known = [(i, datetime.fromisoformat(d).replace(tzinfo=timezone.utc)) for i, d in KNOWN_IDS]
    lo, hi = known[0], known[-1]
    for i in range(len(known) - 1):
        if known[i][0] <= uid < known[i + 1][0]:
            lo, hi = known[i], known[i + 1]
            break
    t  = (uid - lo[0]) / max(hi[0] - lo[0], 1)
    ts = lo[1].timestamp() + t * (hi[1].timestamp() - lo[1].timestamp())
    d  = datetime.fromtimestamp(ts, tz=timezone.utc)
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
    # Baca langsung dari .env file supaya tidak terpotong oleh env variable
    sess = TELETHON_SESSION
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELETHON_SESSION="):
                sess = line.split("=", 1)[1].strip()
                break
    _client = TelegramClient(StringSession(sess), TELETHON_API_ID, TELETHON_API_HASH)
    await _client.connect()
    if await _client.is_user_authorized():
        log.info("✅ Telethon terhubung!")
    else:
        log.warning("⚠️  Telethon session tidak valid! Jalankan: python3 main.py --gensession")
    return _client


async def fetch_user(identifier):
    try:
        cl     = await telethon_client()
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


async def fetch_chat(identifier):
    try:
        cl     = await telethon_client()
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
                desc = "⚠️ Warning: Many users reported this account as a scam or a fake account."

            return {
                "type": "chat", "chat_id": chat_id, "title": title,
                "username": username, "tipe": tipe,
                "dc": str(dc_id) if dc_id else "?",
                "members": members, "desc": desc,
                "scam": scam, "fake": fake, "verified": verified,
                "restricted": restr, "noforwards": nofwd,
            }

        elif isinstance(entity, Chat):
            full    = await cl(GetFullChatRequest(entity.id))
            fu      = full.full_chat
            members = getattr(fu, "participants_count", None) or getattr(entity, "participants_count", None)
            desc    = getattr(fu, "about", None) or "-"
            return {
                "type": "chat", "chat_id": f"-{entity.id}",
                "title": entity.title or "?", "username": "Tidak Ada",
                "tipe": "Grup", "dc": "?", "members": members, "desc": desc,
                "scam": False, "fake": False, "verified": False,
                "restricted": False, "noforwards": False,
            }
        return None
    except Exception as e:
        log.error(f"fetch_chat error: {e}")
        return None


def caption_user(d: dict, is_self: bool) -> str:
    mention  = html.escape(str(d['mention']))
    username = html.escape(str(d['username']))
    cname    = html.escape(str(d['cname']))
    cemoji   = html.escape(str(d['cemoji']))
    id_info_ = html.escape(str(d['id_info']))
    est_date = html.escape(str(d['est_date']))
    dc       = html.escape(str(d['dc']))

    if is_self:
        return (
            f"{'─'*3} {E_ROCKET} <b><u>✦ INFORMASI PROFIL ✦</u></b> {E_ROCKET} {'─'*3}\n\n"
            f"<blockquote>"
            f"{'─'*4} {E_ROCKET} <b>Berikut adalah detail profil Anda saat ini:</b>\n\n"
            f"{E_MENTION} <b>Mention</b>        »  <b>{mention}</b>\n"
            f"{E_ID} <b>ID Kamu</b>         »  <b><code>{d['uid']}</code></b>  <i>({id_info_})</i>\n"
            f"{E_USERNAME} <b>Username</b>      »  <b>{username}</b>\n"
            f"{E_DC} <b>DC Server</b>       »  <b>{dc}</b>\n"
            f"{E_PREMIUM} <b>Akun Premium</b>  »  <b>{'✅ Ya' if d['premium'] else '❌ Tidak'}</b>\n"
            f"{E_DATE} <b>Estimasi Dibuat</b> »  <b>{est_date}</b>\n"
            f"{E_COLOR} <b>Warna Profil</b>   »  <b>{cemoji} {cname}</b>"
            f"</blockquote>\n\n"
            f"<b>{E_BELL} Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi. 🔥</b>"
        )
    else:
        raw_bio = d["bio"]
        if d["scam"] and raw_bio in ("-", "", None):
            raw_bio = "⚠️ Warning: Many users reported this account as a scam or a fake account."
        bio_val  = html.escape(str(raw_bio))
        lastseen = html.escape(str(d['last_seen']))
        return (
            f"{'─'*3} {E_MEMBERS} <b><u>✦ INFORMASI PROFIL TARGET ✦</u></b> {E_MEMBERS} {'─'*3}\n\n"
            f"<blockquote>"
            f"{'─'*4} {E_ROCKET} <b>Berikut adalah detail profil target:</b>\n\n"
            f"{E_MENTION} <b>Mention</b>        »  <b>{mention}</b>\n"
            f"{E_ID} <b>User ID</b>         »  <b><code>{d['uid']}</code></b>  <i>({id_info_})</i>\n"
            f"{E_USERNAME} <b>Username</b>      »  <b>{username}</b>\n"
            f"{E_DC} <b>DC Server</b>       »  <b>{dc}</b>\n"
            f"{E_PREMIUM} <b>Akun Premium</b>  »  <b>{'✅ Ya' if d['premium'] else '❌ Tidak'}</b>\n"
            f"{E_DATE} <b>Estimasi Dibuat</b> »  <b>{est_date}</b>\n"
            f"{E_COLOR} <b>Warna Profil</b>   »  <b>{cemoji} {cname}</b>\n"
            f"{E_BOT} <b>Bot</b>             »  <b>{'✅ Ya' if d['bot'] else '❌ Tidak'}</b>\n"
            f"{E_SCAM} <b>Scam</b>           »  <b>{'⚠️ Ya' if d['scam'] else '✅ Tidak'}</b>\n"
            f"{E_RESTRICT} <b>Restricted</b>  »  <b>{'⚠️ Ya' if d['restricted'] else '✅ Tidak'}</b>\n"
            f"{E_VERIFIED} <b>Verified</b>    »  <b>{'✅ Ya' if d['verified'] else '❌ Tidak'}</b>\n"
            f"{E_BIO} <b>Bio</b>             »  <b>{bio_val}</b>\n"
            f"{E_LASTSEEN} <b>Terakhir Dilihat</b> »  <b>{lastseen}</b>"
            f"</blockquote>\n\n"
            f"<b>{E_BELL} Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi.</b>"
        )


def caption_chat(d: dict) -> str:
    chat_id  = html.escape(str(d['chat_id']))
    title    = html.escape(str(d['title']))
    username = html.escape(str(d['username']))
    tipe     = html.escape(str(d['tipe']))
    dc       = html.escape(str(d['dc']))
    desc     = html.escape(str(d['desc']))
    members  = d['members'] if d['members'] is not None else '?'
    return (
        f"{'─'*3} {E_INFO} <b><u>✦ INFORMASI CHAT TARGET ✦</u></b> {E_INFO} {'─'*3}\n\n"
        f"<blockquote>"
        f"{'─'*4} {E_INFO} <b>Data obrolan berhasil ditemukan:</b>\n\n"
        f"{E_CHATID} <b>Chat ID</b>        »  <b><code>{chat_id}</code></b>\n"
        f"{E_TITLE} <b>Judul</b>           »  <b>{title}</b>\n"
        f"{E_USERNAME} <b>Username</b>     »  <b>{username}</b>\n"
        f"{E_TYPE} <b>Tipe</b>             »  <b>{tipe}</b>\n"
        f"{E_DC} <b>DC Server</b>          »  <b>{dc}</b>\n"
        f"{E_MEMBERS} <b>Jumlah Anggota</b> »  <b>{members}</b>\n"
        f"{E_SCAM} <b>Scam</b>             »  <b>{'⚠️ Ya' if d['scam'] else '✅ Tidak'}</b>\n"
        f"{E_FAKE} <b>Fake</b>             »  <b>{'⚠️ Ya' if d['fake'] else '✅ Tidak'}</b>\n"
        f"{E_VERIFIED} <b>Verified</b>     »  <b>{'✅ Ya' if d['verified'] else '❌ Tidak'}</b>\n"
        f"{E_RESTRICT} <b>Restricted</b>   »  <b>{'⚠️ Ya' if d['restricted'] else '✅ Tidak'}</b>\n"
        f"{E_NOFORWARD} <b>Dilindungi</b>  »  <b>{'🔒 Ya' if d['noforwards'] else '✅ Tidak'}</b>\n"
        f"{E_DESC} <b>Deskripsi</b>        »  <b>{desc}</b>"
        f"</blockquote>\n\n"
        f"<b>{E_BELL} Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi.</b>"
    )


def kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("JOIN STORE KAMI", url=STORE_LINK)],
    ])


async def send_user_card(chat_id: int, d: dict, ctx: ContextTypes.DEFAULT_TYPE, is_self: bool):
    card = generate_card(
        mention=d["mention"], user_id=str(d["uid"]), username=d["username"],
        dc=d["dc"], is_premium=d["premium"], estimated_date=d["est_date"],
        color_name=d["cname"], color_hex=d["chex"], color_emoji=d["cemoji"],
        avatar_bytes=d["photo"],
    )
    await ctx.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(card))
    await ctx.bot.send_message(
        chat_id=chat_id, text=caption_user(d, is_self),
        parse_mode=ParseMode.HTML, reply_markup=kb(),
    )


def _err_msg(detail: str = "") -> str:
    extra = f"\n\n<blockquote><b>🔍 Detail:</b> <code>{html.escape(str(detail)[:200])}</code></blockquote>" if detail else ""
    return (
        f"<b>{'─'*3} ❌ <u>GAGAL MENGAMBIL DATA</u> ❌ {'─'*3}</b>\n\n"
        f"<blockquote>"
        f"<b>⚠️ Terjadi kesalahan saat memproses permintaan.</b>\n\n"
        f"<b>Kemungkinan penyebab:</b>\n"
        f"<b>• Profil akun diset privat</b>\n"
        f"<b>• Target tidak ditemukan</b>\n"
        f"<b>• Koneksi Telethon terputus</b>"
        f"</blockquote>"
        f"{extra}\n\n"
        f"<b>🔄 Silakan coba lagi dengan ketik /start</b>"
    )


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    log.info(f"/start dari {user.id} (@{user.username or '-'})")

    msg = await ctx.bot.send_message(
        chat_id,
        f"<b>{'─'*3} {E_HOURGLASS} <u>MEMPROSES DATA</u> {E_HOURGLASS} {'─'*3}</b>\n\n"
        f"<blockquote><b>{'─'*4} {E_CLOCK} Sedang memproses profil Anda, mohon tunggu...</b></blockquote>",
        parse_mode=ParseMode.HTML,
    )
    try:
        uid      = user.id
        fname    = ((user.first_name or "") + " " + (user.last_name or "")).strip() or "Unknown"
        username = f"@{user.username}" if user.username else "Tidak Ada"
        mention  = f"@{user.username}" if user.username else fname
        cname, chex, cemoji = profile_color(uid)

        # Coba ambil info tambahan (DC, bio, foto) via Telethon — fallback jika gagal
        dc_id = "?"
        bio   = "-"
        photo = None
        try:
            cl      = await telethon_client()
            lookup  = f"@{user.username}" if user.username else user.id
            entity  = await cl.get_entity(lookup)
            full    = await cl(GetFullUserRequest(entity))
            tg_user = full.users[0]
            fu      = full.full_user
            dc_id   = str(getattr(getattr(tg_user, "photo", None), "dc_id", None) or "?")
            bio     = getattr(fu, "about", None) or "-"
            photo_buf = io.BytesIO()
            await cl.download_profile_photo(entity, file=photo_buf)
            photo_buf.seek(0)
            photo = photo_buf.read() or None
        except Exception as te:
            log.warning(f"Telethon lookup gagal (pakai data bot saja): {te}")

        d = {
            "type":       "user",
            "uid":        uid,
            "mention":    mention,
            "username":   username,
            "full_name":  fname,
            "dc":         dc_id,
            "premium":    getattr(user, "is_premium", False) or False,
            "bot":        getattr(user, "is_bot", False) or False,
            "scam":       False,
            "restricted": False,
            "verified":   False,
            "bio":        bio,
            "last_seen":  "Tersembunyi",
            "est_date":   estimate_date(uid),
            "id_info":    id_info(uid),
            "cname":      cname,
            "chex":       chex,
            "cemoji":     cemoji,
            "photo":      photo,
        }

        track_user(uid, user.username, fname)
        await msg.delete()
        await send_user_card(chat_id, d, ctx, is_self=True)
        log.info(f"✅ Kartu dikirim ke {uid}")
    except Exception as e:
        log.error(f"cmd_start error: {e}")
        try:
            await msg.delete()
        except Exception:
            pass
        await ctx.bot.send_message(
            chat_id, _err_msg(str(e)), parse_mode=ParseMode.HTML
        )


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
        identifier = f"@{slug}" if slug else None
        if not identifier:
            return
    else:
        return

    msg = await update.message.reply_text(
        f"<b>{'─'*3} {E_HOURGLASS} <u>MEMPROSES DATA</u> {E_HOURGLASS} {'─'*3}</b>\n\n"
        f"<blockquote><b>{'─'*4} {E_CLOCK} Sedang memproses informasi target, mohon tunggu...</b></blockquote>",
        parse_mode=ParseMode.HTML,
    )
    try:
        cl     = await telethon_client()
        entity = await cl.get_entity(identifier)
        await msg.delete()

        if isinstance(entity, User):
            d = await fetch_user(identifier)
            if not d:
                await update.message.reply_text(
                    _err_msg("Pengguna tidak ditemukan atau tidak bisa diakses."),
                    parse_mode=ParseMode.HTML,
                )
                return
            await send_user_card(chat_id, d, ctx, is_self=False)

        elif isinstance(entity, (Channel, Chat)):
            d = await fetch_chat(identifier)
            if not d:
                await update.message.reply_text(
                    _err_msg("Chat tidak ditemukan atau tidak bisa diakses."),
                    parse_mode=ParseMode.HTML,
                )
                return
            await ctx.bot.send_message(
                chat_id=chat_id, text=caption_chat(d),
                parse_mode=ParseMode.HTML, reply_markup=kb(),
            )
        else:
            await update.message.reply_text(
                _err_msg("Tipe entitas tidak dikenali."), parse_mode=ParseMode.HTML
            )

    except Exception as e:
        log.error(f"cmd_msg error: {e}")
        try:
            await msg.edit_text(_err_msg(str(e)), parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ <b>Akses ditolak. Hanya admin!</b>", parse_mode=ParseMode.HTML)
        return
    total = len(get_all_user_ids())
    now   = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    await update.message.reply_text(
        f"<b>📊 STATISTIK BOT</b>\n\n"
        f"<blockquote>"
        f"👥 <b>Total Pengguna</b>  »  <b>{total:,}</b>\n"
        f"🕐 <b>Waktu Sekarang</b>  »  <b>{now}</b>"
        f"</blockquote>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ <b>Akses ditolak. Hanya admin!</b>", parse_mode=ParseMode.HTML)
        return

    # Teks broadcast = semua setelah /broadcast
    text = " ".join(ctx.args).strip() if ctx.args else ""
    if not text:
        await update.message.reply_text(
            "⚠️ <b>Format:</b> <code>/broadcast pesan kamu di sini</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    user_ids = get_all_user_ids()
    total    = len(user_ids)
    ok = fail = 0

    status_msg = await update.message.reply_text(
        f"📡 <b>Mengirim broadcast ke {total} pengguna...</b>",
        parse_mode=ParseMode.HTML,
    )

    broadcast_text = (
        f"📢 <b>PESAN DARI ADMIN</b>\n\n"
        f"<blockquote>{html.escape(text)}</blockquote>"
    )

    for uid in user_ids:
        try:
            await ctx.bot.send_message(uid, broadcast_text, parse_mode=ParseMode.HTML, reply_markup=kb())
            ok += 1
        except Exception:
            fail += 1

    await status_msg.edit_text(
        f"✅ <b>Broadcast selesai!</b>\n\n"
        f"<blockquote>"
        f"📨 <b>Terkirim</b>  »  <b>{ok}</b>\n"
        f"❌ <b>Gagal</b>     »  <b>{fail}</b>\n"
        f"👥 <b>Total</b>    »  <b>{total}</b>"
        f"</blockquote>",
        parse_mode=ParseMode.HTML,
    )


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.error(f"Bot error: {ctx.error}")


async def on_startup(app):
    try:
        await telethon_client()
    except Exception as e:
        log.error(f"Telethon startup error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def _read_session_from_env() -> str:
    """Baca TELETHON_SESSION langsung dari file .env (hindari truncation)."""
    env_path = ENV_FILE
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELETHON_SESSION="):
                val = line.split("=", 1)[1].strip()
                if val:
                    return val
    return ""


def main():
    # ── Validasi wajib ──────────────────────────────────────────────────────────
    if not BOT_TOKEN:
        print("\n❌ BOT_TOKEN belum diisi di .env!\n")
        sys.exit(1)
    if not TELETHON_API_ID or not TELETHON_API_HASH:
        print("\n❌ TELETHON_API_ID / TELETHON_API_HASH belum diisi di .env!\n")
        sys.exit(1)

    # ── Cek session — auto jalankan gensession jika belum ada ──────────────────
    if "--gensession" in sys.argv or not _read_session_from_env():
        if not _read_session_from_env():
            print("\n" + "═" * 55)
            print("  ⚠️  TELETHON SESSION BELUM ADA")
            print("  Memulai proses generate session otomatis...")
            print("═" * 55 + "\n")
        asyncio.run(_run_gensession())
        if "--gensession" in sys.argv:
            return
        # Lanjut jalankan bot setelah session berhasil dibuat
        print("\n▶️  Session tersimpan. Memulai bot...\n")

    log.info("🤖 Memulai CekID Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("stats",     cmd_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_msg))
    app.add_error_handler(on_error)
    log.info("✅ Bot siap!\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
