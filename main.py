# ══════════════════════════════════════════════════════════════════════════════
#  CekID Bot — main.py (all-in-one, Pterodactyl ready)
#  Versi: 2.0 — colored buttons, sessions via bot, estimasi real-time
#
#  Setup di Pterodactyl:
#    1. Upload 4 file: main.py, config.py, requirements.txt, .env
#    2. Isi .env dengan BOT_TOKEN saja
#    3. Klik Start — bot aktif
#    4. /admin → tombol 🟢 Sessions → ikuti alur setup API ID/Hash/OTP
# ══════════════════════════════════════════════════════════════════════════════

import sys
import os
import io
import json
import math
import logging
import asyncio
import html
import re
import random

# ── auto-install dependencies ─────────────────────────────────────────────────
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

from datetime import datetime, timezone, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
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
        BOT_TOKEN, STORE_LINK, DC_MAP, PROFILE_COLORS, KNOWN_IDS, MONTHS_ID, ADMIN_IDS,
    )
except ImportError:
    BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
    STORE_LINK = "https://t.me/botallz"
    ADMIN_IDS  = []
    DC_MAP     = {
        1: "DC1 🇺🇸 Virginia, USA",
        2: "DC2 🇳🇱 Amsterdam, Belanda",
        3: "DC3 🇺🇸 Miami, USA",
        4: "DC4 🇳🇱 Amsterdam, Belanda",
        5: "DC5 🇸🇬 Singapura",
    }
    PROFILE_COLORS = {
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
        (100_000_000,    "2014-04-01"),
        (500_000_000,    "2016-06-01"),
        (1_000_000_000,  "2018-06-01"),
        (2_000_000_000,  "2020-04-01"),
        (3_000_000_000,  "2021-01-15"),
        (4_000_000_000,  "2021-06-01"),
        (5_000_000_000,  "2022-01-01"),
        (6_000_000_000,  "2022-09-01"),
        (7_000_000_000,  "2023-04-01"),
        (8_000_000_000,  "2023-11-01"),
        (9_000_000_000,  "2024-04-01"),
        (10_000_000_000, "2024-11-01"),
        (11_000_000_000, "2025-06-01"),
        (12_000_000_000, "2026-01-01"),
        (12_857_000_000, "2026-06-29"),
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

ENV_FILE      = Path(__file__).parent / ".env"
USERS_FILE    = Path(__file__).parent / "users.json"
SESSIONS_FILE = Path(__file__).parent / "sessions.json"
_client: TelegramClient | None = None

# ── Session setup state machine ───────────────────────────────────────────────
# State per admin_id: {"state": str, "api_id": int, "api_hash": str,
#                      "phone": str, "pclient": TelegramClient,
#                      "phone_code_hash": str, "chat_id": int, "msg_id": int}
_SESSION_SETUP: dict[int, dict] = {}

SS_API_ID  = "waiting_api_id"
SS_API_HASH = "waiting_api_hash"
SS_PHONE   = "waiting_phone"
SS_OTP     = "waiting_otp"
SS_2FA     = "waiting_2fa"


# ══════════════════════════════════════════════════════════════════════════════
#  SESSIONS CONFIG (file-based, bukan env)
# ══════════════════════════════════════════════════════════════════════════════

def _load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        try:
            return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_sessions(data: dict):
    SESSIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_session_configured() -> bool:
    d = _load_sessions()
    api_id   = d.get("api_id", 0) or int(os.environ.get("TELETHON_API_ID", "0") or "0")
    api_hash = d.get("api_hash", "") or os.environ.get("TELETHON_API_HASH", "")
    session  = d.get("session", "") or os.environ.get("TELETHON_SESSION", "")
    return bool(api_id and api_hash and _is_valid_session(session))


def _is_valid_session(sess: str) -> bool:
    if not sess or len(sess) < 100:
        return False
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=_-")
    return all(c in valid_chars for c in sess.strip())


def _get_telethon_creds() -> tuple[int, str, str]:
    """Return (api_id, api_hash, session) — file dahulu, env sebagai fallback."""
    d        = _load_sessions()
    api_id   = d.get("api_id", 0) or int(os.environ.get("TELETHON_API_ID", "0") or "0")
    api_hash = d.get("api_hash", "") or os.environ.get("TELETHON_API_HASH", "")
    session  = d.get("session", "") or os.environ.get("TELETHON_SESSION", "")
    return int(api_id), str(api_hash), str(session)


# ══════════════════════════════════════════════════════════════════════════════
#  USER TRACKING
# ══════════════════════════════════════════════════════════════════════════════

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
    data["users"][str(user_id)] = {"username": username or "", "name": full_name}
    _save_users(data)


def get_all_user_ids() -> list[int]:
    return [int(uid) for uid in _load_users()["users"].keys()]


# ══════════════════════════════════════════════════════════════════════════════
#  CARD GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

W, H = 1060, 560

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

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
    cx  = x
    while cx < x + w:
        bar_w = rng.choice([2, 3, 4, 2, 1, 3])
        if rng.random() > 0.4:
            draw.rectangle([cx, y, cx + bar_w - 1, y + h], fill=color)
        cx += bar_w + rng.choice([1, 2, 1])


def _draw_star(draw, cx, cy, r_outer, r_inner, points, fill, outline):
    pts = []
    for i in range(points * 2):
        angle = math.radians(i * 180 / points - 90)
        r     = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=fill, outline=outline)


