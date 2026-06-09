"""Google Sheets integration layer with in-memory caching.

Handles all CRUD operations against Google Sheets API v4.
Implements caching strategy per PRD Section 7:
- Read operations (GET) use in-memory cache with configurable TTL.
- Write operations (POST/PUT/DELETE) invalidate cache immediately.
- Row scanning by ID column for update/delete since Sheets has no auto-increment.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)

# Scopes required for read/write access
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Tab names matching PRD schema
TAB_DOMPET = "dompet"
TAB_KATEGORI = "kategori"
TAB_ANGGARAN = "anggaran"
TAB_TRANSAKSI = "transaksi"
TAB_USERS = "users"

# Headers per PRD Section 5
HEADERS = {
    TAB_DOMPET: ["id_dompet", "nama_dompet", "saldo_awal"],
    TAB_KATEGORI: ["id_kategori", "nama_kategori", "tipe"],
    TAB_ANGGARAN: ["id_anggaran", "periode", "id_kategori", "limit_anggaran"],
    TAB_TRANSAKSI: [
        "id", "tanggal", "tipe", "id_kategori",
        "id_dompet_asal", "id_dompet_tujuan", "nominal", "catatan", "created_at",
    ],
    TAB_USERS: ["username", "hashed_password", "created_at"],
}


class CacheEntry:
    """Simple TTL cache entry."""

    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.expires_at = time.time() + ttl

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class GoogleSheetsService:
    """Service for interacting with Google Sheets as a database layer."""

    def __init__(self):
        self._service = None
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_ttl = settings.cache_ttl

    @property
    def service(self):
        """Lazily initialize the Google Sheets API service."""
        if self._service is None:
            try:
                creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
                if creds_json:
                    creds_dict = json.loads(creds_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_dict, scopes=SCOPES
                    )
                else:
                    credentials = service_account.Credentials.from_service_account_file(
                        settings.google_service_account_file, scopes=SCOPES
                    )
                self._service = build("sheets", "v4", credentials=credentials)
            except Exception as e:
                logger.error(f"Failed to initialize Google Sheets service: {e}")
                raise RuntimeError(
                    "Gagal menginisialisasi koneksi Google Sheets. "
                    "Pastikan GOOGLE_SERVICE_ACCOUNT_JSON (env var) atau credentials.json valid."
                ) from e
        return self._service

    @property
    def spreadsheet_id(self) -> str:
        return settings.google_sheets_spreadsheet_id

    # ─── Cache Management ──────────────────────────────────────────

    def _get_cache(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            logger.debug(f"Cache HIT for key: {key}")
            return entry.data
        if entry:
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        self._cache[key] = CacheEntry(data, self._cache_ttl)

    def _invalidate_cache(self, tab_name: str):
        """Invalidate all cache entries for a given tab.

        Per PRD Section 7: data is re-fetched after any write operation.
        """
        keys_to_delete = [k for k in self._cache if k.startswith(tab_name)]
        for k in keys_to_delete:
            del self._cache[k]
        logger.debug(f"Cache invalidated for tab: {tab_name}")

    def _invalidate_all_cache(self):
        """Invalidate entire cache (used after cross-tab operations like transfers)."""
        self._cache.clear()
        logger.debug("Entire cache invalidated")

    # ─── Low-Level Sheet Operations ────────────────────────────────

    def _read_sheet(self, tab_name: str) -> List[List[str]]:
        """Read all rows from a tab. Returns list of rows (each row is a list of cell values)."""
        cache_key = f"{tab_name}:all"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{tab_name}!A:Z",
                )
                .execute()
            )
            rows = result.get("values", [])
            self._set_cache(cache_key, rows)
            return rows
        except Exception as e:
            logger.error(f"Error reading sheet '{tab_name}': {e}")
            raise

    def _append_row(self, tab_name: str, values: List[Any]):
        """Append a single row to a tab."""
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{tab_name}!A:Z",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [values]},
            ).execute()
            self._invalidate_cache(tab_name)
        except Exception as e:
            logger.error(f"Error appending to '{tab_name}': {e}")
            raise

    def _update_row(self, tab_name: str, row_index: int, values: List[Any]):
        """Update a specific row (1-indexed, row 1 = header)."""
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{tab_name}!A{row_index}:Z{row_index}",
                valueInputOption="USER_ENTERED",
                body={"values": [values]},
            ).execute()
            self._invalidate_cache(tab_name)
        except Exception as e:
            logger.error(f"Error updating row {row_index} in '{tab_name}': {e}")
            raise

    def _delete_row(self, tab_name: str, row_index: int):
        """Delete a specific row by shifting cells up.

        Per PRD Section 7: Backend scans rows by ID column before deletion.
        """
        try:
            # Get sheet ID for the tab
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            sheet_id = None
            for sheet in spreadsheet.get("sheets", []):
                if sheet["properties"]["title"] == tab_name:
                    sheet_id = sheet["properties"]["sheetId"]
                    break

            if sheet_id is None:
                raise ValueError(f"Tab '{tab_name}' not found in spreadsheet")

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    "requests": [
                        {
                            "deleteDimension": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "ROWS",
                                    "startIndex": row_index - 1,  # 0-indexed
                                    "endIndex": row_index,
                                }
                            }
                        }
                    ]
                },
            ).execute()
            self._invalidate_cache(tab_name)
        except Exception as e:
            logger.error(f"Error deleting row {row_index} in '{tab_name}': {e}")
            raise

    def _find_row_index(self, tab_name: str, id_column: int, id_value: str) -> Optional[int]:
        """Scan rows to find row index by ID value (per PRD Section 7 constraint).

        Returns 1-indexed row number (row 1 = header), or None if not found.
        """
        rows = self._read_sheet(tab_name)
        for i, row in enumerate(rows):
            if i == 0:  # skip header
                continue
            if len(row) > id_column and row[id_column] == id_value:
                return i + 1  # convert to 1-indexed
        return None

    def _rows_to_dicts(self, tab_name: str) -> List[Dict[str, str]]:
        """Convert sheet rows to list of dicts using headers."""
        rows = self._read_sheet(tab_name)
        if len(rows) < 2:  # only header or empty
            return []
        headers = rows[0]
        result = []
        for row in rows[1:]:
            record = {}
            for j, header in enumerate(headers):
                record[header] = row[j] if j < len(row) else ""
            result.append(record)
        return result

    # ─── Setup / Initialize Tabs ───────────────────────────────────

    def initialize_spreadsheet(self):
        """Ensure all required tabs exist with correct headers."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            existing_tabs = {
                s["properties"]["title"] for s in spreadsheet.get("sheets", [])
            }

            requests = []
            for tab_name in HEADERS:
                if tab_name not in existing_tabs:
                    requests.append({
                        "addSheet": {"properties": {"title": tab_name}}
                    })

            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"requests": requests},
                ).execute()

            # Set headers for each tab
            for tab_name, headers in HEADERS.items():
                rows = self._read_sheet(tab_name)
                if not rows:
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"{tab_name}!A1",
                        valueInputOption="RAW",
                        body={"values": [headers]},
                    ).execute()
                    self._invalidate_cache(tab_name)

            logger.info("Spreadsheet initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize spreadsheet: {e}")
            raise

    # ─── Dompet (Wallet) Operations ────────────────────────────────

    def get_all_dompet(self) -> List[Dict[str, str]]:
        return self._rows_to_dicts(TAB_DOMPET)

    def get_dompet_by_id(self, id_dompet: str) -> Optional[Dict[str, str]]:
        for d in self.get_all_dompet():
            if d.get("id_dompet") == id_dompet:
                return d
        return None

    def create_dompet(self, nama_dompet: str, saldo_awal: float) -> str:
        id_dompet = f"w-{uuid.uuid4().hex[:6]}"
        self._append_row(TAB_DOMPET, [id_dompet, nama_dompet, saldo_awal])
        return id_dompet

    def update_dompet(self, id_dompet: str, nama_dompet: Optional[str], saldo_awal: Optional[float]) -> bool:
        row_idx = self._find_row_index(TAB_DOMPET, 0, id_dompet)
        if row_idx is None:
            return False
        current = self.get_dompet_by_id(id_dompet)
        if current is None:
            return False
        new_nama = nama_dompet if nama_dompet is not None else current["nama_dompet"]
        new_saldo = saldo_awal if saldo_awal is not None else float(current["saldo_awal"])
        self._update_row(TAB_DOMPET, row_idx, [id_dompet, new_nama, new_saldo])
        return True

    def delete_dompet(self, id_dompet: str) -> bool:
        row_idx = self._find_row_index(TAB_DOMPET, 0, id_dompet)
        if row_idx is None:
            return False
        self._delete_row(TAB_DOMPET, row_idx)
        return True

    # ─── Kategori (Category) Operations ────────────────────────────

    def get_all_kategori(self) -> List[Dict[str, str]]:
        return self._rows_to_dicts(TAB_KATEGORI)

    def get_kategori_by_id(self, id_kategori: str) -> Optional[Dict[str, str]]:
        for k in self.get_all_kategori():
            if k.get("id_kategori") == id_kategori:
                return k
        return None

    def create_kategori(self, nama_kategori: str, tipe: str) -> str:
        id_kategori = f"kat-{uuid.uuid4().hex[:6]}"
        self._append_row(TAB_KATEGORI, [id_kategori, nama_kategori, tipe])
        return id_kategori

    def update_kategori(self, id_kategori: str, nama_kategori: Optional[str], tipe: Optional[str]) -> bool:
        row_idx = self._find_row_index(TAB_KATEGORI, 0, id_kategori)
        if row_idx is None:
            return False
        current = self.get_kategori_by_id(id_kategori)
        if current is None:
            return False
        new_nama = nama_kategori if nama_kategori is not None else current["nama_kategori"]
        new_tipe = tipe if tipe is not None else current["tipe"]
        self._update_row(TAB_KATEGORI, row_idx, [id_kategori, new_nama, new_tipe])
        return True

    def delete_kategori(self, id_kategori: str) -> bool:
        row_idx = self._find_row_index(TAB_KATEGORI, 0, id_kategori)
        if row_idx is None:
            return False
        self._delete_row(TAB_KATEGORI, row_idx)
        return True

    # ─── Anggaran (Budget) Operations ──────────────────────────────

    def get_all_anggaran(self) -> List[Dict[str, str]]:
        return self._rows_to_dicts(TAB_ANGGARAN)

    def get_anggaran_by_id(self, id_anggaran: str) -> Optional[Dict[str, str]]:
        for a in self.get_all_anggaran():
            if a.get("id_anggaran") == id_anggaran:
                return a
        return None

    def create_anggaran(self, periode: str, id_kategori: str, limit_anggaran: float) -> str:
        id_anggaran = f"bg-{uuid.uuid4().hex[:6]}"
        self._append_row(TAB_ANGGARAN, [id_anggaran, periode, id_kategori, limit_anggaran])
        return id_anggaran

    def update_anggaran(
        self, id_anggaran: str,
        periode: Optional[str], id_kategori: Optional[str], limit_anggaran: Optional[float]
    ) -> bool:
        row_idx = self._find_row_index(TAB_ANGGARAN, 0, id_anggaran)
        if row_idx is None:
            return False
        current = self.get_anggaran_by_id(id_anggaran)
        if current is None:
            return False
        new_periode = periode if periode is not None else current["periode"]
        new_kategori = id_kategori if id_kategori is not None else current["id_kategori"]
        new_limit = limit_anggaran if limit_anggaran is not None else float(current["limit_anggaran"])
        self._update_row(TAB_ANGGARAN, row_idx, [id_anggaran, new_periode, new_kategori, new_limit])
        return True

    def delete_anggaran(self, id_anggaran: str) -> bool:
        row_idx = self._find_row_index(TAB_ANGGARAN, 0, id_anggaran)
        if row_idx is None:
            return False
        self._delete_row(TAB_ANGGARAN, row_idx)
        return True

    # ─── Users Operations ──────────────────────────────────────────

    def get_user(self, username: str) -> Optional[Dict[str, str]]:
        for u in self._rows_to_dicts(TAB_USERS):
            if u.get("username") == username:
                return u
        return None

    def create_user(self, username: str, hashed_password: str):
        self._append_row(TAB_USERS, [username, hashed_password, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")])

    # ─── Transaksi (Transaction) Operations ────────────────────────

    def get_all_transaksi(self) -> List[Dict[str, str]]:
        return self._rows_to_dicts(TAB_TRANSAKSI)

    def get_transaksi_by_id(self, id_transaksi: str) -> Optional[Dict[str, str]]:
        for t in self.get_all_transaksi():
            if t.get("id") == id_transaksi:
                return t
        return None

    def create_transaksi(
        self,
        tanggal: str,
        tipe: str,
        id_kategori: str,
        id_dompet_asal: str,
        id_dompet_tujuan: str,
        nominal: float,
        catatan: str,
    ) -> str:
        tx_id = f"tx-{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._append_row(
            TAB_TRANSAKSI,
            [tx_id, tanggal, tipe, id_kategori, id_dompet_asal, id_dompet_tujuan, nominal, catatan, created_at],
        )
        # Invalidate all caches since transactions affect wallet balances
        self._invalidate_all_cache()
        return tx_id

    def delete_transaksi(self, id_transaksi: str) -> bool:
        row_idx = self._find_row_index(TAB_TRANSAKSI, 0, id_transaksi)
        if row_idx is None:
            return False
        self._delete_row(TAB_TRANSAKSI, row_idx)
        self._invalidate_all_cache()
        return True

    # ─── Computed Balances ─────────────────────────────────────────

    def calculate_wallet_balance(self, id_dompet: str) -> float:
        """Calculate current balance: saldo_awal + income - expenses.

        Per PRD Section 5A: Saldo Awal + Total Pemasukan - Total Pengeluaran.
        """
        dompet = self.get_dompet_by_id(id_dompet)
        if dompet is None:
            return 0.0

        saldo_awal = float(dompet.get("saldo_awal", 0))
        transaksi_list = self.get_all_transaksi()

        total_masuk = 0.0
        total_keluar = 0.0

        for tx in transaksi_list:
            try:
                nominal = float(tx.get("nominal", 0))
            except (ValueError, TypeError):
                continue

            # Income to this wallet
            if tx.get("id_dompet_tujuan") == id_dompet and tx.get("tipe") in ("PEMASUKAN", "TRANSFER"):
                total_masuk += nominal

            # Expense from this wallet
            if tx.get("id_dompet_asal") == id_dompet and tx.get("tipe") in ("PENGELUARAN", "TRANSFER"):
                total_keluar += nominal

        return saldo_awal + total_masuk - total_keluar

    def calculate_budget_usage(self, id_kategori: str, periode: str) -> float:
        """Calculate total spending for a category in a given period (YYYY-MM)."""
        transaksi_list = self.get_all_transaksi()
        total = 0.0
        for tx in transaksi_list:
            if (
                tx.get("tipe") == "PENGELUARAN"
                and tx.get("id_kategori") == id_kategori
                and tx.get("tanggal", "")[:7] == periode
            ):
                try:
                    total += float(tx.get("nominal", 0))
                except (ValueError, TypeError):
                    continue
        return total


# Singleton instance
sheets_service = GoogleSheetsService()
