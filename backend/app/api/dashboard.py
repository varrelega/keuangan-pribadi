"""Dashboard and analytics endpoints.

Per PRD Section 3.4:
- Interactive dashboard with total + per-wallet balances
- Monthly spending trends
- Budget vs actual spending comparison
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.schemas import (
    BudgetSummary,
    DashboardResponse,
    MonthlyTrend,
    WalletSummary,
)
from app.services.sheets import sheets_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(user: dict = Depends(get_current_user)):
    """Get full dashboard data: wallet balances, budget status, monthly trends."""

    # --- Wallet Summaries ---
    dompet_list = sheets_service.get_all_dompet()
    wallet_summaries = []
    total_saldo = 0.0

    for d in dompet_list:
        saldo = sheets_service.calculate_wallet_balance(d["id_dompet"])
        total_saldo += saldo
        wallet_summaries.append(
            WalletSummary(
                id_dompet=d["id_dompet"],
                nama_dompet=d["nama_dompet"],
                saldo=saldo,
            )
        )

    # --- Budget Summary for Current Month ---
    current_periode = datetime.now(timezone.utc).strftime("%Y-%m")
    anggaran_list = sheets_service.get_all_anggaran()
    budget_summaries = []

    for a in anggaran_list:
        if a.get("periode") != current_periode:
            continue
        id_kategori = a["id_kategori"]
        kategori = sheets_service.get_kategori_by_id(id_kategori)
        nama_kategori = kategori["nama_kategori"] if kategori else id_kategori
        limit_val = float(a.get("limit_anggaran", 0))
        total_terpakai = sheets_service.calculate_budget_usage(id_kategori, current_periode)
        sisa = limit_val - total_terpakai
        persen = (total_terpakai / limit_val * 100) if limit_val > 0 else 0

        budget_summaries.append(
            BudgetSummary(
                id_kategori=id_kategori,
                nama_kategori=nama_kategori,
                limit_anggaran=limit_val,
                total_terpakai=total_terpakai,
                sisa=sisa,
                persentase_terpakai=round(persen, 2),
            )
        )

    # --- Monthly Trends (last 6 months) ---
    transaksi_list = sheets_service.get_all_transaksi()
    monthly_data: dict = {}

    for tx in transaksi_list:
        periode = tx.get("tanggal", "")[:7]
        if not periode:
            continue
        if periode not in monthly_data:
            monthly_data[periode] = {"pemasukan": 0.0, "pengeluaran": 0.0}
        try:
            nominal = float(tx.get("nominal", 0))
        except (ValueError, TypeError):
            continue

        if tx.get("tipe") == "PEMASUKAN":
            monthly_data[periode]["pemasukan"] += nominal
        elif tx.get("tipe") == "PENGELUARAN":
            monthly_data[periode]["pengeluaran"] += nominal

    # Sort by period descending and take last 6
    sorted_periods = sorted(monthly_data.keys(), reverse=True)[:6]
    monthly_trends = [
        MonthlyTrend(
            periode=p,
            total_pemasukan=monthly_data[p]["pemasukan"],
            total_pengeluaran=monthly_data[p]["pengeluaran"],
            selisih=monthly_data[p]["pemasukan"] - monthly_data[p]["pengeluaran"],
        )
        for p in reversed(sorted_periods)
    ]

    return DashboardResponse(
        total_saldo=total_saldo,
        dompet_list=wallet_summaries,
        anggaran_bulan_ini=budget_summaries,
        tren_bulanan=monthly_trends,
    )
