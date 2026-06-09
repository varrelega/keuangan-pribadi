"""Wallet (Dompet) CRUD endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.schemas import DompetCreate, DompetResponse, DompetUpdate
from app.services.sheets import sheets_service

router = APIRouter(prefix="/api/wallets", tags=["Dompet (Wallet)"])


@router.get("/", response_model=List[DompetResponse])
async def list_wallets(user: dict = Depends(get_current_user)):
    """Get all wallets with current calculated balances."""
    dompet_list = sheets_service.get_all_dompet()
    result = []
    for d in dompet_list:
        saldo_saat_ini = sheets_service.calculate_wallet_balance(d["id_dompet"])
        result.append(
            DompetResponse(
                id_dompet=d["id_dompet"],
                nama_dompet=d["nama_dompet"],
                saldo_awal=float(d.get("saldo_awal", 0)),
                saldo_saat_ini=saldo_saat_ini,
            )
        )
    return result


@router.get("/{id_dompet}", response_model=DompetResponse)
async def get_wallet(id_dompet: str, user: dict = Depends(get_current_user)):
    """Get a single wallet by ID."""
    d = sheets_service.get_dompet_by_id(id_dompet)
    if d is None:
        raise HTTPException(status_code=404, detail="Dompet tidak ditemukan")
    saldo_saat_ini = sheets_service.calculate_wallet_balance(id_dompet)
    return DompetResponse(
        id_dompet=d["id_dompet"],
        nama_dompet=d["nama_dompet"],
        saldo_awal=float(d.get("saldo_awal", 0)),
        saldo_saat_ini=saldo_saat_ini,
    )


@router.post("/", response_model=DompetResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(data: DompetCreate, user: dict = Depends(get_current_user)):
    """Create a new wallet."""
    id_dompet = sheets_service.create_dompet(data.nama_dompet, data.saldo_awal)
    return DompetResponse(
        id_dompet=id_dompet,
        nama_dompet=data.nama_dompet,
        saldo_awal=data.saldo_awal,
        saldo_saat_ini=data.saldo_awal,
    )


@router.put("/{id_dompet}", response_model=dict)
async def update_wallet(
    id_dompet: str, data: DompetUpdate, user: dict = Depends(get_current_user)
):
    """Update wallet details."""
    success = sheets_service.update_dompet(id_dompet, data.nama_dompet, data.saldo_awal)
    if not success:
        raise HTTPException(status_code=404, detail="Dompet tidak ditemukan")
    return {"message": "Dompet berhasil diperbarui"}


@router.delete("/{id_dompet}", response_model=dict)
async def delete_wallet(id_dompet: str, user: dict = Depends(get_current_user)):
    """Delete a wallet."""
    success = sheets_service.delete_dompet(id_dompet)
    if not success:
        raise HTTPException(status_code=404, detail="Dompet tidak ditemukan")
    return {"message": "Dompet berhasil dihapus"}
