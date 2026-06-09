"""Telegram Bot for AI-powered transaction input with interactive selection."""

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

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = os.getenv("PORT", "8000")
BACKEND_URL = os.getenv("TELEGRAM_BACKEND_URL", f"http://localhost:{PORT}")

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your-telegram-bot-token-here":
    raise ValueError("TELEGRAM_BOT_TOKEN tidak ditemukan di .env file!")

user_sessions: Dict[int, Dict] = {}
pending_transactions: Dict[int, Dict] = {}


def get_user_token(user_id: int) -> Optional[str]:
    session = user_sessions.get(user_id)
    return session.get("token") if session else None


async def call_backend(endpoint: str, method: str = "GET", token: Optional[str] = None, data: Optional[Dict] = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
        if method == "GET":
            resp = await client.get(endpoint, headers=headers)
        elif method == "POST":
            resp = await client.post(endpoint, headers=headers, json=data)
        elif method == "PUT":
            resp = await client.put(endpoint, headers=headers, json=data)
        elif method == "DELETE":
            resp = await client.delete(endpoint, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        resp.raise_for_status()
        return resp.json()


def build_confirm_keyboard(parsed: dict, wallets: list, categories: list) -> InlineKeyboardMarkup:
    buttons = []

    tipe = parsed["tipe"]
    if tipe in ("PENGELUARAN", "PEMASUKAN"):
        kat_name = parsed.get("kategori") or "(pilih)"
        buttons.append([InlineKeyboardButton(f"Kategori: {kat_name}", callback_data="edit_kategori")])

    if tipe in ("PENGELUARAN", "TRANSFER"):
        asal_name = parsed.get("dompet_asal") or "(pilih)"
        buttons.append([InlineKeyboardButton(f"Dari: {asal_name}", callback_data="edit_dompet_asal")])

    if tipe in ("PEMASUKAN", "TRANSFER"):
        tuju_name = parsed.get("dompet_tujuan") or "(pilih)"
        buttons.append([InlineKeyboardButton(f"Ke: {tuju_name}", callback_data="edit_dompet_tujuan")])

    buttons.append([
        InlineKeyboardButton("✅ Simpan", callback_data="save_transaction"),
        InlineKeyboardButton("❌ Batal", callback_data="cancel_transaction"),
    ])
    return InlineKeyboardMarkup(buttons)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Halo! Saya bot pencatatan keuangan.*\n\n"
        "Saya bisa mencatat transaksi dari teks biasa.\n\n"
        "📝 *Contoh:*\n"
        "• `Beli kopi 25rb pakai GoPay`\n"
        "• `Gaji 5jt masuk ke BCA`\n"
        "• `Transfer 100rb dari BCA ke GoPay`\n\n"
        "🔐 *Login dulu ya:*\n"
        "`/login username password`\n\n"
        "Ketik /help untuk bantuan.",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Bantuan Bot Keuangan*\n\n"
        "*Perintah:*\n"
        "├ `/start` - Mulai bot\n"
        "├ `/login username password` - Login\n"
        "├ `/logout` - Keluar\n"
        "├ `/saldo` - Cek saldo\n"
        "├ `/help` - Bantuan ini\n\n"
        "*Contoh transaksi:*\n"
        "├ Beli kopi 25rb pakai GoPay\n"
        "├ Gaji 5jt masuk ke BCA\n"
        "├ Transfer 100rb dari BCA ke GoPay\n"
        "├ Bayar parkir 5rb cash\n"
        "├ Top up ShopeePay 50rb dari BCA\n\n"
        "Tips: Setelah AI deteksi, Anda bisa ganti kategori/dompet dengan tap tombol.",
        parse_mode="Markdown"
    )


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Format: `/login username password`",
            parse_mode="Markdown"
        )
        return

    username, password = args[0], args[1]

    try:
        resp = await call_backend(
            "/api/auth/login",
            method="POST",
            data={"username": username, "password": password},
        )
        user_sessions[user_id] = {
            "token": resp["access_token"],
            "username": username,
        }
        await update.message.reply_text(
            f"✅ Login berhasil! Selamat datang, {username}!\n\n"
            "Sekarang kirim teks transaksi untuk dicatat."
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", "Login gagal")
        await update.message.reply_text(f"❌ {detail}")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal login: {str(e)}")


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        username = user_sessions[user_id]["username"]
        del user_sessions[user_id]
        await update.message.reply_text(f"👋 Logout berhasil, {username}!")
    else:
        await update.message.reply_text("ℹ️ Anda belum login.")


async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    if not token:
        await update.message.reply_text("🔐 Silakan login dulu! `/login username password`", parse_mode="Markdown")
        return

    try:
        data = await call_backend("/api/dashboard/", token=token)
        total = data.get("total_saldo", 0)
        wallets = data.get("dompet_list", [])

        if not wallets:
            await update.message.reply_text("ℹ️ Belum ada dompet. Buat di web app dulu.")
            return

        msg = f"💰 *Total Saldo: Rp {total:,.0f}*\n\n📊 *Rincian:*\n"
        for w in wallets:
            msg += f"├ {w['nama_dompet']}: Rp {w['saldo']:,.0f}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal ambil saldo: {str(e)}")


