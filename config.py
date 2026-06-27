import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN         = os.environ.get("BOT_TOKEN", "")
TELETHON_API_ID   = int(os.environ.get("TELETHON_API_ID", "0") or "0")
TELETHON_API_HASH = os.environ.get("TELETHON_API_HASH", "")
TELETHON_SESSION  = os.environ.get("TELETHON_SESSION", "")

STORE_LINK = "https://t.me/botallz"

# ─── ADMIN IDS ────────────────────────────────────────────────────────────────
# Tambahkan ID admin di sini (pisah dengan koma jika lebih dari satu)
ADMIN_IDS = [
    8620738432,   # Owner utama
]

DC_MAP = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}

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
