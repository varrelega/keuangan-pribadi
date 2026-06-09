import { useState, useEffect } from 'react';
import { getWallets, createWallet, deleteWallet } from '../services/api';
import { Plus, Trash2, Wallet } from 'lucide-react';

function formatRupiah(num) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency', currency: 'IDR', minimumFractionDigits: 0,
  }).format(num);
}

export default function WalletsPage() {
  const [wallets, setWallets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nama_dompet: '', saldo_awal: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const fetchWallets = () => {
    setLoading(true);
    getWallets()
      .then((res) => setWallets(res.data))
      .catch(() => setError('Gagal memuat dompet'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchWallets(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createWallet({
        nama_dompet: form.nama_dompet,
        saldo_awal: parseFloat(form.saldo_awal),
      });
      setForm({ nama_dompet: '', saldo_awal: '' });
      setShowForm(false);
      fetchWallets();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal membuat dompet');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Hapus dompet ini?')) return;
    try {
      await deleteWallet(id);
      fetchWallets();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal menghapus dompet');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl md:text-2xl font-bold">Dompet</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} /> Tambah Dompet
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
          <button onClick={() => setError('')} className="ml-2 underline">tutup</button>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nama Dompet</label>
              <input
                type="text" required
                value={form.nama_dompet}
                onChange={(e) => setForm({ ...form, nama_dompet: e.target.value })}
                placeholder="contoh: GoPay, Bank BCA"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Saldo Awal</label>
              <input
                type="number" required min="0" step="1"
                value={form.saldo_awal}
                onChange={(e) => setForm({ ...form, saldo_awal: e.target.value })}
                placeholder="500000"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={submitting}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
              {submitting ? 'Menyimpan...' : 'Simpan'}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="border px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
              Batal
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-gray-400 text-center py-10">Memuat...</p>
      ) : wallets.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Wallet size={48} className="mx-auto mb-3 opacity-30" />
          <p>Belum ada dompet. Tambahkan dompet pertama Anda.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {wallets.map((w) => (
            <div key={w.id_dompet} className="bg-white rounded-xl shadow-sm border p-5 relative group">
              <button
                onClick={() => handleDelete(w.id_dompet)}
                className="absolute top-3 right-3 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 size={16} />
              </button>
              <p className="text-sm text-gray-500">{w.nama_dompet}</p>
              <p className="text-xl font-bold mt-1">{formatRupiah(w.saldo_saat_ini)}</p>
              <p className="text-xs text-gray-400 mt-2">
                Saldo awal: {formatRupiah(w.saldo_awal)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
