# Telegram Bot Setup Guide

Bot AI untuk mencatat transaksi keuangan melalui Telegram dengan natural language processing.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Setup Gemini API Key (Gratis!)

1. Buka: https://makersuite.google.com/app/apikey
2. Login dengan Google Account
3. Klik "Create API Key"
4. Copy API key yang didapat

### 3. Update .env File

Edit `backend/.env` dan isi:

```env
# Telegram Bot Token (dari BotFather)
TELEGRAM_BOT_TOKEN=your-actual-bot-token-here

# Google Gemini API Key (gratis dari makersuite)
GEMINI_API_KEY=your-actual-gemini-api-key-here

# Backend URL (default sudah ok)
TELEGRAM_BACKEND_URL=http://localhost:8000
```

### 4. Jalankan Backend API

```bash
cd backend
uvicorn main:app --reload
```

Backend harus running di port 8000.

### 5. Jalankan Telegram Bot

Buka terminal baru:

```bash
cd backend
python telegram_bot.py
```

## 📱 Cara Pakai Bot

### Login ke Bot

1. Buka Telegram dan cari bot Anda (nama yang didaftarkan di BotFather)
2. Klik `/start`
3. Login dengan akun web app:
   ```
   /login username password
   ```

### Catat Transaksi

Kirim pesan dengan bahasa natural:

**Pengeluaran:**
- "Beli kopi 25rb pakai GoPay"
- "Bayar parkir 5000 cash"
- "Makan siang 35ribu"

**Pemasukan:**
- "Gaji 5jt masuk ke BCA"
- "Dapat bonus 500rb"
- "Terima transfer 200ribu"

**Transfer:**
- "Transfer 100rb dari BCA ke GoPay"
- "Top up GoPay 50ribu dari BCA"
- "Isi ShopeePay 1jt dari BCA"

Bot akan:
1. Parse dengan AI
2. Tampilkan konfirmasi
3. Klik ✅ Simpan untuk menyimpan transaksi

### Perintah Lain

- `/saldo` - Cek saldo semua dompet
- `/help` - Bantuan & contoh
- `/logout` - Keluar

## 🔧 Troubleshooting

### Bot tidak merespons
- Pastikan backend API running (port 8000)
- Pastikan bot token benar
- Cek log terminal untuk error

### Parsing tidak akurat
- Gunakan format lebih jelas: nominal + kata kunci (beli/bayar/transfer)
- Sebutkan nama dompet yang sesuai dengan yang ada di web app
- Gemini AI gratis punya rate limit: 15 req/menit, 1500 req/hari

### Gagal menyimpan transaksi
- Pastikan dompet dan kategori sudah dibuat di web app
- Bot akan coba match nama dompet otomatis (partial match)
- Kategori akan dipilih otomatis berdasarkan tipe

## 🎯 Tips

1. **Nama dompet konsisten**: Gunakan nama yang sama dengan web app (GoPay, BCA, ShopeePay)
2. **Format angka fleksibel**: 
   - "25rb" = 25000
   - "2.5jt" = 2500000
   - "150ribu" = 150000
3. **Kategori otomatis**: Bot detect berdasarkan kata kunci
   - "kopi", "makan" → Makanan & Minuman
   - "parkir", "bensin" → Transportasi
   - "gaji" → Gaji

## 📊 Gemini API Quota (Free Tier)

- **Rate limit**: 15 requests per minute
- **Daily limit**: 1500 requests per day
- **Model**: gemini-pro (free)

Lebih dari cukup untuk penggunaan personal!

## 🔐 Keamanan

- JWT token disimpan in-memory (hilang saat bot restart)
- Tidak ada data sensitif yang dikirim ke Gemini (hanya teks transaksi)
- Password tidak disimpan oleh bot

## 🐛 Error Codes

- `401` - Token expired atau invalid → `/login` lagi
- `403` - Permission denied → Cek Google Sheets sharing
- `500` - Backend error → Cek log backend

## 📝 Pengembangan Lanjutan

Ide fitur tambahan:
- [ ] Recurring transactions (reminder)
- [ ] Budget alerts via Telegram
- [ ] Monthly summary report
- [ ] Voice message support
- [ ] Photo receipt parsing (OCR)
- [ ] Multi-user per Telegram account

Selamat mencatat transaksi! 🎉