async def handle_transaction_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    if not token:
        await update.message.reply_text("🔐 Silakan login dulu! `/login username password`", parse_mode="Markdown")
        return

    text = update.message.text

    try:
        from app.services.ai_parser import parser, TransactionParser

        await update.message.reply_text("🤖 Memproses transaksi...")

        parsed = None
        if parser:
            parsed = parser.parse_transaction(text)

        if not parsed:
            simple_parser = TransactionParser()
            parsed = simple_parser.parse_simple(text)

        if not parsed:
            await update.message.reply_text(
                "❌ Tidak bisa memahami transaksi.\n\n"
                "Contoh: Beli kopi 25rb pakai GoPay\n"
                "Ketik /help untuk panduan."
            )
            return

        # Fetch wallets & categories for validation & keyboard
        wallets = await call_backend("/api/wallets/", token=token)
        categories = await call_backend("/api/categories/", token=token)

        pending_transactions[user_id] = parsed
        context.user_data["wallets_cache"] = wallets
        context.user_data["categories_cache"] = categories

        tipe_emoji = {"PEMASUKAN": "🟢", "PENGELUARAN": "🔴", "TRANSFER": "🔵"}
        emoji = tipe_emoji.get(parsed["tipe"], "⚪")
        msg = f"{emoji} *Transaksi Terdeteksi:*\n\n"
        msg += f"├ Jenis: {parsed['tipe']}\n"
        msg += f"├ Nominal: Rp {parsed['nominal']:,.0f}\n"
        if parsed.get("kategori"):
            msg += f"├ Kategori: {parsed['kategori']}\n"
        if parsed.get("dompet_asal"):
            msg += f"├ Dari: {parsed['dompet_asal']}\n"
        if parsed.get("dompet_tujuan"):
            msg += f"├ Ke: {parsed['dompet_tujuan']}\n"
        if parsed.get("catatan"):
            msg += f"└ Catatan: {parsed['catatan']}\n"

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=build_confirm_keyboard(parsed, wallets, categories)
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    token = get_user_token(user_id)

    if not token:
        await query.edit_message_text("❌ Sesi habis. Login ulang.")
        return

    data = query.data
    tipe = pending_transactions.get(user_id, {}).get("tipe", "")

    # === CANCEL ===
    if data == "cancel_transaction":
        pending_transactions.pop(user_id, None)
        await query.edit_message_text("❌ Transaksi dibatalkan.")
        return

    # === SAVE ===
    if data == "save_transaction":
        await save_transaction(query, user_id, token)
        return

    # === EDIT KATEGORI ===
    if data == "edit_kategori":
        await show_kategori_picker(query, user_id, tipe)
        return

    # === EDIT DOMPET ASAL ===
    if data == "edit_dompet_asal":
        await show_wallet_picker(query, user_id, "asal")
        return

    # === EDIT DOMPET TUJUAN ===
    if data == "edit_dompet_tujuan":
        await show_wallet_picker(query, user_id, "tujuan")
        return

    # === SELECT KATEGORI ===
    if data.startswith("select_kat:"):
        kat_id = data.split(":", 1)[1]
        categories = context.user_data.get("categories_cache", [])
        kat = next((c for c in categories if c["id_kategori"] == kat_id), None)
        if kat:
            pending_transactions[user_id]["kategori"] = kat["nama_kategori"]
            await refresh_confirmation(query, user_id)
        return

    # === SELECT WALLET ===
    if data.startswith("select_wallet:"):
        _, field, wal_id = data.split(":", 2)
        wallets = context.user_data.get("wallets_cache", [])
        wal = next((w for w in wallets if w["id_dompet"] == wal_id), None)
        if wal:
            if field == "asal":
                pending_transactions[user_id]["dompet_asal"] = wal["nama_dompet"]
            else:
                pending_transactions[user_id]["dompet_tujuan"] = wal["nama_dompet"]
            await refresh_confirmation(query, user_id)
        return

    # === BACK TO CONFIRMATION ===
    if data == "back_to_confirm":
        await refresh_confirmation(query, user_id)
        return

    # === PROMPT ADD KATEGORI ===
    if data == "prompt_add_kategori":
        context.user_data["awaiting_category"] = True
        context.user_data["awaiting_wallet"] = False
        await query.edit_message_text(
            "📝 *Tambah Kategori Baru*\n\n"
            "Ketik nama kategori yang ingin ditambahkan.\n"
            "Contoh: `Transportasi`, `Belanja`, `Hiburan`\n\n"
            "Atau ketik /batal untuk batal.",
            parse_mode="Markdown"
        )
        return

    # === PROMPT ADD WALLET ===
    if data == "prompt_add_wallet":
        context.user_data["awaiting_wallet"] = True
        context.user_data["awaiting_category"] = False
        await query.edit_message_text(
            "📝 *Tambah Dompet Baru*\n\n"
            "Ketik nama dompet yang ingin ditambahkan.\n"
            "Contoh: `GoPay`, `Bank BCA`, `Cash`\n\n"
            "Atau ketik /batal untuk batal.",
            parse_mode="Markdown"
        )
        return

    # === ADD KATEGORI (waiting for name) ===
    if data.startswith("add_kat:"):
        name = data.split(":", 1)[1]
        try:
            result = await call_backend(
                "/api/categories/",
                method="POST",
                token=token,
                data={"nama_kategori": name, "tipe": tipe},
            )
            pending_transactions[user_id]["kategori"] = name
            context.user_data["categories_cache"] = await call_backend("/api/categories/", token=token)
            await refresh_confirmation(query, user_id)
        except Exception as e:
            await query.edit_message_text(f"❌ Gagal buat kategori: {str(e)[:100]}")
        return

    # === ADD WALLET (waiting for name) ===
    if data.startswith("add_wallet:"):
        name = data.split(":", 1)[1]
        field = data.split(":", 2)[1] if ":" in data.split(":", 1)[1][:10] else "asal"
        try:
            result = await call_backend(
                "/api/wallets/",
                method="POST",
                token=token,
                data={"nama_dompet": name, "saldo_awal": 0},
            )
            if field == "edit_dompet_asal":
                pending_transactions[user_id]["dompet_asal"] = name
            else:
                pending_transactions[user_id]["dompet_tujuan"] = name
            context.user_data["wallets_cache"] = await call_backend("/api/wallets/", token=token)
            await refresh_confirmation(query, user_id)
        except Exception as e:
            await query.edit_message_text(f"❌ Gagal buat dompet: {str(e)[:100]}")
        return


