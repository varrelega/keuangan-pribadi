import json
import os
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

import httpx


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class TransactionParser:
    """Parse natural language transaction input using OpenRouter AI (free models)."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key or self.api_key == "your-openrouter-api-key-here":
            raise ValueError(
                "OPENROUTER_API_KEY tidak ditemukan di .env. "
                "Dapatkan gratis di https://openrouter.ai/keys"
            )

    def parse_transaction(self, text: str, categories: list = None, wallets: list = None) -> Optional[Dict[str, Any]]:
        """Parse natural language text into structured transaction data."""

        cat_list = ""
        if categories:
            expense_cats = [c["nama_kategori"] for c in categories if c.get("tipe") == "PENGELUARAN"]
            income_cats = [c["nama_kategori"] for c in categories if c.get("tipe") == "PEMASUKAN"]
            if expense_cats:
                cat_list += f"\nKategori PENGELUARAN tersedia: {', '.join(expense_cats)}"
            if income_cats:
                cat_list += f"\nKategori PEMASUKAN tersedia: {', '.join(income_cats)}"

        wal_list = ""
        if wallets:
            wal_list = f"\nDompet tersedia: {', '.join(w['nama_dompet'] for w in wallets)}"

        prompt = f"""Kamu adalah asisten parsing transaksi keuangan. 
Ekstrak informasi transaksi dari teks berikut dan kembalikan dalam format JSON.

Aturan:
- tipe: "PEMASUKAN", "PENGELUARAN", atau "TRANSFER"
- nominal: angka dalam rupiah (tanpa titik/koma, contoh: 25000)
- kategori: pilih dari daftar yang tersedia. Jika tidak cocok, gunakan null.
- dompet_asal: pilih dari daftar dompet yang tersedia. Jika tidak disebutkan, gunakan null.
- dompet_tujuan: pilih dari daftar dompet yang tersedia. Jika tidak disebutkan, gunakan null.
- catatan: keterangan tambahan (opsional){cat_list}{wal_list}

Deteksi kata kunci:
- "beli", "bayar", "buat", "untuk" → PENGELUARAN
- "dapat", "terima", "gaji", "masuk" → PEMASUKAN  
- "transfer", "kirim", "pindah", "top up", "topup", "isi" → TRANSFER
- "rb" atau "ribu" → kalikan 1000
- "jt" atau "juta" → kalikan 1000000

Teks: "{text}"

Kembalikan HANYA JSON tanpa penjelasan tambahan. Format:
{{"tipe": "...", "nominal": ..., "kategori": "...", "dompet_asal": "...", "dompet_tujuan": "...", "catatan": "..."}}

Gunakan nama kategori dan dompet PERSIS dari daftar yang tersedia. Jika tidak ada yang cocok, gunakan null.
"""

        try:
            response = httpx.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://keuangan-pribadi.vercel.app",
                    "X-Title": "Keuangan Pribadi",
                },
                json={
                    "model": "openrouter/free",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                timeout=30,
            )
            response.raise_for_status()
            result_text = response.json()["choices"][0]["message"]["content"].strip()

            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)

            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)

            parsed = json.loads(result_text)

            if parsed.get("tipe") not in ["PEMASUKAN", "PENGELUARAN", "TRANSFER"]:
                return None

            if not parsed.get("nominal") or parsed["nominal"] <= 0:
                return None

            cleaned = {
                "tipe": parsed["tipe"],
                "nominal": int(parsed["nominal"]),
                "kategori": parsed.get("kategori"),
                "dompet_asal": parsed.get("dompet_asal"),
                "dompet_tujuan": parsed.get("dompet_tujuan"),
                "catatan": parsed.get("catatan") or text,
            }

            return cleaned

        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    def parse_simple(self, text: str) -> Optional[Dict[str, Any]]:
        """Fallback simple regex-based parser (no API needed)."""
        text_lower = text.lower()
        original_text = text

        tipe = None
        if any(word in text_lower for word in [
            "beli", "bayar", "buat", "untuk", "keluar",
            "service", "servis", "bengkel", "ganti", "perbaiki",
            "makan", "minum", "kopi", "jajan",
            "bensin", "parkir", "tol", "bbm",
            "pulsa", "kuota", "paket data", "langganan",
            "sewa", "bayar", "biaya", "ongkir", "ongkos",
            "belanja", "sembako", "sayur", "daging",
            "topup", "top up", "isi ulang",
        ]):
            tipe = "PENGELUARAN"
        elif any(word in text_lower for word in [
            "dapat", "terima", "gaji", "masuk", "pendapatan",
            "bonus", "hasil", "komisi", "refund", "kembali",
            "kiriman", "transferan", "rejeki", "untung",
            "dividen", "bunga", "cashback",
        ]):
            tipe = "PEMASUKAN"
        elif any(word in text_lower for word in [
            "transfer", "kirim", "pindah", "top up", "topup", "isi",
        ]):
            tipe = "TRANSFER"

        if not tipe:
            return None

        nominal = None
        amount_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:jt|juta)', 1000000),
            (r'(\d+(?:\.\d+)?)\s*(?:rb|ribu)', 1000),
            (r'(\d{3,})', 1),
        ]

        for pattern, multiplier in amount_patterns:
            match = re.search(pattern, text_lower)
            if match:
                nominal = float(match.group(1)) * multiplier
                break

        if not nominal:
            return None

        dompet_asal = None
        dompet_tujuan = None

        pakai_match = re.search(r'(?:pakai|pake|dengan|gunakan)\s+([A-Za-z][\w\s]*?)(?:\s+[0-9]|\s*$)', text_lower)
        if pakai_match:
            wallet_name = pakai_match.group(1).strip()
            wallet_match = re.search(re.escape(wallet_name), original_text, re.IGNORECASE)
            if wallet_match:
                dompet_asal = wallet_match.group(0).strip()

        dari_match = re.search(r'dari\s+([A-Za-z][\w\s]*?)(?:\s+ke|\s+untuk|\s+[0-9]|\s*$)', text_lower)
        if dari_match:
            wallet_name = dari_match.group(1).strip()
            wallet_match = re.search(re.escape(wallet_name), original_text, re.IGNORECASE)
            if wallet_match:
                dompet_asal = wallet_match.group(0).strip()

        ke_match = re.search(r'(?:masuk\s+ke|ke)\s+([A-Za-z][\w\s]*?)(?:\s+[0-9]|\s*$)', text_lower)
        if ke_match:
            wallet_name = ke_match.group(1).strip()
            wallet_match = re.search(re.escape(wallet_name), original_text, re.IGNORECASE)
            if wallet_match:
                dompet_tujuan = wallet_match.group(0).strip()

        return {
            "tipe": tipe,
            "nominal": int(nominal),
            "kategori": None,
            "dompet_asal": dompet_asal,
            "dompet_tujuan": dompet_tujuan,
            "catatan": text,
        }


try:
    parser = TransactionParser()
    print("OK: OpenRouter AI parser initialized")
except ValueError as e:
    print(f"Warning: OpenRouter not configured - {e}")
    print("Info: Bot will use simple regex parser as fallback")
    parser = None
