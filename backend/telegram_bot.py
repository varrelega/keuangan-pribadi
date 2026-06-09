import os
import json
import re
import httpx
from datetime import date
from typing import Dict, Optional
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = os.getenv("PORT", "8000")
BACKEND_URL = os.getenv("TELEGRAM_BACKEND_URL", f"http://localhost:{PORT}")

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your-telegram-bot-token-here":
    raise ValueError("TELEGRAM_BOT_TOKEN tidak ditemukan di .env file!")

user_sessions: Dict[int, Dict] = {}

# ─── Helpers ────────────────────────────────────────────

def get_token(user_id: int) -> Optional[str]:
    s = user_sessions.get(user_id)
    return s.get("token") if s else None


async def api(endpoint: str, method: str = "GET", token: Optional[str] = None, data: Optional[Dict] = None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as c:
        if method == "GET":
            r = await c.get(endpoint, headers=h)
        elif method == "POST":
            r = await c.post(endpoint, headers=h, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        r.raise_for_status()
        return r.json()


async def login_api(username: str, password: str) -> dict:
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as c:
        r = await c.post("/api/auth/login", data={"username": username, "password": password},
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
        r.raise_for_status()
        return r.json()


def format_idr(v):
    return f"Rp {v:,.0f}"


# ─── Commands ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Keuangan Pribadi*\n\n"
        "Kirim teks transaksi, saya catat otomatis!\n\n"
        "Contoh:\n"
        "`Beli kopi 25rb pakai GoPay`\n"
        "`Gaji 5jt masuk ke BCA`\n"
        "`Transfer 100rb dari BCA ke GoPay`\n\n"
        "🔐 Login: `/login username password`\n"
        "ℹ️ /help - panduan",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Bantuan*\n\n"
        "`/start` - mulai bot\n"
        "`/login user pass` - login\n"
        "`/logout` - keluar\n"
        "`/saldo` - cek semua saldo\n\n"
        "*Contoh transaksi:*\n"
        "• Beli kopi 25rb pakai GoPay\n"
        "• Gaji 5jt masuk ke BCA\n"
        "• Transfer 100rb dari BCA ke GoPay\n"
        "• Bayar parkir 5rb cash\n"
        "• Service motor 200rb",
        parse_mode="Markdown"
    )


async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Format: `/login username password`", parse_mode="Markdown")
        return
    try:
        resp = await login_api(args[0], args[1])
        user_sessions[update.effective_user.id] = {"token": resp["access_token"], "username": args[0]}
        await update.message.reply_text(f"✅ Login berhasil! Selamat datang, {args[0]}.")
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", "Login gagal")
        await update.message.reply_text(f"❌ {detail}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def cmd_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_sessions:
        del user_sessions[uid]
        await update.message.reply_text("👋 Logout berhasil.")
    else:
        await update.message.reply_text("ℹ️ Anda belum login.")


async def cmd_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    token = get_token(uid)
    if not token:
        await update.message.reply_text("🔐 Login dulu: `/login username password`", parse_mode="Markdown")
        return
    try:
        data = await api("/api/dashboard/", token=token)
        wallets = data.get("dompet_list", [])
        if not wallets:
            await update.message.reply_text("ℹ️ Belum ada dompet.")
            return
        msg = f"💰 *Total: {format_idr(data['total_saldo'])}*\n\n"
        for w in wallets:
            msg += f"├ {w['nama_dompet']}: {format_idr(w['saldo'])}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)[:100]}")


# ─── AI Parser ────────────────────────────────────────────

def parse_with_ai(text: str, categories: list = None, wallets: list = None) -> Optional[dict]:
    try:
        from app.services.ai_parser import parser
        if parser:
            return parser.parse_transaction(text, categories, wallets)
    except Exception:
        pass
    return None


def parse_with_regex(text: str) -> Optional[dict]:
    """Fallback regex parser."""
    tl = text.lower()

    tipe = None
    if any(w in tl for w in ["beli", "bayar", "buat", "untuk", "keluar", "service", "servis",
                               "bengkel", "ganti", "perbaiki", "makan", "minum", "kopi", "jajan",
                               "bensin", "parkir", "tol", "pulsa", "kuota", "langganan",
                               "sewa", "biaya", "ongkir", "ongkos", "belanja", "sembako"]):
        tipe = "PENGELUARAN"
    elif any(w in tl for w in ["dapat", "terima", "gaji", "masuk", "pendapatan", "bonus",
                                "hasil", "komisi", "refund", "cashback", "kiriman"]):
        tipe = "PEMASUKAN"
    elif any(w in tl for w in ["transfer", "kirim", "pindah", "top up", "topup", "isi"]):
        tipe = "TRANSFER"
    if not tipe:
        return None

    nominal = None
    for pat, mul in [(r'(\d+(?:\.\d+)?)\s*(?:jt|juta)', 1000000),
                     (r'(\d+(?:\.\d+)?)\s*(?:rb|ribu)', 1000),
                     (r'(\d{3,})', 1)]:
        m = re.search(pat, tl)
        if m:
            nominal = float(m.group(1)) * mul
            break
    if not nominal:
        return None

    dompet_asal = None
    dompet_tujuan = None

    m = re.search(r'(?:pakai|pake|dengan|gunakan)\s+([A-Za-z][\w\s]*?)(?:\s+[0-9]|\s*$)', tl)
    if m:
        wm = re.search(re.escape(m.group(1).strip()), text, re.I)
        if wm:
            dompet_asal = wm.group(0).strip()

    m = re.search(r'dari\s+([A-Za-z][\w\s]*?)(?:\s+ke|\s+untuk|\s+[0-9]|\s*$)', tl)
    if m:
        wm = re.search(re.escape(m.group(1).strip()), text, re.I)
        if wm:
            dompet_asal = wm.group(0).strip()

    m = re.search(r'(?:masuk\s+ke|ke)\s+([A-Za-z][\w\s]*?)(?:\s+[0-9]|\s*$)', tl)
    if m:
        wm = re.search(re.escape(m.group(1).strip()), text, re.I)
        if wm:
            dompet_tujuan = wm.group(0).strip()

    return {"tipe": tipe, "nominal": int(nominal), "kategori": None,
            "dompet_asal": dompet_asal, "dompet_tujuan": dompet_tujuan, "catatan": text}


def match_wallet(name: str, wallets: list) -> Optional[str]:
    if not name:
        return None
    nl = name.lower()
    for w in wallets:
        if nl in w["nama_dompet"].lower():
            return w["id_dompet"]
    return None


def match_category(name: str, tipe: str, categories: list) -> Optional[str]:
    if name:
        nl = name.lower()
        for c in categories:
            if c["tipe"] == tipe and nl in c["nama_kategori"].lower():
                return c["id_kategori"]
    for c in categories:
        if c["tipe"] == tipe:
            return c["id_kategori"]
    return None


# ─── Transaction Handler ─────────────────────────────────

def smart_match_category(name: str, tipe: str, categories: list) -> Optional[str]:
    """Try to match parsed category name to existing categories using keywords."""
    if not name:
        return None
    nl = name.lower()

    # Exact/partial match first
    for c in categories:
        if c["tipe"] == tipe and nl in c["nama_kategori"].lower():
            return c["id_kategori"]

    # Keyword mapping for common Indonesian expense categories
    keyword_map = {
        "makan": ["makan", "minum", "kopi", "jajan", "soto", "bakso", "nasi", "ayam", "sate",
                  "cafe", "restoran", "warung", "katering", "catering"],
        "transportasi": ["bensin", "parkir", "tol", "bengkel", "service", "servis", "spbu",
                         "bbm", "solar", "ganti oli", "tambah angin", "cuci motor", "cuci mobil",
                         "perbaiki", "perbaikan", "montir"],
        "belanja": ["belanja", "sembako", "sayur", "daging", "buah", "beras", "minyak goreng",
                    "indomaret", "alfamart", "supermarket"],
        "hiburan": ["nonton", "bioskop", "game", "steam", "netflix", "spotify", "youtube"],
        "tagihan": ["listrik", "air", "pdam", "pln", "bpjs", "pajak", "iuran"],
        "pulsa": ["pulsa", "kuota", "paket data"],
        "transportasi umum": ["gojek", "grab", "taxi", "taksi", "ojek", "bus", "transit", "krl",
                              "mrt", "lrt", "angkot"],
    }

    for default_name, keywords in keyword_map.items():
        if any(kw in nl for kw in keywords):
            for c in categories:
                if c["tipe"] == tipe and default_name in c["nama_kategori"].lower():
                    return c["id_kategori"]
            # Also try partial match on each word
            for c in categories:
                cn = c["nama_kategori"].lower()
                if c["tipe"] == tipe and any(kw in cn for kw in keywords):
                    return c["id_kategori"]

    # Fallback: use first category of this type
    for c in categories:
        if c["tipe"] == tipe:
            return c["id_kategori"]
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    token = get_token(uid)
    if not token:
        await update.message.reply_text("🔐 Login dulu: `/login username password`", parse_mode="Markdown")
        return

    text = update.message.text

    # Fetch wallets & categories first for matching
    try:
        wallets = await api("/api/wallets/", token=token)
        categories = await api("/api/categories/", token=token)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal ambil data: {str(e)[:100]}")
        return

    if not wallets:
        await update.message.reply_text("❌ Belum ada dompet! Buat di web app dulu.")
        return

    # Parse with AI (pass categories & wallets for context), fallback to regex
    parsed = parse_with_ai(text, categories, wallets)
    if not parsed:
        parsed = parse_with_regex(text)
    if not parsed:
        await update.message.reply_text(
            "❌ Tidak bisa memahami transaksi.\n"
            "Contoh: `Beli kopi 25rb pakai GoPay`",
            parse_mode="Markdown"
        )
        return

    try:
        tx = {"tanggal": str(date.today()), "tipe": parsed["tipe"], "nominal": parsed["nominal"],
              "catatan": parsed.get("catatan")}

        if parsed["tipe"] == "PENGELUARAN":
            wal = match_wallet(parsed.get("dompet_asal"), wallets)
            if not wal:
                await update.message.reply_text(
                    f"❌ Dompet '{parsed.get('dompet_asal','?')}' tidak dikenal.\n"
                    f"Tersedia: {', '.join(w['nama_dompet'] for w in wallets)}"
                )
                return
            tx["id_dompet_asal"] = wal
            kat = smart_match_category(parsed.get("kategori"), "PENGELUARAN", categories)
            if kat:
                tx["id_kategori"] = kat

        elif parsed["tipe"] == "PEMASUKAN":
            wal = match_wallet(parsed.get("dompet_tujuan"), wallets)
            if not wal:
                await update.message.reply_text(
                    f"❌ Dompet '{parsed.get('dompet_tujuan','?')}' tidak dikenal.\n"
                    f"Tersedia: {', '.join(w['nama_dompet'] for w in wallets)}"
                )
                return
            tx["id_dompet_tujuan"] = wal
            kat = smart_match_category(parsed.get("kategori"), "PEMASUKAN", categories)
            if kat:
                tx["id_kategori"] = kat

        elif parsed["tipe"] == "TRANSFER":
            a = match_wallet(parsed.get("dompet_asal"), wallets)
            b = match_wallet(parsed.get("dompet_tujuan"), wallets)
            if not a or not b:
                await update.message.reply_text(
                    f"❌ Dompet tidak dikenal.\n"
                    f"Tersedia: {', '.join(w['nama_dompet'] for w in wallets)}"
                )
                return
            tx["id_dompet_asal"] = a
            tx["id_dompet_tujuan"] = b

        if not tx.get("id_kategori") and parsed["tipe"] != "TRANSFER":
            await update.message.reply_text(
                f"❌ Tidak ada kategori '{parsed.get('kategori','')}' — buat kategori {parsed['tipe']} dulu di web app."
            )
            return

        result = await api("/api/transactions/", method="POST", token=token, data=tx)

        msg = f"✅ *Transaksi tersimpan!*\n"
        msg += f"│ {parsed['tipe']}: {format_idr(parsed['nominal'])}\n"
        if parsed.get("dompet_asal"):
            msg += f"│ Dari: {parsed['dompet_asal']}\n"
        if parsed.get("dompet_tujuan"):
            msg += f"│ Ke: {parsed['dompet_tujuan']}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", str(e))
        await update.message.reply_text(f"❌ Gagal simpan: {detail}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


# ─── Main ─────────────────────────────────────────────────

def main():
    print(f"🤖 Starting Telegram Bot (auto-save mode)...")
    print(f"📡 Backend: {BACKEND_URL}")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("logout", cmd_logout))
    app.add_handler(CommandHandler("saldo", cmd_saldo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot siap!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
