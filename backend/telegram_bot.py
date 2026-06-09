"""Telegram Bot for AI-powered transaction input.

Run this bot separately: python telegram_bot.py
"""

import os
import json
import asyncio
import httpx
from datetime import date
from typing import Dict, Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = os.getenv("PORT", "8000")
BACKEND_URL = os.getenv("TELEGRAM_BACKEND_URL", f"http://localhost:{PORT}")

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your-telegram-bot-token-here":
    raise ValueError("TELEGRAM_BOT_TOKEN tidak ditemukan di .env file!")

# Simple in-memory session storage
# Format: {telegram_user_id: {"token": jwt_token, "username": username}}
user_sessions: Dict[int, Dict] = {}

# Temporary transaction storage for confirmation
# Format: {telegram_user_id: {transaction_data}}
pending_transactions: Dict[int, Dict] = {}


def get_user_token(user_id: int) -> Optional[str]:
    """Get JWT token for authenticated user."""
    session = user_sessions.get(user_id)
    return session.get("token") if session else None


async def call_backend(endpoint: str, method: str = "GET", token: Optional[str] = None, data: Optional[Dict] = None):
    """Call backend API."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{BACKEND_URL}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = await client.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    welcome_message = f"""👋 Halo {user.first_name}!

Saya adalah bot AI untuk mencatat transaksi keuangan Anda.

🔐 **Login terlebih dahulu:**
`/login username password`

📝 **Cara pakai:**
Setelah login, kirim saja pesan transaksi dengan bahasa natural:
• "Beli kopi 25rb pakai GoPay"
• "Gaji 5jt masuk ke BCA"  
• "Transfer 100rb dari BCA ke GoPay"
• "Bayar listrik 150ribu"

🤖 **AI akan otomatis mendeteksi:**
✓ Jenis transaksi (pemasukan/pengeluaran/transfer)
✓ Nominal uang
✓ Kategori
✓ Dompet/akun

⌨️ **Perintah lain:**
/help - Bantuan & contoh
/saldo - Cek saldo dompet
/logout - Keluar

Silakan login untuk mulai mencatat! 🚀"""
    
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """📖 **Panduan Penggunaan**

**Format pesan transaksi:**

🔴 **Pengeluaran:**
• "Beli kopi 25000 pakai GoPay"
• "Bayar parkir 5rb cash"
• "Makan siang 35ribu pakai ShopeePay"

🟢 **Pemasukan:**
• "Gaji 5jt masuk ke Bank BCA"
• "Dapat bonus 500rb"
• "Terima transfer 200ribu ke GoPay"

🔵 **Transfer:**
• "Transfer 100rb dari BCA ke GoPay"
• "Top up GoPay 50ribu dari BCA"
• "Pindah 1jt dari ShopeePay ke BCA"

**Tips:**
✓ Gunakan "rb" untuk ribuan (25rb = 25000)
✓ Gunakan "jt" untuk jutaan (2jt = 2000000)
✓ Bot akan mendeteksi kategori otomatis
✓ Konfirmasi sebelum menyimpan

Ada pertanyaan? Hubungi admin! 💬"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command."""
    user_id = update.effective_user.id
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Format salah!\n\n"
            "Gunakan: `/login username password`\n"
            "Contoh: `/login john mypassword123`",
            parse_mode="Markdown"
        )
        return
    
    username, password = context.args
    
    try:
        # Call backend login API
        params = {"username": username, "password": password}
        form_data = "&".join([f"{k}={v}" for k, v in params.items()])
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/auth/login",
                content=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            result = response.json()
        
        # Store session
        user_sessions[user_id] = {
            "token": result["access_token"],
            "username": username
        }
        
        await update.message.reply_text(
            f"✅ Login berhasil!\n\n"
            f"Selamat datang, **{username}**!\n"
            f"Sekarang Anda bisa mulai mencatat transaksi.\n\n"
            f"Kirim pesan transaksi atau ketik /help untuk panduan.",
            parse_mode="Markdown"
        )
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            await update.message.reply_text(
                "❌ Login gagal!\n\n"
                "Username atau password salah.\n"
                "Coba lagi atau daftar akun baru di web app."
            )
        else:
            await update.message.reply_text(
                f"❌ Error: {e.response.text}"
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Terjadi kesalahan: {str(e)}"
        )


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logout command."""
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        username = user_sessions[user_id]["username"]
        del user_sessions[user_id]
        await update.message.reply_text(
            f"👋 Logout berhasil, {username}!\n\n"
            f"Ketik /login untuk masuk kembali."
        )
    else:
        await update.message.reply_text(
            "ℹ️ Anda belum login.\n\n"
            "Ketik /login username password"
        )


async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /saldo command - show wallet balances."""
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "🔐 Silakan login terlebih dahulu!\n\n"
            "Ketik: `/login username password`",
            parse_mode="Markdown"
        )
        return
    
    try:
        # Get dashboard data
        data = await call_backend("/api/dashboard/", token=token)
        
        total = data.get("total_saldo", 0)
        wallets = data.get("dompet_list", [])
        
        if not wallets:
            await update.message.reply_text(
                "ℹ️ Belum ada dompet terdaftar.\n\n"
                "Buat dompet baru di web app terlebih dahulu."
            )
            return
        
        message = f"💰 **Total Saldo: Rp {total:,.0f}**\n\n"
        message += "📊 **Rincian per Dompet:**\n"
        
        for wallet in wallets:
            name = wallet["nama_dompet"]
            balance = wallet["saldo"]
            message += f"├ {name}: Rp {balance:,.0f}\n"
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal mengambil data saldo: {str(e)}"
        )