async def show_kategori_picker(query, user_id, tipe):
    msg = "📂 *Pilih Kategori:*\n\n"
    buttons = []

    # Fetch categories
    try:
        categories = await call_backend(
            f"/api/categories/",
            token=get_user_token(user_id),
        )
        kat_list = [c for c in categories if c.get("tipe") == tipe]

        if kat_list:
            row = []
            for i, kat in enumerate(kat_list):
                btn = InlineKeyboardButton(kat["nama_kategori"], callback_data=f"select_kat:{kat['id_kategori']}")
                row.append(btn)
                if len(row) == 2 or i == len(kat_list) - 1:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)

        # Add "Tambah Baru" - ask user to type
        buttons.append([InlineKeyboardButton("➕ Tambah Kategori Baru", callback_data="prompt_add_kategori")])
    except Exception as e:
        msg += f"Error: {str(e)[:50]}"

    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_to_confirm")])

    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_wallet_picker(query, user_id, field):
    label = "Dari" if field == "asal" else "Ke"
    msg = f"💰 *Pilih Dompet ({label}):*\n\n"
    buttons = []

    try:
        wallets = await call_backend("/api/wallets/", token=get_user_token(user_id))

        if wallets:
            row = []
            for i, wal in enumerate(wallets):
                btn = InlineKeyboardButton(
                    f"{wal['nama_dompet']} (Rp {float(wal.get('saldo_awal',0)):,.0f})",
                    callback_data=f"select_wallet:{field}:{wal['id_dompet']}"
                )
                row.append(btn)
                if len(row) == 1 or i == len(wallets) - 1:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)

        buttons.append([InlineKeyboardButton("➕ Tambah Dompet Baru", callback_data="prompt_add_wallet")])
    except Exception as e:
        msg += f"Error: {str(e)[:50]}"

    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_to_confirm")])

    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def refresh_confirmation(query, user_id):
    parsed = pending_transactions.get(user_id)
    if not parsed:
        await query.edit_message_text("❌ Data transaksi tidak ditemukan.")
        return

    token = get_user_token(user_id)
    wallets = []
    categories = []
    if token:
        try:
            wallets = await call_backend("/api/wallets/", token=token)
            categories = await call_backend("/api/categories/", token=token)
        except:
            pass

    tipe_emoji = {"PEMASUKAN": "🟢", "PENGELUARAN": "🔴", "TRANSFER": "🔵"}
    emoji = tipe_emoji.get(parsed["tipe"], "⚪")
    msg = f"{emoji} *Konfirmasi Transaksi:*\n\n"
    msg += f"├ Jenis: {parsed['tipe']}\n"
    msg += f"├ Nominal: Rp {parsed['nominal']:,.0f}\n"
    if parsed.get("kategori"):
        msg += f"├ Kategori: {parsed['kategori']}\n"
    if parsed.get("dompet_asal"):
        msg += f"├ Dari: {parsed['dompet_asal']}\n"
    if parsed.get("dompet_tujuan"):
        msg += f"├ Ke: {parsed['dompet_tujuan']}\n"
    if parsed.get("catatan"):
        msg += f"└ Catatan: {parsed['catatan']}\n"

    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=build_confirm_keyboard(parsed, wallets, categories),
    )


