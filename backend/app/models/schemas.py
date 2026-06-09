"""Pydantic models/schemas for request and response validation."""

from datetime import date, datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


# --- Enums ---

class TipeKategori(str, Enum):
    PEMASUKAN = "PEMASUKAN"
    PENGELUARAN = "PENGELUARAN"


class TipeTransaksi(str, Enum):
    PEMASUKAN = "PEMASUKAN"
    PENGELUARAN = "PENGELUARAN"
    TRANSFER = "TRANSFER"


# --- Auth ---

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Dompet (Wallet) ---

class DompetCreate(BaseModel):
    nama_dompet: str = Field(..., min_length=1, max_length=100, examples=["GoPay"])
    saldo_awal: float = Field(..., ge=0, examples=[500000.0])


class DompetUpdate(BaseModel):
    nama_dompet: Optional[str] = Field(None, min_length=1, max_length=100)
    saldo_awal: Optional[float] = Field(None, ge=0)


class DompetResponse(BaseModel):
    id_dompet: str
    nama_dompet: str
    saldo_awal: float
    saldo_saat_ini: Optional[float] = None


# --- Kategori (Category) ---

class KategoriCreate(BaseModel):
    nama_kategori: str = Field(..., min_length=1, max_length=100, examples=["Makanan & Minuman"])
    tipe: TipeKategori


class KategoriUpdate(BaseModel):
    nama_kategori: Optional[str] = Field(None, min_length=1, max_length=100)
    tipe: Optional[TipeKategori] = None


class KategoriResponse(BaseModel):
    id_kategori: str
    nama_kategori: str
    tipe: str


# --- Anggaran (Budget) ---

class AnggaranCreate(BaseModel):
    periode: str = Field(..., pattern=r"^\d{4}-\d{2}$", examples=["2026-06"])
    id_kategori: str
    limit_anggaran: float = Field(..., gt=0, examples=[1500000.0])


class AnggaranUpdate(BaseModel):
    periode: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    id_kategori: Optional[str] = None
    limit_anggaran: Optional[float] = Field(None, gt=0)


class AnggaranResponse(BaseModel):
    id_anggaran: str
    periode: str
    id_kategori: str
    nama_kategori: Optional[str] = None
    limit_anggaran: float
    total_terpakai: Optional[float] = None
    sisa_anggaran: Optional[float] = None


# --- Transaksi (Transaction) ---

class TransaksiCreate(BaseModel):
    tanggal: date
    tipe: TipeTransaksi
    id_kategori: Optional[str] = None
    id_dompet_asal: Optional[str] = None
    id_dompet_tujuan: Optional[str] = None
    nominal: float = Field(..., gt=0)
    catatan: Optional[str] = Field(None, max_length=500)


class TransaksiResponse(BaseModel):
    id: str
    tanggal: str
    tipe: str
    id_kategori: Optional[str] = None
    id_dompet_asal: Optional[str] = None
    id_dompet_tujuan: Optional[str] = None
    nominal: float
    catatan: Optional[str] = None
    created_at: str


# --- Dashboard ---

class WalletSummary(BaseModel):
    id_dompet: str
    nama_dompet: str
    saldo: float


class BudgetSummary(BaseModel):
    id_kategori: str
    nama_kategori: str
    limit_anggaran: float
    total_terpakai: float
    sisa: float
    persentase_terpakai: float


class MonthlyTrend(BaseModel):
    periode: str
    total_pemasukan: float
    total_pengeluaran: float
    selisih: float


class DashboardResponse(BaseModel):
    total_saldo: float
    dompet_list: List[WalletSummary]
    anggaran_bulan_ini: List[BudgetSummary]
    tren_bulanan: List[MonthlyTrend]