async def handle_transaction_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language transaction input."""
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "🔐 Silakan login terlebih dahulu!\n\n"
            "Ketik: `/login username password`",
            parse_mode="Markdown"
        )
        return
    
    text = update.message.text
    
    # Import parser here to avoid circular dependency
    try:
        from app.services.ai_parser import parser, TransactionParser
        
        # Try AI parsing first
        parsed = None
        if parser:
            await update.message.reply_text("🤖 Sedang memproses dengan AI...")
            parsed = parser.parse_transaction(text)
        
        # If AI parsing failed or not available, use simple regex parser
        if not parsed:
            simple_parser = TransactionParser()
            parsed = simple_parser.parse_simple(text)
        
        if not parsed:
            await update.message.reply_text(
                "❌ Maaf, saya tidak bisa memahami transaksi tersebut.\n\n"
                "Contoh format yang benar:\n"
                "• Beli kopi 25rb pakai GoPay\n"
                "• Gaji 5jt masuk ke BCA\n"
                "• Transfer 100rb dari BCA ke GoPay\n\n"
                "Ketik /help untuk panduan lengkap."
            )
            return
        
        # Store pending transaction
        pending_transactions[user_id] = parsed
        
        # Format confirmation message
        tipe_emoji = {
            "PEMASUKAN": "🟢",
            "PENGELUARAN": "🔴",
            "TRANSFER": "🔵"
        }
        
        emoji = tipe_emoji.get(parsed["tipe"], "⚪")
        message = f"{emoji} **Transaksi Terdeteksi:**\n\n"
        message += f"├ Jenis: {parsed['tipe']}\n"
        message += f"├ Nominal: Rp {parsed['nominal']:,.0f}\n"
        
        if parsed.get("kategori"):
            message += f"├ Kategori: {parsed['kategori']}\n"
        if parsed.get("dompet_asal"):
            message += f"├ Dari: {parsed['dompet_asal']}\n"
        if parsed.get("dompet_tujuan"):
            message += f"├ Ke: {parsed['dompet_tujuan']}\n"
        if parsed.get("catatan"):
            message += f"└ Catatan: {parsed['catatan']}\n"
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Simpan", callback_data="save_transaction"),
                InlineKeyboardButton("❌ Batal", callback_data="cancel_transaction")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error saat memproses: {str(e)}\n\n"
            "Coba lagi atau hubungi admin."
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback from inline keyboard buttons."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    
    if not token:
        await query.edit_message_text("❌ Sesi Anda telah berakhir. Silakan login kembali.")
        return
    
    if query.data == "cancel_transaction":
        if user_id in pending_transactions:
            del pending_transactions[user_id]
        await query.edit_message_text("❌ Transaksi dibatalkan.")
        return
    
    if query.data == "save_transaction":
        if user_id not in pending_transactions:
            await query.edit_message_text("❌ Data transaksi tidak ditemukan.")
            return
        
        parsed = pending_transactions[user_id]
        
        try:
            # Get wallets and categories from backend
            wallets = await call_backend("/api/wallets/", token=token)
            categories = await call_backend("/api/categories/", token=token)
            
            # Try to match wallet names
            def find_wallet(name):
                if not name:
                    return None
                name_lower = name.lower()
                for w in wallets:
                    if name_lower in w["nama_dompet"].lower():
                        return w["id_dompet"]
                return None
            
            # Try to match category
            def find_category(name, tipe):
                # If name is provided, try exact/partial match first
                if name:
                    name_lower = name.lower()
                    for c in categories:
                        if c["tipe"] == tipe and name_lower in c["nama_kategori"].lower():
                            return c["id_kategori"]
                
                # If no name provided or no match, return first category of matching type
                for c in categories:
                    if c["tipe"] == tipe:
                        return c["id_kategori"]
                
                return None  # No categories of this type exist
            
            # Check if wallets exist
            if not wallets:
                await query.edit_message_text(
                    "❌ Belum ada dompet terdaftar!\n\n"
                    "Silakan buat dompet terlebih dahulu di web app:\n"
                    "1. Buka web app\n"
                    "2. Menu Dompet\n"
                    "3. Tambah dompet (GoPay, BCA, dll)\n\n"
                    "Setelah itu coba lagi."
                )
                return
            
            # Check if categories exist (needed for PENGELUARAN and PEMASUKAN)
            if not categories and parsed["tipe"] in ["PENGELUARAN", "PEMASUKAN"]:
                await query.edit_message_text(
                    "❌ Belum ada kategori terdaftar!\n\n"
                    "Silakan buat kategori terlebih dahulu di web app:\n"
                    "1. Buka web app\n"
                    "2. Menu Kategori\n"
                    "3. Tambah kategori (Makanan, Transport, dll)\n"
                    "4. Pilih tipe: PENGELUARAN atau PEMASUKAN\n\n"
                    "Setelah itu coba lagi."
                )
                return
            
            # Build transaction data
            transaction_data = {
                "tanggal": str(date.today()),
                "tipe": parsed["tipe"],
                "nominal": parsed["nominal"],
                "catatan": parsed.get("catatan"),
            }
            
            # Set wallet and category based on type
            wallet_id_asal = None
            wallet_id_tujuan = None
            
            if parsed["tipe"] == "PENGELUARAN":
                wallet_id_asal = find_wallet(parsed.get("dompet_asal"))
                transaction_data["id_kategori"] = find_category(parsed.get("kategori"), "PENGELUARAN")
                
                if not wallet_id_asal:
                    wallet_list = "\n".join([f"• {w['nama_dompet']}" for w in wallets])
                    await query.edit_message_text(
                        f"❌ Dompet tidak ditemukan!\n\n"
                        f"Anda sebutkan: '{parsed.get('dompet_asal') or '(tidak disebutkan)'}'\n\n"
                        f"Dompet yang tersedia:\n{wallet_list}\n\n"
                        f"Gunakan format: Beli kopi 25000 pakai NamaDompet"
                    )
                    return
                transaction_data["id_dompet_asal"] = wallet_id_asal
                
            elif parsed["tipe"] == "PEMASUKAN":
                wallet_id_tujuan = find_wallet(parsed.get("dompet_tujuan"))
                transaction_data["id_kategori"] = find_category(parsed.get("kategori"), "PEMASUKAN")
                
                if not wallet_id_tujuan:
                    wallet_list = "\n".join([f"• {w['nama_dompet']}" for w in wallets])
                    await query.edit_message_text(
                        f"❌ Dompet tidak ditemukan!\n\n"
                        f"Anda sebutkan: '{parsed.get('dompet_tujuan') or '(tidak disebutkan)'}'\n\n"
                        f"Dompet yang tersedia:\n{wallet_list}\n\n"
                        f"Gunakan format: Gaji 5jt masuk ke NamaDompet"
                    )
                    return
                transaction_data["id_dompet_tujuan"] = wallet_id_tujuan
                
            elif parsed["tipe"] == "TRANSFER":
                wallet_id_asal = find_wallet(parsed.get("dompet_asal"))
                wallet_id_tujuan = find_wallet(parsed.get("dompet_tujuan"))
                
                if not wallet_id_asal or not wallet_id_tujuan:
                    wallet_list = "\n".join([f"• {w['nama_dompet']}" for w in wallets])
                    await query.edit_message_text(
                        f"❌ Dompet tidak ditemukan!\n\n"
                        f"Dari: '{parsed.get('dompet_asal') or '(tidak disebutkan)'}'\n"
                        f"Ke: '{parsed.get('dompet_tujuan') or '(tidak disebutkan)'}'\n\n"
                        f"Dompet yang tersedia:\n{wallet_list}\n\n"
                        f"Gunakan format: Transfer 100rb dari Dompet1 ke Dompet2"
                    )
                    return
                transaction_data["id_dompet_asal"] = wallet_id_asal
                transaction_data["id_dompet_tujuan"] = wallet_id_tujuan
            
            # Save transaction
            result = await call_backend(
                "/api/transactions/",
                method="POST",
                token=token,
                data=transaction_data
            )
            
            # Clean up
            del pending_transactions[user_id]
            
            await query.edit_message_text(
                f"✅ **Transaksi berhasil disimpan!**\n\n"
                f"ID: {result['id']}\n"
                f"Nominal: Rp {parsed['nominal']:,.0f}\n\n"
                f"Ketik /saldo untuk cek saldo terbaru.",
                parse_mode="Markdown"
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json().get("detail", str(e))
            await query.edit_message_text(
                f"❌ Gagal menyimpan transaksi!\n\n"
                f"Error: {error_detail}\n\n"
                f"Pastikan dompet dan kategori sudah dibuat di web app."
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}"
            )


def main():
    """Run the bot."""
    print("🤖 Starting Telegram Bot...")
    print(f"📡 Backend URL: {BACKEND_URL}")
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("saldo", saldo_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_transaction_message
    ))
    
    # Start bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
