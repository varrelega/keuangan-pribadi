# Product Requirements Document (PRD)

**Nama Produk:** Aplikasi Pencatatan Keuangan Pribadi (Cloud & Multi-Wallet)  
**Platform:** Frontend (Mobile/Web) & Backend API  
**Database:** Google Sheets API v4  
**Lingkungan Pengembangan:** Windows 11 / Linux  

---

## 1. Pendahuluan & Tujuan Produk

Aplikasi Pencatatan Keuangan Pribadi ini dirancang untuk memberikan kontrol penuh kepada pengguna dalam melacak, mengelola, dan menganalisis arus kas (*cash flow*) harian mereka. Dengan memanfaatkan arsitektur *cloudless backend* (menggunakan Google Sheets sebagai database), aplikasi ini menawarkan fleksibilitas tinggi di mana data mentah tetap dapat diakses dan dimanipulasi langsung oleh pengguna di luar aplikasi.

Tujuan utama proyek eksperimental ini adalah menyederhanakan pelacakan keuangan multi-aset secara *real-time*, mengamankan pengelolaan anggaran (*budgeting*), dan menyediakan struktur data yang bersih untuk kebutuhan analisis statistik atau proyeksi (*forecasting*) keuangan di masa mendatang.

---

## 2. Target Pengguna

* **Individu dengan Banyak Pos Keuangan:** Pengguna yang aktif menggunakan berbagai jenis dompet digital (*e-wallet* seperti GoPay, ShopeePay) serta rekening bank, dan membutuhkan pemisahan saldo yang jelas.
* **Pengguna Sadar Data (*Data-Centric Users*):** Mereka yang menyukai transparansi data keuangan dan menginginkan laporan riwayat transaksi yang siap diolah kembali menggunakan perkakas spreadsheet atau visualisasi eksternal.

---

## 3. Spesifikasi Fungsional (Minimum Viable Product / MVP)

### 3.1. Manajemen Multi-Dompet (*Multi-Wallet*)
* Aplikasi harus dapat mendaftarkan beberapa dompet/rekening/metode pembayaran dengan saldo awal yang ditentukan pengguna.
* Aplikasi menampilkan sisa uang secara spesifik per dompet digital atau akun bank.

### 3.2. Pencatatan Transaksi Dinamis
Mendukung tiga jenis interaksi keuangan utama:
1. **Pemasukan (Income):** Menambahkan dana ke dompet tujuan tertentu (misal: Gaji masuk ke Akun Bank).
2. **Pengeluaran (Expense):** Mengurangi dana dari dompet asal tertentu (misal: Bayar kopi menggunakan GoPay).
3. **Transfer Dana:** Memindahkan dana dari satu dompet ke dompet lainnya (misal: *Top-up* ShopeePay dari Akun Bank). Proses ini harus memotong saldo dompet asal dan menambah saldo dompet tujuan dalam satu kali aksi (*atomic operation*).

### 3.3. Manajemen Anggaran (*Budgeting*)
* Penetapan batas (*limit*) kuota pengeluaran bulanan yang dikelompokkan per kategori transaksi.
* Menyediakan kalkulasi sisa anggaran secara *real-time* untuk mencegah pengeluaran berlebih (*overspending*).

### 3.4. Analisis & Laporan Data
* *Dashboard* interaktif yang menampilkan total saldo gabungan dan rincian saldo per dompet.
* Visualisasi tren pengeluaran bulanan dan perbandingan pengeluaran riil terhadap *limit* anggaran.

---

## 4. Arsitektur Sistem & Tech Stack

Aplikasi ini menggunakan arsitektur terpisah (*decoupled*) untuk memastikan keamanan kredensial dan pemrosesan data yang optimal:

* **Frontend:** React / Vue.js (untuk Web) atau Flutter / React Native (untuk Mobile).
* **Backend Server:** Python dengan **FastAPI**. Bertindak sebagai proksi aman untuk menyembunyikan Google Service Account Token, melakukan validasi skema data, serta menangani logika kalkulasi matematika sebelum disajikan ke frontend.
* **Database Layer:** **Google Sheets API v4**. Dokumen Spreadsheet bertindak sebagai basis data cloud relasional lokal.
* **Autentikasi:** JSON Web Token (JWT) yang diisukan oleh backend server untuk memverifikasi sesi frontend.

---

## 5. Skema Database (Struktur Google Sheets)

Satu dokumen Google Sheets akan dibagi menjadi empat *tab* utama. Baris pertama pada setiap *tab* wajib digunakan sebagai *header* (nama kolom) dengan format huruf kecil (*lowercase*):

