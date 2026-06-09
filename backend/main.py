"""FastAPI application entry point.

Pencatatan Keuangan Pribadi (Cloud & Multi-Wallet)
Backend API with Google Sheets as database.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth, wallets, categories, budgets, transactions, dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "API Backend untuk Aplikasi Pencatatan Keuangan Pribadi. "
        "Menggunakan Google Sheets sebagai database cloud."
    ),
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
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
    """Initialize Google Sheets tabs and headers.

    Call this endpoint once to set up the spreadsheet structure.
    """
    from app.services.sheets import sheets_service

    try:
        sheets_service.initialize_spreadsheet()
        return {"message": "Spreadsheet berhasil diinisialisasi"}
    except Exception as e:
        return {"error": str(e)}
