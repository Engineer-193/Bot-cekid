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
ADMIN_IDS = [
    8620738432,   # Owner utama
]

# DC Server Telegram + lokasi fisiknya
DC_MAP = {
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

# ─── Checkpoint ID → Tanggal Pembuatan Akun ───────────────────────────────────
# Data berdasarkan riset komunitas Telegram tracker & pola pertumbuhan ID.
# Semakin banyak checkpoint → interpolasi makin akurat.
KNOWN_IDS = [
    (1,               "2013-08-01"),  # Telegram diluncurkan
    (100_000_000,     "2014-02-01"),
    (500_000_000,     "2016-03-01"),
    (1_000_000_000,   "2018-08-01"),
    (1_500_000_000,   "2019-03-01"),
    (2_000_000_000,   "2019-11-01"),
    (2_500_000_000,   "2020-06-01"),
    (3_000_000_000,   "2020-12-01"),
    (3_500_000_000,   "2021-03-01"),  # Gelombang migrasi Signal
    (4_000_000_000,   "2021-06-01"),
    (4_500_000_000,   "2021-10-01"),  # Pemadaman WhatsApp
    (5_000_000_000,   "2022-02-01"),
    (5_500_000_000,   "2022-06-01"),
    (6_000_000_000,   "2022-09-01"),
    (6_500_000_000,   "2022-12-01"),
    (7_000_000_000,   "2023-03-01"),
    (7_500_000_000,   "2023-07-01"),
    (8_000_000_000,   "2023-11-01"),
    (8_500_000_000,   "2024-02-01"),
    (9_000_000_000,   "2024-06-01"),
    (9_500_000_000,   "2024-09-01"),
    (10_000_000_000,  "2025-01-01"),
    (10_500_000_000,  "2025-04-01"),
    (11_000_000_000,  "2025-07-01"),
    (11_500_000_000,  "2025-10-01"),
    (12_000_000_000,  "2026-01-01"),
    (12_500_000_000,  "2026-04-01"),
    (13_000_000_000,  "2026-08-01"),
]

MONTHS_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