### A. Tab: `dompet`
Menyimpan master data dompet dan aset pengguna.
* **id_dompet** (String/UUID): ID unik dompet (e.g., `w-01`, `w-02`).
* **nama_dompet** (String): Nama dompet/rekening (e.g., `GoPay`, `Bank BCA`, `ShopeePay`).
* **saldo_awal** (Number/Float): Nominal saldo awal saat akun didaftarkan.

*Catatan Logika:* Saldo saat ini (*current balance*) akan dihitung secara dinamis oleh backend dengan rumus: `Saldo Awal + Total Pemasukan - Total Pengeluaran`.

### B. Tab: `kategori`
Menyimpan daftar kategori pengeluaran dan pemasukan.
* **id_kategori** (String/UUID): ID unik kategori (e.g., `kat-01`, `kat-02`).
* **nama_kategori** (String): Nama aktivitas (e.g., `Makanan & Minuman`, `Transportasi`, `Gaji`).
* **tipe** (String/Enum): Kategori peruntukan, bernilai `PEMASUKAN` atau `PENGELUARAN`.

### C. Tab: `anggaran`
Menyimpan batas alokasi dana per bulan.
* **id_anggaran** (String/UUID): ID unik anggaran (e.g., `bg-01`).
* **periode** (String - YYYY-MM): Bulan dan tahun anggaran (e.g., `2026-06`).
* **id_kategori** (String): Relasi ke `id_kategori` di Tab Kategori.
* **limit_anggaran** (Number/Float): Batas pengeluaran maksimal (e.g., `1500000`).

### D. Tab: `transaksi`
Menyimpan seluruh riwayat log aktivitas keuangan.
* **id** (String/UUID): ID unik transaksi (e.g., `tx-10293`).
* **tanggal** (Date - YYYY-MM-DD): Tanggal eksekusi transaksi.
* **tipe** (String/Enum): Jenis transaksi, berisi `PEMASUKAN`, `PENGELUARAN`, atau `TRANSFER`.
* **id_kategori** (String): Relasi ke `id_kategori`. Dapat dikosongkan jika tipe transaksi adalah `TRANSFER`.
* **id_dompet_asal** (String): Relasi ke `id_dompet`. Diisi jika tipe `PENGELUARAN` atau `TRANSFER`.
* **id_dompet_tujuan** (String): Relasi ke `id_dompet`. Diisi jika tipe `PEMASUKAN` atau `TRANSFER`.
* **nominal** (Number/Float): Jumlah uang yang ditransaksikan.
* **catatan** (String): Keterangan tambahan (opsional).
* **created_at** (Timestamp): Waktu otomatis pencatatan sistem (YYYY-MM-DD HH:MM:SS).

---

## 6. Alur Pengguna Utama (*User Flow*)

1. **Inisialisasi Aplikasi:** Pengguna pertama kali mendaftarkan akun dompet beserta saldo awal, serta menyusun batasan anggaran per kategori untuk bulan berjalan melalui antarmuka frontend.
2. **Pencatatan Aktivitas:** Pengguna memilih tipe transaksi di frontend (misal: Transfer dari Bank ke GoPay sebesar Rp100.000).
3. **Validasi & Penulisan Backend:** Frontend mengirimkan data tersebut ke REST endpoint backend (`/api/transactions`). Backend FastAPI melakukan validasi format:
   * Memastikan `id_dompet_asal` dan `id_dompet_tujuan` valid.
   * Mengirimkan instruksi penulisan baris baru secara aman menggunakan Google Sheets API.
4. **Kalkulasi & Sinkronisasi Visual:** Backend memperbarui data *cache* internal, lalu mengirimkan status sukses ke frontend. Frontend memperbarui visualisasi halaman utama dan menampilkan sisa uang terbaru pada dompet GoPay dan Bank BCA secara akurat.

---

## 7. Batasan Teknis & Solusi (*Constraints & Optimizations*)

* **Rate Limiting Google API:** Google Sheets API membatasi jumlah *request* per menit. Backend harus menerapkan lapisan *caching* jangka pendek (*in-memory* atau Redis) untuk operasi pembacaan data (`GET`). Data dari Google Sheets hanya akan ditarik ulang secara paksa jika terjadi operasi penulisan (`POST`, `PUT`, `DELETE`).
* **Penanganan Operasi Baris (Row Management):** Karena Google Sheets tidak memiliki indeks *auto-increment* seperti database SQL, backend server bertanggung jawab melakukan pencarian (*scanning*) nomor baris berdasarkan kolom `id` transaksi sebelum menjalankan perintah modifikasi (`PUT`) atau penghapusan (`DELETE`).
* **Konsistensi Format:** Seluruh sanitasi data wajib diselesaikan di tingkat backend. Data yang tidak lolos validasi (seperti nominal berformat teks atau tanggal tidak sesuai standar) akan langsung ditolak oleh backend untuk menghindari kerusakan struktur tabel spreadsheet.