def generate_card(
    full_name: str,
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

    for g in range(12, 0, -2):
        draw.rounded_rectangle(
            [CX0 - g, CY0 - g, CX1 + g, CY1 + g],
            radius=24 + g // 2,
            fill=None, outline=(0, 80 + g * 8, 150 + g * 6),
        )

    draw.rounded_rectangle([CX0, CY0, CX1, CY1], radius=22, fill=BG_CARD)

    PANEL_W = 300
    draw.rounded_rectangle([CX0, CY0, CX0 + PANEL_W, CY1], radius=22, fill=BG_PANEL)
    draw.line([(CX0 + PANEL_W, CY0 + 10), (CX0 + PANEL_W, CY1 - 10)], fill=BLUE_MID,  width=3)
    draw.line([(CX0 + PANEL_W + 4, CY0 + 10), (CX0 + PANEL_W + 4, CY1 - 10)], fill=BLUE_BORD, width=1)
    _draw_dot_matrix(draw, CX0 + 8, CY0 + 8, CX0 + PANEL_W - 8, CY1 - 8, "#0a1e30", spacing=16, r=1)

    PANEL_RX = CX0 + PANEL_W + 14

    title_font = _font(34, bold=True)
    for off in [(2, 2), (-1, -1), (1, -1), (-1, 1)]:
        draw.text((PANEL_RX + 20 + off[0], CY0 + 22 + off[1]), "TELEGRAM PROFILE CARD", font=title_font, fill="#001030")
    draw.text((PANEL_RX + 20, CY0 + 22), "TELEGRAM PROFILE CARD", font=title_font, fill=TITLE_COL)

    line_y = CY0 + 72
    _draw_glow_line(draw, PANEL_RX + 10, line_y, CX1 - 14, line_y, BLUE_GLOW, BLUE_MID, width=2)
    _draw_glow_line(draw, PANEL_RX + 10, line_y + 5, CX1 - 14, line_y + 5, BLUE_BORD, BLUE_DIM, width=1)
    for px in [PANEL_RX + 10, CX1 - 14]:
        draw.ellipse([px - 4, line_y - 4, px + 4, line_y + 4], fill=BLUE_GLOW)
        draw.ellipse([px - 2, line_y - 2, px + 2, line_y + 2], fill=CYAN_LITE)

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
        ang    = math.radians(angle_deg)
        px     = AV_CX + int((AV_R + 8) * math.cos(ang))
        py     = AV_CY + int((AV_R + 8) * math.sin(ang))
        dot_r  = 2 if angle_deg % 40 == 0 else 1
        draw.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                     fill=BLUE_GLOW if angle_deg % 40 == 0 else BLUE_BORD)

    letter = (full_name or "?")[0]
    av = _circle_avatar(avatar_bytes, AV_DIAM, letter=letter)
    img.paste(av, (AV_CX - AV_R, AV_CY - AV_R), av)

    draw = ImageDraw.Draw(img)

    TG_CX, TG_CY, TG_R = AV_CX, AV_CY + AV_R + 26, 18
    draw.ellipse([TG_CX - TG_R - 3, TG_CY - TG_R - 3, TG_CX + TG_R + 3, TG_CY + TG_R + 3], fill=BLUE_BORD, outline=BLUE_GLOW, width=2)
    draw.ellipse([TG_CX - TG_R, TG_CY - TG_R, TG_CX + TG_R, TG_CY + TG_R], fill="#1a7fc4")
    draw.text((TG_CX, TG_CY), "✈", font=_font(18, bold=True), fill=WHITE, anchor="mm")

    fields = [
        ("Nama Lengkap",    str(full_name)),
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

    _draw_tech_corner(draw, CX0, CY0, CX1 - CX0, CY1 - CY0, color=BLUE_GLOW, size=30, thick=3)
    _draw_tech_corner(draw, CX0 + 8, CY0 + 8, CX1 - CX0 - 16, CY1 - CY0 - 16, color=BLUE_MID, size=16, thick=2)

    for gap in [0, 3]:
        draw.line([(PANEL_RX + 10, CY0 + 10 + gap), (CX1 - 14, CY0 + 10 + gap)], fill=BLUE_MID if gap else BLUE_BORD, width=1)
        draw.line([(PANEL_RX + 10, CY1 - 10 - gap), (CX1 - 14, CY1 - 10 - gap)], fill=BLUE_MID if gap else BLUE_BORD, width=1)

    FOOTER_Y      = CY1 - 38
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
#  PREMIUM EMOJI & HTML PARSER
# ══════════════════════════════════════════════════════════════════════════════

def ce(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

E_MENTION   = ce("5852636219250317264", "⭐")
E_ID        = ce("5969696910112463071", "🪪")
E_USERNAME  = ce("5447410659077661506", "🌐")
E_DC        = ce("6003735582495216112", "📡")
E_PREMIUM   = ce("5861637182212543018", "💎")
E_DATE      = ce("5413879192267805083", "📅")
E_COLOR     = ce("5395444784611480792", "🎨")
E_BOT       = ce("5188481279963715781", "🚀")
E_SCAM      = ce("5420323339723881652", "🚫")
E_RESTRICT  = ce("5420323339723881652", "🛡")
E_VERIFIED  = ce("5251203410396458957", "✅")
E_BIO       = ce("5282843764451195532", "📋")
E_LASTSEEN  = ce("5461174173835489008", "⏳")
E_CHATID    = ce("5969696910112463071", "🪪")
E_TITLE     = ce("5852636219250317264", "⭐")
E_TYPE      = ce("5918075981649679952", "🔴")
E_FAKE      = ce("5420323339723881652", "🚫")
E_NOFORWARD = ce("5420323339723881652", "🛡")
E_MEMBERS   = ce("5348136664738839786", "👥")
E_DESC      = ce("5282843764451195532", "📋")
E_INFO      = ce("5258474669769497337", "ℹ️")
E_ROCKET    = ce("5188481279963715781", "🚀")
E_BELL      = ce("6271271702408204490", "🔔")
E_HOURGLASS = ce("5461174173835489008", "⏳")
E_CLOCK     = ce("5461174173835489008", "⏳")

import html.parser as _html_parser
from telegram import MessageEntity


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


class _TelegramHTMLParser(_html_parser.HTMLParser):
    _TAG_TYPE = {
        "b": "bold", "strong": "bold",
        "i": "italic", "em": "italic",
        "u": "underline",
        "s": "strikethrough", "strike": "strikethrough", "del": "strikethrough",
        "code": "code",
        "pre": "pre",
        "tg-spoiler": "spoiler",
        "blockquote": "blockquote",
    }

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._parts: list[str] = []
        self._entities: list[MessageEntity] = []
        self._stack: list[tuple[str, dict, int]] = []
        self._utf16_pos: int = 0

    def handle_starttag(self, tag: str, attrs):
        self._stack.append((tag, dict(attrs), self._utf16_pos))

    def handle_endtag(self, tag: str):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                open_tag, attrs_dict, start = self._stack.pop(i)
                length = self._utf16_pos - start
                if length <= 0:
                    break
                etype = self._TAG_TYPE.get(tag)
                ekw: dict = {}
                if etype:
                    pass
                elif tag == "a":
                    etype = "text_link"
                    ekw["url"] = attrs_dict.get("href", "")
                elif tag == "tg-emoji":
                    etype = "custom_emoji"
                    ekw["custom_emoji_id"] = attrs_dict.get("emoji-id", "")
                if etype:
                    self._entities.append(
                        MessageEntity(type=etype, offset=start, length=length, **ekw)
                    )
                break

    def handle_data(self, data: str):
        self._parts.append(data)
        self._utf16_pos += _utf16_len(data)

    def handle_entityref(self, name: str):
        char = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}.get(name, f"&{name};")
        self._parts.append(char)
        self._utf16_pos += _utf16_len(char)

    def handle_charref(self, name: str):
        char = chr(int(name[1:], 16) if name.startswith("x") else int(name))
        self._parts.append(char)
        self._utf16_pos += _utf16_len(char)

    def result(self) -> tuple[str, list[MessageEntity]]:
        return "".join(self._parts), self._entities


def _html_to_entities(html_text: str) -> tuple[str, list[MessageEntity]]:
    p = _TelegramHTMLParser()
    p.feed(html_text)
    return p.result()


def _strip_tgemoji(text: str) -> str:
    return re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text, flags=re.DOTALL)


