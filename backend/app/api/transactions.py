"""Transaction (Transaksi) endpoints with Income/Expense/Transfer logic.

Per PRD Section 3.2:
- PEMASUKAN: Adds funds to target wallet
- PENGELUARAN: Deducts funds from source wallet
- TRANSFER: Atomic operation - deduct from source, add to target
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.models.schemas import TransaksiCreate, TransaksiResponse, TipeTransaksi
from app.services.sheets import sheets_service

router = APIRouter(prefix="/api/transactions", tags=["Transaksi (Transaction)"])


def _validate_transaction(data: TransaksiCreate):
    """Validate transaction data per PRD Section 6 Step 3 rules."""

    if data.tipe == TipeTransaksi.PEMASUKAN:
        if not data.id_dompet_tujuan:
            raise HTTPException(
                status_code=400,
                detail="PEMASUKAN memerlukan id_dompet_tujuan",
            )
        if not data.id_kategori:
            raise HTTPException(
                status_code=400,
                detail="PEMASUKAN memerlukan id_kategori",
            )
        # Validate wallet exists
        if sheets_service.get_dompet_by_id(data.id_dompet_tujuan) is None:
            raise HTTPException(status_code=400, detail="Dompet tujuan tidak valid")
        # Validate category exists and is correct type
        kat = sheets_service.get_kategori_by_id(data.id_kategori)
        if kat is None:
            raise HTTPException(status_code=400, detail="Kategori tidak valid")
        if kat["tipe"] != "PEMASUKAN":
            raise HTTPException(
                status_code=400,
                detail="Kategori harus bertipe PEMASUKAN untuk transaksi pemasukan",
            )

    elif data.tipe == TipeTransaksi.PENGELUARAN:
        if not data.id_dompet_asal:
            raise HTTPException(
                status_code=400,
                detail="PENGELUARAN memerlukan id_dompet_asal",
            )
        if not data.id_kategori:
            raise HTTPException(
                status_code=400,
                detail="PENGELUARAN memerlukan id_kategori",
            )
        if sheets_service.get_dompet_by_id(data.id_dompet_asal) is None:
            raise HTTPException(status_code=400, detail="Dompet asal tidak valid")
        kat = sheets_service.get_kategori_by_id(data.id_kategori)
        if kat is None:
            raise HTTPException(status_code=400, detail="Kategori tidak valid")
        if kat["tipe"] != "PENGELUARAN":
            raise HTTPException(
                status_code=400,
                detail="Kategori harus bertipe PENGELUARAN untuk transaksi pengeluaran",
            )

    elif data.tipe == TipeTransaksi.TRANSFER:
        if not data.id_dompet_asal or not data.id_dompet_tujuan:
            raise HTTPException(
                status_code=400,
                detail="TRANSFER memerlukan id_dompet_asal dan id_dompet_tujuan",
            )
        if data.id_dompet_asal == data.id_dompet_tujuan:
            raise HTTPException(
                status_code=400,
                detail="Dompet asal dan tujuan tidak boleh sama",
            )
        if sheets_service.get_dompet_by_id(data.id_dompet_asal) is None:
            raise HTTPException(status_code=400, detail="Dompet asal tidak valid")
        if sheets_service.get_dompet_by_id(data.id_dompet_tujuan) is None:
            raise HTTPException(status_code=400, detail="Dompet tujuan tidak valid")


@router.get("/", response_model=List[TransaksiResponse])
async def list_transactions(
    tipe: Optional[str] = Query(None, description="Filter by type: PEMASUKAN, PENGELUARAN, TRANSFER"),
    id_dompet: Optional[str] = Query(None, description="Filter by wallet ID"),
    periode: Optional[str] = Query(None, description="Filter by period (YYYY-MM)"),
    user: dict = Depends(get_current_user),
):
    """Get all transactions with optional filters."""
    transaksi_list = sheets_service.get_all_transaksi()

    # Apply filters
    if tipe:
        transaksi_list = [t for t in transaksi_list if t.get("tipe") == tipe]
    if id_dompet:
        transaksi_list = [
            t for t in transaksi_list
            if t.get("id_dompet_asal") == id_dompet or t.get("id_dompet_tujuan") == id_dompet
        ]
    if periode:
        transaksi_list = [
            t for t in transaksi_list if t.get("tanggal", "")[:7] == periode
        ]

    return [
        TransaksiResponse(
            id=t.get("id", ""),
            tanggal=t.get("tanggal", ""),
            tipe=t.get("tipe", ""),
            id_kategori=t.get("id_kategori") or None,
            id_dompet_asal=t.get("id_dompet_asal") or None,
            id_dompet_tujuan=t.get("id_dompet_tujuan") or None,
            nominal=float(t.get("nominal", 0)),
            catatan=t.get("catatan") or None,
            created_at=t.get("created_at", ""),
        )
        for t in transaksi_list
    ]


@router.get("/{id_transaksi}", response_model=TransaksiResponse)
async def get_transaction(id_transaksi: str, user: dict = Depends(get_current_user)):
    """Get a single transaction by ID."""
    t = sheets_service.get_transaksi_by_id(id_transaksi)
    if t is None:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    return TransaksiResponse(
        id=t.get("id", ""),
        tanggal=t.get("tanggal", ""),
        tipe=t.get("tipe", ""),
        id_kategori=t.get("id_kategori") or None,
        id_dompet_asal=t.get("id_dompet_asal") or None,
        id_dompet_tujuan=t.get("id_dompet_tujuan") or None,
        nominal=float(t.get("nominal", 0)),
        catatan=t.get("catatan") or None,
        created_at=t.get("created_at", ""),
    )


@router.post("/", response_model=TransaksiResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(data: TransaksiCreate, user: dict = Depends(get_current_user)):
    """Create a new transaction.

    Validates wallets and categories per PRD Section 6, Step 3.
    For TRANSFER type, this is an atomic operation (PRD Section 3.2.3).
    """
    _validate_transaction(data)

    tx_id = sheets_service.create_transaksi(
        tanggal=data.tanggal.isoformat(),
        tipe=data.tipe.value,
        id_kategori=data.id_kategori or "",
        id_dompet_asal=data.id_dompet_asal or "",
        id_dompet_tujuan=data.id_dompet_tujuan or "",
        nominal=data.nominal,
        catatan=data.catatan or "",
    )

    return TransaksiResponse(
        id=tx_id,
        tanggal=data.tanggal.isoformat(),
        tipe=data.tipe.value,
        id_kategori=data.id_kategori,
        id_dompet_asal=data.id_dompet_asal,
        id_dompet_tujuan=data.id_dompet_tujuan,
        nominal=data.nominal,
        catatan=data.catatan,
        created_at="",
    )


@router.delete("/{id_transaksi}", response_model=dict)
async def delete_transaction(id_transaksi: str, user: dict = Depends(get_current_user)):
    """Delete a transaction."""
    success = sheets_service.delete_transaksi(id_transaksi)
    if not success:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    return {"message": "Transaksi berhasil dihapus"}
