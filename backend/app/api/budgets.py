"""Budget (Anggaran) CRUD endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.schemas import AnggaranCreate, AnggaranResponse, AnggaranUpdate
from app.services.sheets import sheets_service

router = APIRouter(prefix="/api/budgets", tags=["Anggaran (Budget)"])


@router.get("/", response_model=List[AnggaranResponse])
async def list_budgets(
    periode: str = None,
    user: dict = Depends(get_current_user),
):
    """Get all budgets, optionally filtered by period (YYYY-MM)."""
    anggaran_list = sheets_service.get_all_anggaran()
    if periode:
        anggaran_list = [a for a in anggaran_list if a.get("periode") == periode]

    result = []
    for a in anggaran_list:
        id_kategori = a["id_kategori"]
        kategori = sheets_service.get_kategori_by_id(id_kategori)
        nama_kategori = kategori["nama_kategori"] if kategori else ""
        total_terpakai = sheets_service.calculate_budget_usage(id_kategori, a["periode"])
        limit_val = float(a.get("limit_anggaran", 0))
        result.append(
            AnggaranResponse(
                id_anggaran=a["id_anggaran"],
                periode=a["periode"],
                id_kategori=id_kategori,
                nama_kategori=nama_kategori,
                limit_anggaran=limit_val,
                total_terpakai=total_terpakai,
                sisa_anggaran=limit_val - total_terpakai,
            )
        )
    return result


@router.get("/{id_anggaran}", response_model=AnggaranResponse)
async def get_budget(id_anggaran: str, user: dict = Depends(get_current_user)):
    """Get a single budget by ID."""
    a = sheets_service.get_anggaran_by_id(id_anggaran)
    if a is None:
        raise HTTPException(status_code=404, detail="Anggaran tidak ditemukan")

    id_kategori = a["id_kategori"]
    kategori = sheets_service.get_kategori_by_id(id_kategori)
    nama_kategori = kategori["nama_kategori"] if kategori else ""
    total_terpakai = sheets_service.calculate_budget_usage(id_kategori, a["periode"])
    limit_val = float(a.get("limit_anggaran", 0))

    return AnggaranResponse(
        id_anggaran=a["id_anggaran"],
        periode=a["periode"],
        id_kategori=id_kategori,
        nama_kategori=nama_kategori,
        limit_anggaran=limit_val,
        total_terpakai=total_terpakai,
        sisa_anggaran=limit_val - total_terpakai,
    )


@router.post("/", response_model=AnggaranResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(data: AnggaranCreate, user: dict = Depends(get_current_user)):
    """Create a new budget entry."""
    # Validate category exists
    kategori = sheets_service.get_kategori_by_id(data.id_kategori)
    if kategori is None:
        raise HTTPException(status_code=400, detail="Kategori tidak ditemukan")
    if kategori["tipe"] != "PENGELUARAN":
        raise HTTPException(
            status_code=400,
            detail="Anggaran hanya dapat dibuat untuk kategori PENGELUARAN",
        )

    id_anggaran = sheets_service.create_anggaran(
        data.periode, data.id_kategori, data.limit_anggaran
    )
    return AnggaranResponse(
        id_anggaran=id_anggaran,
        periode=data.periode,
        id_kategori=data.id_kategori,
        nama_kategori=kategori["nama_kategori"],
        limit_anggaran=data.limit_anggaran,
        total_terpakai=0,
        sisa_anggaran=data.limit_anggaran,
    )


@router.put("/{id_anggaran}", response_model=dict)
async def update_budget(
    id_anggaran: str, data: AnggaranUpdate, user: dict = Depends(get_current_user)
):
    """Update a budget entry."""
    success = sheets_service.update_anggaran(
        id_anggaran, data.periode, data.id_kategori, data.limit_anggaran
    )
    if not success:
        raise HTTPException(status_code=404, detail="Anggaran tidak ditemukan")
    return {"message": "Anggaran berhasil diperbarui"}


@router.delete("/{id_anggaran}", response_model=dict)
async def delete_budget(id_anggaran: str, user: dict = Depends(get_current_user)):
    """Delete a budget entry."""
    success = sheets_service.delete_anggaran(id_anggaran)
    if not success:
        raise HTTPException(status_code=404, detail="Anggaran tidak ditemukan")
    return {"message": "Anggaran berhasil dihapus"}