async def safe_send_message(bot, *, chat_id, text, parse_mode=None, reply_markup=None, **kwargs):
    if parse_mode == ParseMode.HTML and "<tg-emoji" in text:
        try:
            plain, entities = _html_to_entities(text)
            return await bot.send_message(
                chat_id=chat_id, text=plain, entities=entities,
                reply_markup=reply_markup, **kwargs,
            )
        except Exception as e1:
            log.warning(f"[emoji] Entity-send gagal ({e1}), coba HTML…")
        try:
            return await bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode,
                reply_markup=reply_markup, **kwargs,
            )
        except Exception as e2:
            log.warning(f"[emoji] HTML-send gagal ({e2}), fallback plain emoji…")
        stripped = _strip_tgemoji(text)
        return await bot.send_message(
            chat_id=chat_id, text=stripped, parse_mode=parse_mode,
            reply_markup=reply_markup, **kwargs,
        )
    return await bot.send_message(
        chat_id=chat_id, text=text, parse_mode=parse_mode,
        reply_markup=reply_markup, **kwargs,
    )


async def safe_send_photo(bot, *, chat_id, photo, caption=None, parse_mode=None, reply_markup=None, **kwargs):
    if caption and parse_mode == ParseMode.HTML and "<tg-emoji" in caption:
        try:
            plain, entities = _html_to_entities(caption)
            return await bot.send_photo(
                chat_id=chat_id, photo=photo, caption=plain, caption_entities=entities,
                reply_markup=reply_markup, **kwargs,
            )
        except Exception as e1:
            log.warning(f"[emoji] Entity-photo gagal ({e1}), coba HTML…")
        try:
            return await bot.send_photo(
                chat_id=chat_id, photo=photo, caption=caption,
                parse_mode=parse_mode, reply_markup=reply_markup, **kwargs,
            )
        except Exception as e2:
            log.warning(f"[emoji] HTML-photo gagal ({e2}), fallback plain emoji…")
        stripped = _strip_tgemoji(caption)
        return await bot.send_photo(
            chat_id=chat_id, photo=photo, caption=stripped,
            parse_mode=parse_mode, reply_markup=reply_markup, **kwargs,
        )
    return await bot.send_photo(
        chat_id=chat_id, photo=photo, caption=caption,
        parse_mode=parse_mode, reply_markup=reply_markup, **kwargs,
    )


