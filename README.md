# 🤖 CekID Bot

Bot Telegram untuk mengecek informasi profil Telegram — ID, username, DC server, estimasi tanggal registrasi, warna profil, dan generate kartu profil bergaya cyberpunk.

---

## 📁 Struktur File

```
Bot-cekid/
├── main.py           ← Bot utama (all-in-one)
├── config.py         ← Konfigurasi & konstanta
├── requirements.txt  ← Dependensi Python
├── .env              ← Rahasia (buat sendiri dari .env.example)
└── .env.example      ← Template .env
```

---

## ⚙️ Cara Install di Pterodactyl

### 1. Persyaratan
- Python 3.10+
- pip
- Font DejaVu (opsional, untuk kartu profil):
  ```bash
  apt-get install -y fonts-dejavu-core
  ```

### 2. Upload file
Upload semua file ke panel Pterodactyl:
- `main.py`
- `config.py`
- `requirements.txt`
- `.env` (buat dari `.env.example`)

### 3. Install dependencies
Di console Pterodactyl, jalankan:
```bash
pip install -r requirements.txt
```

### 4. Isi file `.env`
```
BOT_TOKEN=token_bot_dari_BotFather
TELETHON_API_ID=api_id_dari_my.telegram.org
TELETHON_API_HASH=api_hash_dari_my.telegram.org
TELETHON_SESSION=
```

### 5. Generate Telethon Session
Di console Pterodactyl:
```bash
python3 main.py --gensession
```
Ikuti instruksi → masukkan nomor HP + OTP (+ 2FA jika ada).
Session akan otomatis tersimpan ke `.env`.

### 6. Jalankan bot
```bash
python3 main.py
```
Atau set startup command di Pterodactyl: `python3 main.py`

---

## 🔧 Konfigurasi Admin

Edit `config.py`, tambahkan ID Telegram kamu di `ADMIN_IDS`:
```python
ADMIN_IDS = [
    123456789,   # ID kamu
]
```

---

## 📌 Perintah Bot

| Perintah | Keterangan |
|----------|------------|
| `/start` | Tampilkan kartu profil kamu |
| `/stats` | Lihat statistik pengguna *(admin only)* |
| `/broadcast <pesan>` | Kirim pesan ke semua pengguna *(admin only)* |
| *(kirim ID/username)* | Cek info pengguna / grup / channel |

---

## 📦 Dependencies

```
python-telegram-bot==21.11.1
telethon==1.38.1
Pillow==11.2.1
python-dotenv==1.1.1
```

---

## 🔗 Link

- Store: [@botallz](https://t.me/botallz)
