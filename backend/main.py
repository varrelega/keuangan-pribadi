import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth, wallets, categories, budgets, transactions, dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if token and token != "your-telegram-bot-token-here":
        try:
            from telegram import Update
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
            from telegram_bot import (
                start_command, help_command, login_command, logout_command,
                saldo_command, handle_callback, handle_transaction_message,
            )

            global _bot_app
            _bot_app = (
                Application.builder().token(token).build()
            )
            _bot_app.add_handler(CommandHandler("start", start_command))
            _bot_app.add_handler(CommandHandler("help", help_command))
            _bot_app.add_handler(CommandHandler("login", login_command))
            _bot_app.add_handler(CommandHandler("logout", logout_command))
            _bot_app.add_handler(CommandHandler("saldo", saldo_command))
            _bot_app.add_handler(CallbackQueryHandler(handle_callback))
            _bot_app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_transaction_message
            ))

            await _bot_app.initialize()
            await _bot_app.start()
            await _bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram bot started")
        except Exception as e:
            logger.warning(f"Telegram bot not started: {e}")
    else:
        logger.info("TELEGRAM_BOT_TOKEN not set, skipping bot")

    yield

    if _bot_app:
        await _bot_app.updater.stop()
        await _bot_app.stop()
        await _bot_app.shutdown()


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "API Backend untuk Aplikasi Pencatatan Keuangan Pribadi. "
        "Menggunakan Google Sheets sebagai database cloud."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(wallets.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.app_title,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.post("/api/setup", tags=["Setup"])
async def setup_spreadsheet():
    from app.services.sheets import sheets_service

    try:
        sheets_service.initialize_spreadsheet()
        return {"message": "Spreadsheet berhasil diinisialisasi"}
    except Exception as e:
        return {"error": str(e)}
