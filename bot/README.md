# CekID Bot 🤖

Bot Telegram untuk cek informasi profil pengguna, grup, dan channel.

---

## 🚀 Cara Menjalankan

### Di Pterodactyl Panel

1. **Upload** semua file ke folder server
2. **Salin** `.env.example` menjadi `.env`
3. **Isi** nilai di `.env`:
   ```
   BOT_TOKEN=token_dari_botfather
   TELETHON_API_ID=api_id_dari_my.telegram.org
   TELETHON_API_HASH=api_hash_dari_my.telegram.org
   TELETHON_SESSION=     ← kosongkan dulu
   ```
4. **Jalankan** bot → `python3 main.py`
5. **Ikuti setup interaktif** di console:
   - Masukkan nomor HP (format: +628xxx)
   - Masukkan kode OTP yang dikirim Telegram
   - Masukkan password 2FA jika ada
6. Session otomatis tersimpan ke `.env` — bot langsung jalan!

> **Selanjutnya**: cukup klik Start di panel, bot langsung jalan tanpa setup ulang.

---

### Di VPS / Lokal

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env, isi BOT_TOKEN, TELETHON_API_ID, TELETHON_API_HASH
python3 main.py
```

---

## ⚙️ Konfigurasi

| Variable | Keterangan |
|----------|-----------|
| `BOT_TOKEN` | Token dari [@BotFather](https://t.me/BotFather) |
| `TELETHON_API_ID` | API ID dari [my.telegram.org](https://my.telegram.org) |
| `TELETHON_API_HASH` | API Hash dari [my.telegram.org](https://my.telegram.org) |
| `TELETHON_SESSION` | Session string (diisi otomatis saat setup) |

---

## 📦 Dependencies

```
python-telegram-bot==21.11.1
telethon==1.38.1
Pillow==11.2.1
python-dotenv==1.1.1
```

---

## 🛠️ Fitur

- `/start` — Cek info profil sendiri + kartu profil
- Kirim `@username` / `user_id` / link t.me → Cek info target
- Support user, grup, supergroup, dan channel
- Custom emoji animasi (free pack, tampil untuk semua user)
