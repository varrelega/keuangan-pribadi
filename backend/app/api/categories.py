"""Category (Kategori) CRUD endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.schemas import KategoriCreate, KategoriResponse, KategoriUpdate
from app.services.sheets import sheets_service

router = APIRouter(prefix="/api/categories", tags=["Kategori (Category)"])


@router.get("/", response_model=List[KategoriResponse])
async def list_categories(user: dict = Depends(get_current_user)):
    """Get all categories."""
    return [
        KategoriResponse(
            id_kategori=k["id_kategori"],
            nama_kategori=k["nama_kategori"],
            tipe=k["tipe"],
        )
        for k in sheets_service.get_all_kategori()
    ]


@router.get("/{id_kategori}", response_model=KategoriResponse)
async def get_category(id_kategori: str, user: dict = Depends(get_current_user)):
    """Get a single category by ID."""
    k = sheets_service.get_kategori_by_id(id_kategori)
    if k is None:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    return KategoriResponse(
        id_kategori=k["id_kategori"],
        nama_kategori=k["nama_kategori"],
        tipe=k["tipe"],
    )


@router.post("/", response_model=KategoriResponse, status_code=status.HTTP_201_CREATED)
async def create_category(data: KategoriCreate, user: dict = Depends(get_current_user)):
    """Create a new category."""
    id_kategori = sheets_service.create_kategori(data.nama_kategori, data.tipe.value)
    return KategoriResponse(
        id_kategori=id_kategori,
        nama_kategori=data.nama_kategori,
        tipe=data.tipe.value,
    )


@router.put("/{id_kategori}", response_model=dict)
async def update_category(
    id_kategori: str, data: KategoriUpdate, user: dict = Depends(get_current_user)
):
    """Update a category."""
    tipe_val = data.tipe.value if data.tipe else None
    success = sheets_service.update_kategori(id_kategori, data.nama_kategori, tipe_val)
    if not success:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    return {"message": "Kategori berhasil diperbarui"}


@router.delete("/{id_kategori}", response_model=dict)
async def delete_category(id_kategori: str, user: dict = Depends(get_current_user)):
    """Delete a category."""
    success = sheets_service.delete_kategori(id_kategori)
    if not success:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    return {"message": "Kategori berhasil dihapus"}
