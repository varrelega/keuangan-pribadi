"""AI-powered transaction parser using Google Gemini."""

import os
import json
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai


class TransactionParser:
    """Parse natural language transaction input using Gemini AI."""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your-gemini-api-key-here":
            raise ValueError(
                "GEMINI_API_KEY tidak ditemukan di .env. "
                "Dapatkan gratis di https://makersuite.google.com/app/apikey"
            )
        
        genai.configure(api_key=api_key)
        # Use newer model that's still supported
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def parse_transaction(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse natural language text into structured transaction data.
        
        Args:
            text: Natural language transaction description
            
        Returns:
            Dictionary with transaction details or None if parsing fails
        """
        prompt = f"""Kamu adalah asisten parsing transaksi keuangan. 
Ekstrak informasi transaksi dari teks berikut dan kembalikan dalam format JSON.

Aturan:
- tipe: "PEMASUKAN", "PENGELUARAN", atau "TRANSFER"
- nominal: angka dalam rupiah (tanpa titik/koma, contoh: 25000)
- kategori: kategori transaksi (Makanan & Minuman, Transportasi, Belanja, Hiburan, Tagihan, Gaji, dll)
- dompet_asal: nama dompet/akun untuk pengeluaran atau transfer (GoPay, ShopeePay, Bank BCA, Cash, dll)
- dompet_tujuan: nama dompet/akun untuk pemasukan atau transfer
- catatan: keterangan tambahan (opsional)

Deteksi kata kunci:
- "beli", "bayar", "buat", "untuk" → PENGELUARAN
- "dapat", "terima", "gaji", "masuk" → PEMASUKAN  
- "transfer", "kirim", "pindah", "top up", "topup", "isi" → TRANSFER
- "rb" atau "ribu" → kalikan 1000
- "jt" atau "juta" → kalikan 1000000

Teks: "{text}"

Kembalikan HANYA JSON tanpa penjelasan tambahan. Format:
{{"tipe": "...", "nominal": ..., "kategori": "...", "dompet_asal": "...", "dompet_tujuan": "...", "catatan": "..."}}

Jika tidak yakin dengan nilai tertentu, gunakan null.
"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            
            # Try to find JSON object in the text
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
            parsed = json.loads(result_text)
            
            # Normalize and validate
            if parsed.get("tipe") not in ["PEMASUKAN", "PENGELUARAN", "TRANSFER"]:
                return None
            
            if not parsed.get("nominal") or parsed["nominal"] <= 0:
                return None
            
            # Clean up null values
            cleaned = {
                "tipe": parsed["tipe"],
                "nominal": int(parsed["nominal"]),
                "kategori": parsed.get("kategori"),
                "dompet_asal": parsed.get("dompet_asal"),
                "dompet_tujuan": parsed.get("dompet_tujuan"),
                "catatan": parsed.get("catatan") or text,
            }
            
            return cleaned
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response text: {result_text}")
            return None
        except Exception as e:
            print(f"Gemini API error: {e}")
            return None
    
    def parse_simple(self, text: str) -> Optional[Dict[str, Any]]:
        """Fallback simple regex-based parser (no API needed)."""
        text_lower = text.lower()
        original_text = text  # Keep for case-sensitive matching
        
        # Detect transaction type
        tipe = None
        if any(word in text_lower for word in ["beli", "bayar", "buat", "untuk", "keluar"]):
            tipe = "PENGELUARAN"
        elif any(word in text_lower for word in ["dapat", "terima", "gaji", "masuk", "pendapatan"]):
            tipe = "PEMASUKAN"
        elif any(word in text_lower for word in ["transfer", "kirim", "pindah", "top up", "topup", "isi"]):
            tipe = "TRANSFER"
        
        if not tipe:
            return None
        
        # Extract nominal
        nominal = None
        # Match formats: 25000, 25rb, 25ribu, 2.5jt, 2juta
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
        
        # Extract wallet names (must start with letter, not number)
        dompet_asal = None
        dompet_tujuan = None
        
        # Pattern: "pakai [wallet]", "pake [wallet]", "dengan [wallet]"
        # Wallet name must start with a letter, not a number
        pakai_match = re.search(r'(?:pakai|pake|dengan|gunakan)\s+([A-Za-z][\w\s]*?)(?:\s+[0-9]|\s*$)', text_lower)
        if pakai_match:
            wallet_name = pakai_match.group(1).strip()
            # Get original case from text
            wallet_match = re.search(re.escape(wallet_name), original_text, re.IGNORECASE)
            if wallet_match:
                dompet_asal = wallet_match.group(0).strip()
        
        # Pattern: "dari [wallet]" (for TRANSFER or general)
        dari_match = re.search(r'dari\s+([A-Za-z][\w\s]*?)(?:\s+ke|\s+untuk|\s+[0-9]|\s*$)', text_lower)
        if dari_match:
            wallet_name = dari_match.group(1).strip()
            wallet_match = re.search(re.escape(wallet_name), original_text, re.IGNORECASE)
            if wallet_match:
                dompet_asal = wallet_match.group(0).strip()
        
        # Pattern: "ke [wallet]", "masuk ke [wallet]" (prioritize "ke" patterns)
        # Try "masuk ke" or "ke" first, avoid matching "masuk [number]"
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


# Global instance
try:
    parser = TransactionParser()
    print("OK: Gemini AI parser initialized")
except ValueError as e:
    print(f"Warning: Gemini API not configured - {e}")
    print("Info: Bot will use simple regex parser as fallback")
    parser = None