async def safe_edit_text(msg, *, text, parse_mode=None, reply_markup=None, **kwargs):
    if parse_mode == ParseMode.HTML and "<tg-emoji" in text:
        try:
            plain, entities = _html_to_entities(text)
            return await msg.edit_text(
                text=plain, entities=entities,
                reply_markup=reply_markup, **kwargs,
            )
        except Exception as e1:
            log.warning(f"[emoji] Entity-edit gagal ({e1}), coba HTML…")
        try:
            return await msg.edit_text(
                text=text, parse_mode=parse_mode,
                reply_markup=reply_markup, **kwargs,
            )
        except Exception as e2:
            log.warning(f"[emoji] HTML-edit gagal ({e2}), fallback plain emoji…")
        stripped = _strip_tgemoji(text)
        return await msg.edit_text(
            text=stripped, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs,
        )
    return await msg.edit_text(
        text=text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def estimate_date(user_id: int) -> str:
    """
    Estimasi tanggal daftar Telegram berdasarkan User ID.
    Auto-detect tanggal hari ini dan ekstrapolasi real-time jika ID
    melampaui checkpoint terakhir (mendukung tahun 2026 dan seterusnya).
    """
    uid   = abs(int(user_id))
    today = datetime.now(timezone.utc)

    known = [(i, datetime.fromisoformat(d).replace(tzinfo=timezone.utc)) for i, d in KNOWN_IDS]

    if uid <= known[0][0]:
        d = known[0][1]

    elif uid >= known[-1][0]:
        # Ekstrapolasi linear menggunakan rata-rata pertumbuhan 6 checkpoint terakhir
        pts      = known[-6:]
        id_span  = pts[-1][0] - pts[0][0]
        sec_span = (pts[-1][1] - pts[0][1]).total_seconds()
        rate     = id_span / max(sec_span, 1)   # ID per detik
        excess   = uid - known[-1][0]
        d        = known[-1][1] + timedelta(seconds=excess / rate)
        if d > today:
            d = today   # tidak melebihi hari ini

    else:
        lo, hi = known[0], known[-1]
        for i in range(len(known) - 1):
            if known[i][0] <= uid < known[i + 1][0]:
                lo, hi = known[i], known[i + 1]
                break
        t  = (uid - lo[0]) / max(hi[0] - lo[0], 1)
        ts = lo[1].timestamp() + t * (hi[1].timestamp() - lo[1].timestamp())
        d  = datetime.fromtimestamp(ts, tz=timezone.utc)

    return f"{d.day} {MONTHS_ID[d.month]} {d.year}"


def dc_label(dc_id) -> str:
    if dc_id is None:
        return "Privat 🔒"
    try:
        n = int(dc_id)
        return DC_MAP.get(n, f"DC{n}")
    except (ValueError, TypeError):
        return "Privat 🔒"


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


# ══════════════════════════════════════════════════════════════════════════════
#  TELETHON CLIENT
# ══════════════════════════════════════════════════════════════════════════════

async def telethon_client() -> TelegramClient | None:
    global _client
    if _client and _client.is_connected():
        return _client
    api_id, api_hash, session = _get_telethon_creds()
    if not api_id or not api_hash:
        log.warning("⚠️  Telethon credentials belum dikonfigurasi. Gunakan /admin → Sessions.")
        return None
    _client = TelegramClient(StringSession(session), api_id, api_hash)
    await _client.connect()
    if await _client.is_user_authorized():
        log.info("✅ Telethon terhubung!")
    else:
        log.warning("⚠️  Telethon session tidak valid. Gunakan /admin → Sessions untuk setup ulang.")
    return _client


async def _disconnect_client():
    global _client
    if _client:
        try:
            await _client.disconnect()
        except Exception:
            pass
        _client = None


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH USER / CHAT
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_user(identifier):
    try:
        cl     = await telethon_client()
        if not cl:
            return None
        entity = await cl.get_entity(identifier)
        full   = await cl(GetFullUserRequest(entity))
        user   = full.users[0]
        fu     = full.full_user

        uid      = user.id
        # Nama lengkap (bukan username)
        fname    = ((user.first_name or "") + " " + (user.last_name or "")).strip() or "Unknown"
        username = f"@{user.username}" if user.username else "Tidak Ada"
        dc_id    = getattr(getattr(user, "photo", None), "dc_id", None)

        photo_buf = io.BytesIO()
        await cl.download_profile_photo(entity, file=photo_buf)
        photo_buf.seek(0)
        photo = photo_buf.read() or None

        cname, chex, cemoji = profile_color(uid)

        return {
            "type":       "user",
            "uid":        uid,
            "full_name":  fname,
            "username":   username,
            "dc":         dc_label(dc_id),
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
        if not cl:
            return None
        entity = await cl.get_entity(identifier)

        if isinstance(entity, Channel):
            full     = await cl(GetFullChannelRequest(entity))
            fu       = full.full_chat
            ch       = entity
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
                "dc": dc_label(dc_id),
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


# ══════════════════════════════════════════════════════════════════════════════
#  CAPTION BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def caption_user(d: dict, is_self: bool) -> str:
    full_name = html.escape(str(d['full_name']))
    username  = html.escape(str(d['username']))
    cname     = html.escape(str(d['cname']))
    cemoji    = html.escape(str(d['cemoji']))
    id_info_  = html.escape(str(d['id_info']))
    est_date  = html.escape(str(d['est_date']))
    dc        = html.escape(str(d['dc']))

    if is_self:
        return (
            f"<u>{'─'*3} {E_ROCKET} <b>✦ INFORMASI PROFIL ✦</b> {E_ROCKET} {'─'*3}</u>\n\n"
            f"<blockquote>"
            f"{'─'*4} {E_ROCKET} <b>Berikut adalah detail profil Anda saat ini:</b>\n\n"
            f"{E_MENTION} <b>Nama Lengkap</b>   »  <b>{full_name}</b>\n"
            f"{E_ID} <b>ID Kamu</b>         »  <b><code>{d['uid']}</code></b>  <i>({id_info_})</i>\n"
            f"{E_USERNAME} <b>Username</b>      »  <b>{username}</b>\n"
            f"{E_DC} <b>DC Server</b>       »  <b>{dc}</b>\n"
            f"{E_PREMIUM} <b>Akun Premium</b>  »  <b>{'✅ Ya' if d['premium'] else '❌ Tidak'}</b>\n"
            f"{E_DATE} <b>Estimasi Dibuat</b> »  <b>{est_date}</b>\n"
            f"{E_COLOR} <b>Warna Profil</b>   »  <b>{cemoji} {cname}</b>"
            f"</blockquote>\n\n"
            f"<u><b>{E_BELL} Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi. 🔥</b></u>"
        )
    else:
        raw_bio = d["bio"]
        if d["scam"] and raw_bio in ("-", "", None):
            raw_bio = "⚠️ Warning: Many users reported this account as a scam or a fake account."
        bio_val  = html.escape(str(raw_bio))
        lastseen = html.escape(str(d['last_seen']))
        return (
            f"<u>{'─'*3} {E_MEMBERS} <b>✦ INFORMASI PROFIL TARGET ✦</b> {E_MEMBERS} {'─'*3}</u>\n\n"
            f"<blockquote>"
            f"{'─'*4} {E_ROCKET} <b>Berikut adalah detail profil target:</b>\n\n"
            f"{E_MENTION} <b>Nama Lengkap</b>   »  <b>{full_name}</b>\n"
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
            f"<u><b>{E_BELL} Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi.</b></u>"
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
        f"<u>{'─'*3} {E_INFO} <b>✦ INFORMASI CHAT TARGET ✦</b> {E_INFO} {'─'*3}</u>\n\n"
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
        f"<u><b>{E_BELL} Kirim ID atau Username pengguna/grup/channel untuk mengecek informasi.</b></u>"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS — button warna-warni style Telegram Bot API
# ══════════════════════════════════════════════════════════════════════════════
#  Palet warna via emoji:
#  🔵 Primary/Biru  🔘 Secondary/Abu  🟢 Success/Hijau  🔴 Danger/Merah
#  🟡 Warning/Kuning  🔷 Info/Biru Muda  ⬜ Light/Putih  ⬛ Dark/Hitam

def kb() -> InlineKeyboardMarkup:
    """Keyboard user biasa — JOIN STORE pakai warna Merah (Danger)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴  JOIN STORE KAMI", url=STORE_LINK)],
    ])


def kb_admin(session_ok: bool = False) -> InlineKeyboardMarkup:
    """Panel admin — tiap tombol warna berbeda, Sessions hijau (Success)."""
    sess_label = "🟢  Sessions  ✅" if session_ok else "🟢  Sessions  ⚠️ Belum Terhubung"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔵  BROADCAST",      callback_data="admin_broadcast")],
        [InlineKeyboardButton("🟡  Statistik Bot",  callback_data="admin_stats")],
        [InlineKeyboardButton(sess_label,            callback_data="admin_sessions")],
    ])


def kb_admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔷  Kembali ke Panel Admin", callback_data="admin_back")],
    ])


def kb_sessions_setup() -> InlineKeyboardMarkup:
    """Keyboard di halaman Sessions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢  Mulai Setup Sessions", callback_data="sessions_start")],
        [InlineKeyboardButton("🔷  Kembali ke Panel Admin", callback_data="admin_back")],
    ])


def kb_sessions_cancel() -> InlineKeyboardMarkup:
    """Tombol cancel saat di tengah alur setup."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴  Batalkan Setup", callback_data="sessions_cancel")],
    ])


def kb_sessions_done() -> InlineKeyboardMarkup:
    """Setelah sessions berhasil terhubung."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔷  Kembali ke Menu Utama", callback_data="admin_back")],
    ])


