# 📖 Cara Run & Cara Pakai — CekID Bot

Bot Telegram untuk mengecek informasi user, channel, dan grup Telegram secara lengkap — dilengkapi profile card bergambar.

---

## ⚙️ Kebutuhan Sebelum Mulai

| Kebutuhan | Cara Dapat |
|-----------|------------|
| **BOT_TOKEN** | Buat bot baru via [@BotFather](https://t.me/BotFather), lalu salin token |
| **TELETHON_API_ID** | Login ke [my.telegram.org](https://my.telegram.org) → API Development Tools |
| **TELETHON_API_HASH** | Sama seperti di atas, ada di halaman yang sama |
| **TELETHON_SESSION** | Di-generate otomatis saat pertama kali jalankan bot (lihat langkah di bawah) |

> ⚠️ **Jangan pernah share BOT_TOKEN atau API key kamu ke siapa pun!**

---

## 🚀 Cara Run (Pterodactyl / VPS / Lokal)

### Langkah 1 — Upload File

Upload 4 file ini ke server kamu:
```
main.py
config.py
requirements.txt
.env
```

### Langkah 2 — Isi File `.env`

Buat file `.env` (salin dari `.env.example`) lalu isi:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
TELETHON_API_ID=12345678
TELETHON_API_HASH=abcdef1234567890abcdef1234567890
TELETHON_SESSION=    ← dikosongkan dulu, diisi nanti setelah generate session
```

### Langkah 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Langkah 4 — Generate Telethon Session (WAJIB, sekali saja)

```bash
python3 main.py --gensession
```

Ikuti instruksinya:
1. Masukkan **nomor HP** (format internasional, contoh: `+628123456789`)
2. Telegram akan kirim **kode OTP** ke akun kamu
3. Masukkan kode OTP tersebut
4. Setelah selesai, salin **TELETHON_SESSION** yang muncul ke file `.env`

### Langkah 5 — Jalankan Bot

```bash
python3 main.py
```

Bot siap digunakan! ✅

---

## 🤖 Cara Pakai Bot

### `/start`
Menampilkan profile card kamu sendiri beserta informasi lengkap (ID, DC, warna profil, perkiraan tanggal daftar, dll).

### Cek User Lain
Kirim salah satu ke bot:
- **Username** → `@namauser`
- **User ID** → `123456789`

Bot akan membalas dengan profile card dan info lengkap user tersebut.

### Cek Channel / Grup
Kirim salah satu ke bot:
- **Username channel/grup** → `@namaChannel`
- **Link invite** → `https://t.me/+xxxxxxxxxxxx`
- **Channel ID** → `-100123456789`

### Tombol di Bot

| Tombol | Fungsi |
|--------|--------|
| 🏪 JOIN STORE KAMI | Buka halaman store / channel utama |
| 📊 Cara Cek User | Panduan cara cek user |
| 📢 Cara Cek Channel | Panduan cara cek channel/grup |
| 👑 Cek ID Saya | Tampilkan info ID kamu sendiri langsung |
| 📞 Hubungi Owner | Kontak owner / admin |

### `/stats` *(Admin Only)*
Melihat jumlah total user yang pernah pakai bot.

### `/broadcast` *(Admin Only)*
Kirim pesan ke semua user bot.
```
/broadcast Halo semua! Update terbaru telah tersedia.
```

---

## 🛠️ Konfigurasi Tambahan (`config.py`)

### Ganti Link Store
```python
STORE_LINK = "https://t.me/username_kamu"
```

### Tambah Admin
```python
ADMIN_IDS = [
    123456789,   # ID admin 1
    987654321,   # ID admin 2
]
```

---

## ❓ Troubleshooting

| Error | Solusi |
|-------|--------|
| `BOT_TOKEN belum diisi` | Isi `BOT_TOKEN` di file `.env` |
| `TELETHON_API_ID belum diisi` | Isi `TELETHON_API_ID` dan `TELETHON_API_HASH` di `.env` |
| `Telethon session tidak valid` | Jalankan ulang `python3 main.py --gensession` |
| `Profil akun diset privat` | Normal — profil target memang privat, tidak bisa diakses |
| `Target tidak ditemukan` | Username/ID salah atau akun sudah dihapus |
| `ModuleNotFoundError` | Jalankan `pip install -r requirements.txt` |

---

## 📦 Dependencies

```
python-telegram-bot==21.11.1
telethon==1.38.1
Pillow==11.2.1
python-dotenv==1.1.1
```

---

*CekID Bot — dibuat dengan ❤️*