async def save_transaction(query, user_id, token):
    if user_id not in pending_transactions:
        await query.edit_message_text("❌ Data transaksi tidak ditemukan.")
        return

    parsed = pending_transactions[user_id]

    try:
        wallets = await call_backend("/api/wallets/", token=token)
        categories = await call_backend("/api/categories/", token=token)

        def find_wallet_id(name):
            if not name:
                return None
            nl = name.lower()
            for w in wallets:
                if nl in w["nama_dompet"].lower():
                    return w["id_dompet"]
            return None

        def find_category_id(name, tipe):
            if name:
                nl = name.lower()
                for c in categories:
                    if c["tipe"] == tipe and nl in c["nama_kategori"].lower():
                        return c["id_kategori"]
            for c in categories:
                if c["tipe"] == tipe:
                    return c["id_kategori"]
            return None

        if not wallets:
            await query.edit_message_text("❌ Belum ada dompet! Buat di web app dulu.")
            return

        tx_data = {
            "tanggal": str(date.today()),
            "tipe": parsed["tipe"],
            "nominal": parsed["nominal"],
            "catatan": parsed.get("catatan"),
        }

        if parsed["tipe"] == "PENGELUARAN":
            wal_id = find_wallet_id(parsed.get("dompet_asal"))
            if not wal_id:
                wal_list = "\n".join(f"• {w['nama_dompet']}" for w in wallets)
                await query.edit_message_text(
                    f"❌ Dompet '{parsed.get('dompet_asal')}' tidak ditemukan!\n\n"
                    f"Tersedia:\n{wal_list}\n\n"
                    f"Ketik ulang dengan nama yang sesuai."
                )
                return
            tx_data["id_dompet_asal"] = wal_id
            tx_data["id_kategori"] = find_category_id(parsed.get("kategori"), "PENGELUARAN")

        elif parsed["tipe"] == "PEMASUKAN":
            wal_id = find_wallet_id(parsed.get("dompet_tujuan"))
            if not wal_id:
                wal_list = "\n".join(f"• {w['nama_dompet']}" for w in wallets)
                await query.edit_message_text(
                    f"❌ Dompet '{parsed.get('dompet_tujuan')}' tidak ditemukan!\n\n"
                    f"Tersedia:\n{wal_list}\n\n"
                    f"Ketik ulang dengan nama yang sesuai."
                )
                return
            tx_data["id_dompet_tujuan"] = wal_id
            tx_data["id_kategori"] = find_category_id(parsed.get("kategori"), "PEMASUKAN")

        elif parsed["tipe"] == "TRANSFER":
            asal_id = find_wallet_id(parsed.get("dompet_asal"))
            tuju_id = find_wallet_id(parsed.get("dompet_tujuan"))
            if not asal_id or not tuju_id:
                wal_list = "\n".join(f"• {w['nama_dompet']}" for w in wallets)
                await query.edit_message_text(
                    f"❌ Dompet tidak ditemukan!\n\n"
                    f"Tersedia:\n{wal_list}\n\n"
                    f"Gunakan tombol ✏️ untuk pilih dompet."
                )
                return
            tx_data["id_dompet_asal"] = asal_id
            tx_data["id_dompet_tujuan"] = tuju_id

        result = await call_backend("/api/transactions/", method="POST", token=token, data=tx_data)
        del pending_transactions[user_id]

        await query.edit_message_text(
            f"✅ *Transaksi berhasil disimpan!*\n\n"
            f"ID: {result['id']}\n"
            f"Nominal: Rp {parsed['nominal']:,.0f}\n\n"
            f"Ketik /saldo untuk cek saldo.",
            parse_mode="Markdown"
        )

    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", str(e))
        await query.edit_message_text(f"❌ Gagal simpan: {detail}")
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)[:200]}")