def kb_notify_sessions() -> InlineKeyboardMarkup:
    """Notifikasi startup — shortcut ke Sessions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢  Hubungkan Sessions", callback_data="admin_sessions")],
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN PANEL BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _admin_panel_text(username: str, uid: int, dc_str: str, total_users: int, now: str,
                      session_ok: bool = False) -> str:
    sess_line = (
        "\n⚠️ <b>Sessions belum terhubung! Silahkan hubungkan di bawah.</b>"
        if not session_ok else ""
    )
    return (
        f"<u><b>👑 PANEL ADMIN</b></u>\n\n"
        f"<b>Hallo Sayang! Selamat datang di perintah admin 💕</b>\n\n"
        f"<blockquote>"
        f"👤 <b>Nama</b>        »  <b>{html.escape(username)}</b>\n"
        f"🆔 <b>ID</b>          »  <b><code>{uid}</code></b>\n"
        f"💻 <b>DC Server</b>   »  <b>{html.escape(dc_str)}</b>\n"
        f"👥 <b>Total User</b>  »  <b>{total_users:,}</b>\n"
        f"🕐 <b>Waktu</b>       »  <b>{now}</b>"
        f"</blockquote>"
        f"{sess_line}\n\n"
        f"<u><b>📋 Pilih perintah di bawah ini:</b></u>"
    )


async def _fetch_admin_panel_data(uid: int, ptb_user) -> tuple[str, str, int, str]:
    full_name   = ((ptb_user.first_name or "") + " " + (ptb_user.last_name or "")).strip() or "Unknown"
    total_users = len(get_all_user_ids())
    now         = datetime.now(timezone(timedelta(hours=8))).strftime("%d/%m/%Y %H:%M WITA")
    dc_str      = dc_label(None)
    try:
        cl      = await telethon_client()
        if cl:
            lookup = f"@{ptb_user.username}" if ptb_user.username else uid
            entity = await cl.get_entity(lookup)
            dc_raw = getattr(getattr(entity, "photo", None), "dc_id", None)
            dc_str = dc_label(dc_raw)
    except Exception:
        pass
    return full_name, dc_str, total_users, now


_LOADING_TEXT = (
    "⏳ <b>Hallo Sayang! Selamat datang di</b>\n"
    "<b>Format Control Admin 👑</b>\n\n"
    "<blockquote>🔄 Memuat panel admin, harap tunggu...</blockquote>"
)


async def send_user_card(chat_id: int, d: dict, ctx: ContextTypes.DEFAULT_TYPE, is_self: bool):
    card = generate_card(
        full_name=d["full_name"], user_id=str(d["uid"]), username=d["username"],
        dc=d["dc"], is_premium=d["premium"], estimated_date=d["est_date"],
        color_name=d["cname"], color_hex=d["chex"], color_emoji=d["cemoji"],
        avatar_bytes=d["photo"],
    )
    await ctx.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(card))
    await safe_send_message(
        ctx.bot, chat_id=chat_id, text=caption_user(d, is_self),
        parse_mode=ParseMode.HTML, reply_markup=kb(),
    )


def _err_msg(detail: str = "") -> str:
    extra = (
        f"\n\n<blockquote><b>🔍 Detail:</b> <code>{html.escape(str(detail)[:200])}</code></blockquote>"
        if detail else ""
    )
    return (
        f"<u><b>{'─'*3} ❌ GAGAL MENGAMBIL DATA ❌ {'─'*3}</b></u>\n\n"
        f"<blockquote>"
        f"<b>⚠️ Terjadi kesalahan saat memproses permintaan.</b>\n\n"
        f"<b>Kemungkinan penyebab:</b>\n"
        f"<b>• Profil akun diset privat</b>\n"
        f"<b>• Target tidak ditemukan</b>\n"
        f"<b>• Koneksi Telethon terputus</b>\n"
        f"<b>• Sessions belum dikonfigurasi (/admin → 🟢 Sessions)</b>"
        f"</blockquote>"
        f"{extra}\n\n"
        f"<u><b>🔄 Silakan coba lagi dengan ketik /start</b></u>"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  SESSIONS SETUP FLOW
# ══════════════════════════════════════════════════════════════════════════════

def _sessions_page_text(session_ok: bool) -> str:
    if session_ok:
        d       = _load_sessions()
        api_id  = d.get("api_id", "?")
        sess    = d.get("session", "")
        preview = sess[:20] + "..." if len(sess) > 20 else sess
        return (
            f"<u><b>🔗 SESSIONS</b></u>\n\n"
            f"<blockquote>"
            f"<b>✅ Sessions sudah terhubung!</b>\n\n"
            f"🔑 <b>API ID</b>      »  <b><code>{api_id}</code></b>\n"
            f"🔐 <b>Session</b>    »  <b><code>{preview}</code></b>\n\n"
            f"<b>Bot bisa digunakan dengan akurat ✅</b>"
            f"</blockquote>\n\n"
            f"<b>Untuk setup ulang, tekan tombol di bawah.</b>"
        )
    else:
        return (
            f"<u><b>🔗 SESSIONS</b></u>\n\n"
            f"<blockquote>"
            f"<b>⚠️ Sessions belum terhubung!</b>\n\n"
            f"Untuk mengaktifkan fitur penuh bot, kamu perlu menghubungkan\n"
            f"akun Telegram kamu via <b>API ID</b>, <b>API Hash</b>, dan <b>nomor HP</b>.\n\n"
            f"📋 <b>Yang dibutuhkan:</b>\n"
            f"• API ID dan API Hash dari <a href='https://my.telegram.org'>my.telegram.org</a>\n"
            f"• Nomor HP yang terdaftar di Telegram\n"
            f"• Kode OTP yang dikirim Telegram\n"
            f"• Password 2FA (jika diaktifkan)"
            f"</blockquote>\n\n"
            f"<b>Tekan tombol di bawah untuk memulai setup:</b>"
        )


async def _start_sessions_flow(bot, admin_id: int, chat_id: int, msg_id: int):
    """Mulai alur setup sessions — minta API ID."""
    _SESSION_SETUP[admin_id] = {
        "state":           SS_API_ID,
        "chat_id":         chat_id,
        "msg_id":          msg_id,
        "api_id":          0,
        "api_hash":        "",
        "phone":           "",
        "pclient":         None,
        "phone_code_hash": "",
    }
    text = (
        f"<u><b>🔗 SETUP SESSIONS — Langkah 1/4</b></u>\n\n"
        f"<blockquote>"
        f"<b>📱 Masukkan API ID kamu:</b>\n\n"
        f"API ID bisa didapatkan di:\n"
        f"<a href='https://my.telegram.org'>my.telegram.org</a> → API development tools\n\n"
        f"<b>Format:</b> angka, contoh: <code>1234567</code>"
        f"</blockquote>"
    )
    await bot.edit_message_text(
        chat_id=chat_id, message_id=msg_id,
        text=text, parse_mode=ParseMode.HTML,
        reply_markup=kb_sessions_cancel(),
    )


async def _handle_session_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Proses input text dari admin selama alur setup sessions."""
    user    = update.effective_user
    text    = (update.message.text or "").strip()
    state   = _SESSION_SETUP.get(user.id, {})
    chat_id = state.get("chat_id", user.id)
    msg_id  = state.get("msg_id", 0)

    async def edit(new_text: str, markup=None):
        if markup is None:
            markup = kb_sessions_cancel()
        try:
            await ctx.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=new_text, parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
        except Exception:
            pass

    # Hapus pesan input user agar chat rapi
    try:
        await update.message.delete()
    except Exception:
        pass

    current = state.get("state")

    # ── Langkah 1: API ID ─────────────────────────────────────────────────────
    if current == SS_API_ID:
        if not text.isdigit():
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Langkah 1/4</b></u>\n\n"
                f"<blockquote>❌ <b>API ID harus berupa angka!</b>\n\nCoba lagi:</blockquote>"
            )
            return
        _SESSION_SETUP[user.id]["api_id"]  = int(text)
        _SESSION_SETUP[user.id]["state"]   = SS_API_HASH
        await edit(
            f"<u><b>🔗 SETUP SESSIONS — Langkah 2/4</b></u>\n\n"
            f"<blockquote>"
            f"✅ <b>API ID tersimpan:</b> <code>{text}</code>\n\n"
            f"<b>🔑 Sekarang masukkan API Hash kamu:</b>\n\n"
            f"<b>Format:</b> string panjang hex, contoh:\n"
            f"<code>a1b2c3d4e5f6...</code>"
            f"</blockquote>"
        )

    # ── Langkah 2: API Hash ───────────────────────────────────────────────────
    elif current == SS_API_HASH:
        if len(text) < 16:
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Langkah 2/4</b></u>\n\n"
                f"<blockquote>❌ <b>API Hash terlalu pendek! Pastikan copy dengan benar.</b>\n\nCoba lagi:</blockquote>"
            )
            return
        _SESSION_SETUP[user.id]["api_hash"] = text
        _SESSION_SETUP[user.id]["state"]    = SS_PHONE
        await edit(
            f"<u><b>🔗 SETUP SESSIONS — Langkah 3/4</b></u>\n\n"
            f"<blockquote>"
            f"✅ <b>API Hash tersimpan</b>\n\n"
            f"<b>📱 Masukkan nomor HP kamu:</b>\n\n"
            f"<b>Format:</b> dengan kode negara, contoh:\n"
            f"<code>+6281234567890</code>"
            f"</blockquote>"
        )

    # ── Langkah 3: Nomor HP → kirim OTP ──────────────────────────────────────
    elif current == SS_PHONE:
        if not re.match(r"^\+?\d{8,15}$", text):
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Langkah 3/4</b></u>\n\n"
                f"<blockquote>❌ <b>Format nomor tidak valid!</b>\n\nContoh: <code>+6281234567890</code>\n\nCoba lagi:</blockquote>"
            )
            return

        _SESSION_SETUP[user.id]["phone"] = text
        api_id   = _SESSION_SETUP[user.id]["api_id"]
        api_hash = _SESSION_SETUP[user.id]["api_hash"]

        # Animasi loading
        anim_steps = [
            "🔗 <b>SETUP SESSIONS</b>\n\n<blockquote>⏳ <b>Menghubungkan ke server Telegram...</b></blockquote>",
            "🔗 <b>SETUP SESSIONS</b>\n\n<blockquote>🔄 <b>Memverifikasi API credentials...</b></blockquote>",
            "🔗 <b>SETUP SESSIONS</b>\n\n<blockquote>📡 <b>Membuat koneksi aman...</b></blockquote>",
            "🔗 <b>SETUP SESSIONS</b>\n\n<blockquote>📨 <b>Mengirim kode OTP ke nomor kamu...</b></blockquote>",
        ]
        for step in anim_steps:
            try:
                await ctx.bot.edit_message_text(
                    chat_id=chat_id, message_id=msg_id,
                    text=step, parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
            await asyncio.sleep(0.8)

        try:
            pclient = TelegramClient(StringSession(), api_id, api_hash)
            await pclient.connect()
            sent = await pclient.send_code_request(text)
            _SESSION_SETUP[user.id]["pclient"]         = pclient
            _SESSION_SETUP[user.id]["phone_code_hash"] = sent.phone_code_hash
            _SESSION_SETUP[user.id]["state"]           = SS_OTP

            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Langkah 4/4</b></u>\n\n"
                f"<blockquote>"
                f"✅ <b>OTP berhasil dikirim ke <code>{html.escape(text)}</code>!</b>\n\n"
                f"<b>🔢 Masukkan kode OTP yang kamu terima:</b>\n\n"
                f"<b>Format:</b> <code>12345</code>"
                f"</blockquote>"
            )
        except Exception as e:
            _SESSION_SETUP.pop(user.id, None)
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Gagal</b></u>\n\n"
                f"<blockquote>"
                f"❌ <b>Gagal terhubung ke Telegram!</b>\n\n"
                f"<b>Detail:</b> <code>{html.escape(str(e)[:200])}</code>\n\n"
                f"Periksa API ID dan API Hash kamu."
                f"</blockquote>",
                markup=kb_sessions_setup(),
            )

    # ── Langkah 4: OTP ───────────────────────────────────────────────────────
    elif current == SS_OTP:
        pclient         = state.get("pclient")
        phone           = state["phone"]
        phone_code_hash = state["phone_code_hash"]

        if not pclient:
            _SESSION_SETUP.pop(user.id, None)
            await edit("❌ Session expired. Silahkan mulai setup ulang.", markup=kb_sessions_setup())
            return

        try:
            await pclient.sign_in(phone, text, phone_code_hash=phone_code_hash)
            await _finalize_session(user.id, pclient, chat_id, msg_id, ctx)

        except PhoneCodeInvalidError:
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Langkah 4/4</b></u>\n\n"
                f"<blockquote>❌ <b>Kode OTP salah!</b>\n\nCoba masukkan kode OTP lagi:</blockquote>"
            )
        except PhoneCodeExpiredError:
            _SESSION_SETUP.pop(user.id, None)
            try:
                await pclient.disconnect()
            except Exception:
                pass
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Gagal</b></u>\n\n"
                f"<blockquote>❌ <b>Kode OTP sudah kadaluarsa!</b>\n\nSilahkan mulai setup ulang.</blockquote>",
                markup=kb_sessions_setup(),
            )
        except SessionPasswordNeededError:
            _SESSION_SETUP[user.id]["state"] = SS_2FA
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — 2FA</b></u>\n\n"
                f"<blockquote>"
                f"🔐 <b>Akun kamu menggunakan Two-Factor Authentication (2FA)!</b>\n\n"
                f"<b>🔑 Masukkan password 2FA kamu:</b>"
                f"</blockquote>"
            )
        except Exception as e:
            _SESSION_SETUP.pop(user.id, None)
            try:
                await pclient.disconnect()
            except Exception:
                pass
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — Gagal</b></u>\n\n"
                f"<blockquote>❌ <b>Error:</b> <code>{html.escape(str(e)[:200])}</code></blockquote>",
                markup=kb_sessions_setup(),
            )

    # ── Langkah 5: Password 2FA ───────────────────────────────────────────────
    elif current == SS_2FA:
        pclient = state.get("pclient")
        if not pclient:
            _SESSION_SETUP.pop(user.id, None)
            await edit("❌ Session expired. Silahkan mulai setup ulang.", markup=kb_sessions_setup())
            return
        try:
            await pclient.sign_in(password=text)
            await _finalize_session(user.id, pclient, chat_id, msg_id, ctx)
        except Exception as e:
            await edit(
                f"<u><b>🔗 SETUP SESSIONS — 2FA</b></u>\n\n"
                f"<blockquote>"
                f"❌ <b>Password 2FA salah!</b>\n\n"
                f"<b>Detail:</b> <code>{html.escape(str(e)[:150])}</code>\n\n"
                f"<b>Coba lagi:</b>"
                f"</blockquote>"
            )