# Handle text input when user is adding a new category/wallet
async def handle_add_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    if not token:
        return

    text = update.message.text.strip()

    # Check if user was prompted to add a category
    if context.user_data.get("awaiting_category"):
        try:
            tipe = pending_transactions.get(user_id, {}).get("tipe", "PENGELUARAN")
            await call_backend(
                "/api/categories/",
                method="POST",
                token=token,
                data={"nama_kategori": text, "tipe": tipe},
            )
            pending_transactions[user_id]["kategori"] = text
            context.user_data["categories_cache"] = await call_backend("/api/categories/", token=token)
            context.user_data["awaiting_category"] = False
            await update.message.reply_text(f"✅ Kategori '{text}' berhasil dibuat!")
            # Send a new confirmation message
            parsed = pending_transactions.get(user_id)
            if parsed:
                wallets = await call_backend("/api/wallets/", token=token)
                categories = await call_backend("/api/categories/", token=token)
                tipe_emoji = {"PEMASUKAN": "🟢", "PENGELUARAN": "🔴", "TRANSFER": "🔵"}
                msg = f"{tipe_emoji.get(parsed['tipe'],'⚪')} *Konfirmasi Transaksi:*\n\n"
                msg += f"├ Jenis: {parsed['tipe']}\n├ Nominal: Rp {parsed['nominal']:,.0f}\n"
                if parsed.get("kategori"):
                    msg += f"├ Kategori: {parsed['kategori']}\n"
                if parsed.get("dompet_asal"):
                    msg += f"├ Dari: {parsed['dompet_asal']}\n"
                if parsed.get("dompet_tujuan"):
                    msg += f"├ Ke: {parsed['dompet_tujuan']}\n"
                await update.message.reply_text(msg, parse_mode="Markdown",
                    reply_markup=build_confirm_keyboard(parsed, wallets, categories))
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal buat kategori: {str(e)[:100]}")
        return

    if context.user_data.get("awaiting_wallet"):
        try:
            field = context.user_data.get("awaiting_wallet_field", "asal")
            result = await call_backend(
                "/api/wallets/",
                method="POST",
                token=token,
                data={"nama_dompet": text, "saldo_awal": 0},
            )
            if field == "asal":
                pending_transactions[user_id]["dompet_asal"] = text
            else:
                pending_transactions[user_id]["dompet_tujuan"] = text
            context.user_data["wallets_cache"] = await call_backend("/api/wallets/", token=token)
            context.user_data["awaiting_wallet"] = False
            await update.message.reply_text(f"✅ Dompet '{text}' berhasil dibuat!")
            parsed = pending_transactions.get(user_id)
            if parsed:
                wallets = await call_backend("/api/wallets/", token=token)
                categories = await call_backend("/api/categories/", token=token)
                tipe_emoji = {"PEMASUKAN": "🟢", "PENGELUARAN": "🔴", "TRANSFER": "🔵"}
                msg = f"{tipe_emoji.get(parsed['tipe'],'⚪')} *Konfirmasi Transaksi:*\n\n"
                msg += f"├ Jenis: {parsed['tipe']}\n├ Nominal: Rp {parsed['nominal']:,.0f}\n"
                if parsed.get("kategori"):
                    msg += f"├ Kategori: {parsed['kategori']}\n"
                if parsed.get("dompet_asal"):
                    msg += f"├ Dari: {parsed['dompet_asal']}\n"
                if parsed.get("dompet_tujuan"):
                    msg += f"├ Ke: {parsed['dompet_tujuan']}\n"
                await update.message.reply_text(msg, parse_mode="Markdown",
                    reply_markup=build_confirm_keyboard(parsed, wallets, categories))
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal buat dompet: {str(e)[:100]}")
        return


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get("awaiting_category") or context.user_data.get("awaiting_wallet"):
        await handle_add_input(update, context)
    else:
        await handle_transaction_message(update, context)


def main():
    print("🤖 Starting Telegram Bot with interactive selection...")
    print(f"📡 Backend URL: {BACKEND_URL}")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("saldo", saldo_command))

    application.add_handler(CallbackQueryHandler(handle_callback))

    # Handle text messages (both add input and transaction)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message,
    ))

    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