async def _finalize_session(admin_id: int, pclient: TelegramClient,
                             chat_id: int, msg_id: int,
                             ctx: ContextTypes.DEFAULT_TYPE):
    """Simpan session yang berhasil dan tampilkan konfirmasi."""
    global _client
    session_str = pclient.session.save()
    api_id      = _SESSION_SETUP[admin_id]["api_id"]
    api_hash    = _SESSION_SETUP[admin_id]["api_hash"]

    _save_sessions({"api_id": api_id, "api_hash": api_hash, "session": session_str})

    # Reset global client supaya pakai credentials baru
    if _client:
        try:
            await _client.disconnect()
        except Exception:
            pass
        _client = None

    _SESSION_SETUP.pop(admin_id, None)

    sess_preview = session_str[:30] + "..." if len(session_str) > 30 else session_str
    text = (
        f"<u><b>🔗 SESSIONS</b></u>\n\n"
        f"<blockquote>"
        f"<b>✅ Sessions berhasil terhubung!</b>\n\n"
        f"🔑 <b>API ID</b>    »  <b><code>{api_id}</code></b>\n"
        f"🔐 <b>Session</b>  »  <b><code>{sess_preview}</code></b>\n\n"
        f"<b>Bot bisa digunakan dengan akurat ✅</b>"
        f"</blockquote>\n\n"
        f"<u><b>Tekan tombol di bawah untuk kembali ke menu utama:</b></u>"
    )
    try:
        await ctx.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=text, parse_mode=ParseMode.HTML,
            reply_markup=kb_sessions_done(),
        )
    except Exception:
        pass

    log.info(f"✅ Sessions berhasil dikonfigurasi oleh admin {admin_id}")

    # Sambungkan client baru
    try:
        await telethon_client()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  BOT HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    log.info(f"/start dari {user.id} ({user.full_name})")

    msg = await safe_send_message(
        ctx.bot, chat_id=chat_id,
        text=(
            f"<b>{'─'*3} {E_HOURGLASS} <u>MEMPROSES DATA</u> {E_HOURGLASS} {'─'*3}</b>\n\n"
            f"<blockquote><b>{'─'*4} {E_CLOCK} Sedang memproses profil Anda, mohon tunggu...</b></blockquote>"
        ),
        parse_mode=ParseMode.HTML,
    )
    try:
        uid      = user.id
        fname    = ((user.first_name or "") + " " + (user.last_name or "")).strip() or "Unknown"
        username = f"@{user.username}" if user.username else "Tidak Ada"
        cname, chex, cemoji = profile_color(uid)

        dc_id = dc_label(None)
        bio   = "-"
        photo = None
        try:
            cl = await telethon_client()
            if cl:
                lookup = f"@{user.username}" if user.username else user.id
                entity = await cl.get_entity(lookup)
                full   = await cl(GetFullUserRequest(entity))
                tguser = full.users[0]
                fu     = full.full_user
                dc_id  = dc_label(getattr(getattr(tguser, "photo", None), "dc_id", None))
                bio    = getattr(fu, "about", None) or "-"
                photo_buf = io.BytesIO()
                await cl.download_profile_photo(entity, file=photo_buf)
                photo_buf.seek(0)
                photo = photo_buf.read() or None
        except Exception as te:
            log.warning(f"Telethon lookup gagal (pakai data bot saja): {te}")

        d = {
            "type":       "user",
            "uid":        uid,
            "full_name":  fname,
            "username":   username,
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
        log.info(f"✅ Kartu dikirim ke {uid} ({fname})")

        if uid in ADMIN_IDS:
            sess_ok   = is_session_configured()
            admin_msg = await ctx.bot.send_message(
                chat_id, _LOADING_TEXT, parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(1.5)
            adm_fname, adm_dc, adm_total, adm_now = await _fetch_admin_panel_data(uid, user)
            await admin_msg.edit_text(
                _admin_panel_text(adm_fname, uid, adm_dc, adm_total, adm_now, session_ok=sess_ok),
                parse_mode=ParseMode.HTML, reply_markup=kb_admin(session_ok=sess_ok),
            )

    except Exception as e:
        log.error(f"cmd_start error: {e}")
        try:
            await msg.delete()
        except Exception:
            pass
        await ctx.bot.send_message(chat_id, _err_msg(str(e)), parse_mode=ParseMode.HTML)


async def cmd_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user    = update.effective_user
    text    = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Intersep input dari admin yang sedang di alur setup sessions
    if user.id in ADMIN_IDS and user.id in _SESSION_SETUP:
        await _handle_session_input(update, ctx)
        return

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

    _loading_text = (
        f"<b>{'─'*3} {E_HOURGLASS} <u>MEMPROSES DATA</u> {E_HOURGLASS} {'─'*3}</b>\n\n"
        f"<blockquote><b>{'─'*4} {E_CLOCK} Sedang memproses informasi target, mohon tunggu...</b></blockquote>"
    )
    try:
        msg = await update.message.reply_text(_loading_text, parse_mode=ParseMode.HTML)
    except Exception:
        msg = await update.message.reply_text(_strip_tgemoji(_loading_text), parse_mode=ParseMode.HTML)

    try:
        cl = await telethon_client()
        if not cl:
            await safe_edit_text(
                msg,
                text="⚠️ <b>Sessions belum dikonfigurasi!</b>\n\nGunakan /admin → 🟢 Sessions untuk setup.",
                parse_mode=ParseMode.HTML,
            )
            return

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
            await safe_send_message(
                ctx.bot, chat_id=chat_id, text=caption_chat(d),
                parse_mode=ParseMode.HTML, reply_markup=kb(),
            )
        else:
            await update.message.reply_text(
                _err_msg("Tipe entitas tidak dikenali."), parse_mode=ParseMode.HTML
            )

    except Exception as e:
        log.error(f"cmd_msg error: {e}")
        try:
            await safe_edit_text(msg, text=_err_msg(str(e)), parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text(
            "⛔ <b>Akses ditolak. Hanya admin!</b>", parse_mode=ParseMode.HTML
        )
        return
    msg = await update.message.reply_text(_LOADING_TEXT, parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    uid       = user.id
    sess_ok   = is_session_configured()
    fname, dc_str, total_users, now = await _fetch_admin_panel_data(uid, user)
    await msg.edit_text(
        _admin_panel_text(fname, uid, dc_str, total_users, now, session_ok=sess_ok),
        parse_mode=ParseMode.HTML, reply_markup=kb_admin(session_ok=sess_ok),
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ <b>Akses ditolak. Hanya admin!</b>", parse_mode=ParseMode.HTML)
        return
    total = len(get_all_user_ids())
    now   = datetime.now(timezone(timedelta(hours=8))).strftime("%d/%m/%Y %H:%M WITA")
    await update.message.reply_text(
        f"<u><b>📊 STATISTIK BOT</b></u>\n\n"
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
        f"<u><b>📢 PESAN DARI ADMIN</b></u>\n\n"
        f"<blockquote>{html.escape(text)}</blockquote>"
    )

    for uid in user_ids:
        try:
            await ctx.bot.send_message(uid, broadcast_text, parse_mode=ParseMode.HTML, reply_markup=kb())
            ok += 1
        except Exception:
            fail += 1

    await status_msg.edit_text(
        f"<u><b>✅ Broadcast selesai!</b></u>\n\n"
        f"<blockquote>"
        f"📨 <b>Terkirim</b>  »  <b>{ok}</b>\n"
        f"❌ <b>Gagal</b>     »  <b>{fail}</b>\n"
        f"👥 <b>Total</b>    »  <b>{total}</b>"
        f"</blockquote>",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cid = q.message.chat_id

    # ── Callbacks panel admin ─────────────────────────────────────────────────
    if q.data == "admin_back":
        if q.from_user.id not in ADMIN_IDS:
            await q.answer("⛔ Hanya admin!", show_alert=True)
            return
        uid    = q.from_user.id
        sess_ok = is_session_configured()
        fname, dc_str, total_users, now = await _fetch_admin_panel_data(uid, q.from_user)
        await q.edit_message_text(
            _admin_panel_text(fname, uid, dc_str, total_users, now, session_ok=sess_ok),
            parse_mode=ParseMode.HTML, reply_markup=kb_admin(session_ok=sess_ok),
        )
        return

    elif q.data == "admin_broadcast":
        if q.from_user.id not in ADMIN_IDS:
            await q.answer("⛔ Hanya admin!", show_alert=True)
            return
        await q.edit_message_text(
            f"<u><b>🔵 BROADCAST</b></u>\n\n"
            f"<blockquote>"
            f"Kirim pesan ke <b>seluruh pengguna bot</b> sekaligus.\n\n"
            f"📋 <b>Format perintah:</b>\n"
            f"<code>/broadcast pesan kamu di sini</code>\n\n"
            f"💡 <b>Contoh:</b>\n"
            f"<code>/broadcast Halo semua! Ada update baru nih 🔥</code>"
            f"</blockquote>",
            parse_mode=ParseMode.HTML, reply_markup=kb_admin_back(),
        )
        return

    elif q.data == "admin_stats":
        if q.from_user.id not in ADMIN_IDS:
            await q.answer("⛔ Hanya admin!", show_alert=True)
            return
        total = len(get_all_user_ids())
        now   = datetime.now(timezone(timedelta(hours=8))).strftime("%d/%m/%Y %H:%M WITA")
        await q.edit_message_text(
            f"<u><b>🟡 STATISTIK BOT</b></u>\n\n"
            f"<blockquote>"
            f"👥 <b>Total Pengguna</b>  »  <b>{total:,}</b>\n"
            f"🕐 <b>Waktu Sekarang</b>  »  <b>{now}</b>"
            f"</blockquote>",
            parse_mode=ParseMode.HTML, reply_markup=kb_admin_back(),
        )
        return

    # ── Sessions callbacks ────────────────────────────────────────────────────
    elif q.data == "admin_sessions":
        if q.from_user.id not in ADMIN_IDS:
            await q.answer("⛔ Hanya admin!", show_alert=True)
            return
        sess_ok = is_session_configured()
        await q.edit_message_text(
            _sessions_page_text(sess_ok),
            parse_mode=ParseMode.HTML,
            reply_markup=kb_sessions_setup(),
            disable_web_page_preview=True,
        )
        return

    elif q.data == "sessions_start":
        if q.from_user.id not in ADMIN_IDS:
            await q.answer("⛔ Hanya admin!", show_alert=True)
            return
        await _start_sessions_flow(
            bot=ctx.bot,
            admin_id=q.from_user.id,
            chat_id=cid,
            msg_id=q.message.message_id,
        )
        return

    elif q.data == "sessions_cancel":
        if q.from_user.id not in ADMIN_IDS:
            await q.answer("⛔ Hanya admin!", show_alert=True)
            return
        state = _SESSION_SETUP.pop(q.from_user.id, {})
        pclient = state.get("pclient")
        if pclient:
            try:
                await pclient.disconnect()
            except Exception:
                pass
        sess_ok = is_session_configured()
        await q.edit_message_text(
            _sessions_page_text(sess_ok),
            parse_mode=ParseMode.HTML,
            reply_markup=kb_sessions_setup(),
            disable_web_page_preview=True,
        )
        return

    # ── Callback umum ─────────────────────────────────────────────────────────
    elif q.data == "help_user":
        text = (
            "📊 <b>Cara Cek User</b>\n\n"
            "Kirim salah satu ke bot ini:\n"
            "• <code>@username</code> — cek lewat username\n"
            "• <code>123456789</code> — cek lewat User ID\n\n"
            "<b>💡 Contoh:</b> ketik <code>@durov</code> lalu kirim."
        )
    elif q.data == "help_channel":
        text = (
            "📢 <b>Cara Cek Channel / Grup</b>\n\n"
            "Kirim salah satu ke bot ini:\n"
            "• <code>@namaChannel</code> — cek lewat username\n"
            "• Link invite: <code>https://t.me/+xxxx</code>\n\n"
            "<b>💡 Contoh:</b> ketik <code>@telegram</code> lalu kirim."
        )
    elif q.data == "myid":
        user = q.from_user
        cname, chex, cemoji = profile_color(user.id)
        fname = user.full_name or "Unknown"
        text  = (
            f"👤 <b>Info ID Kamu</b>\n\n"
            f"• <b>Nama:</b> {html.escape(fname)}\n"
            f"• <b>ID:</b> <code>{user.id}</code>\n"
            f"• <b>Username:</b> {'@' + user.username if user.username else '—'}\n"
            f"• <b>Warna Profil:</b> {cemoji} {cname}\n"
            f"• <b>Perkiraan Daftar:</b> {estimate_date(user.id)}\n"
            f"• <b>Info ID:</b> {id_info(user.id)}\n"
        )
        await ctx.bot.send_message(cid, text, parse_mode=ParseMode.HTML, reply_markup=kb())
        return
    else:
        text = "❓ Perintah tidak dikenal."

    await ctx.bot.send_message(cid, text, parse_mode=ParseMode.HTML, reply_markup=kb())


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP & ERROR
# ══════════════════════════════════════════════════════════════════════════════

async def on_startup(app):
    """Jalankan saat bot start: cek sessions, notif admin jika belum terhubung."""
    if is_session_configured():
        try:
            await telethon_client()
            log.info("✅ Telethon sessions aktif saat startup.")
        except Exception as e:
            log.error(f"Telethon startup error: {e}")
    else:
        log.warning("⚠️  Sessions belum dikonfigurasi. Notifikasi admin...")
        for admin_id in ADMIN_IDS:
            try:
                await app.bot.send_message(
                    admin_id,
                    f"<u><b>🤖 CekID Bot — Aktif!</b></u>\n\n"
                    f"<blockquote>"
                    f"⚠️ <b>Sessions belum terhubung!</b>\n\n"
                    f"Silahkan hubungkan sessions agar bot bisa bekerja secara penuh.\n\n"
                    f"Tekan tombol di bawah untuk memulai setup:"
                    f"</blockquote>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb_notify_sessions(),
                )
            except Exception as e:
                log.warning(f"Gagal notif admin {admin_id}: {e}")


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.error(f"Bot error: {ctx.error}")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        print("\n❌ BOT_TOKEN belum diisi di .env!\n")
        sys.exit(1)

    log.info("🤖 Memulai CekID Bot v2.0...")

    if not is_session_configured():
        log.warning("⚠️  Sessions belum dikonfigurasi. Bot aktif, tapi fitur cek akun belum tersedia.")
        log.warning("    Gunakan /admin → 🟢 Sessions untuk setup via bot.")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("admin",     cmd_admin))
    app.add_handler(CommandHandler("stats",     cmd_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(cmd_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_msg))
    app.add_error_handler(on_error)
    log.info("✅ Bot siap!\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
