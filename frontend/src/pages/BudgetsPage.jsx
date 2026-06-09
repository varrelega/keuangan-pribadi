import { useState, useEffect } from 'react';
import { getBudgets, createBudget, deleteBudget, getCategories } from '../services/api';
import { Plus, Trash2, PieChart } from 'lucide-react';

function formatRupiah(num) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency', currency: 'IDR', minimumFractionDigits: 0,
  }).format(num);
}

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [periode, setPeriode] = useState(new Date().toISOString().slice(0, 7));
  const [form, setForm] = useState({
    periode: new Date().toISOString().slice(0, 7),
    id_kategori: '',
    limit_anggaran: '',
  });

  const fetchAll = () => {
    setLoading(true);
    Promise.all([getBudgets(periode), getCategories()])
      .then(([bRes, cRes]) => {
        setBudgets(bRes.data);
        setCategories(cRes.data.filter((c) => c.tipe === 'PENGELUARAN'));
      })
      .catch(() => setError('Gagal memuat data'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchAll(); }, [periode]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await createBudget({
        periode: form.periode,
        id_kategori: form.id_kategori,
        limit_anggaran: parseFloat(form.limit_anggaran),
      });
      setShowForm(false);
      setForm({ periode: periode, id_kategori: '', limit_anggaran: '' });
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal membuat anggaran');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Hapus anggaran ini?')) return;
    try {
      await deleteBudget(id);
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal menghapus');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl md:text-2xl font-bold">Anggaran</h2>
        <div className="flex items-center gap-3">
          <input type="month" value={periode}
            onChange={(e) => setPeriode(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500 flex-1 sm:flex-none" />
          <button onClick={() => { setShowForm(!showForm); setForm({ ...form, periode }); }}
            className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 whitespace-nowrap">
            <Plus size={16} /> Tambah Anggaran
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
          <button onClick={() => setError('')} className="ml-2 underline">tutup</button>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Periode</label>
              <input type="month" required value={form.periode}
                onChange={(e) => setForm({ ...form, periode: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Kategori</label>
              <select required value={form.id_kategori}
                onChange={(e) => setForm({ ...form, id_kategori: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="">-- Pilih kategori --</option>
                {categories.map((c) => (
                  <option key={c.id_kategori} value={c.id_kategori}>{c.nama_kategori}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Limit (Rp)</label>
              <input type="number" required min="1" step="1" value={form.limit_anggaran}
                onChange={(e) => setForm({ ...form, limit_anggaran: e.target.value })}
                placeholder="1500000"
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={submitting}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
              {submitting ? 'Menyimpan...' : 'Simpan'}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="border px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Batal</button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-gray-400 text-center py-10">Memuat...</p>
      ) : budgets.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <PieChart size={48} className="mx-auto mb-3 opacity-30" />
          <p>Belum ada anggaran untuk periode {periode}.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {budgets.map((b) => {
            const pct = b.limit_anggaran > 0 ? (b.total_terpakai / b.limit_anggaran) * 100 : 0;
            return (
              <div key={b.id_anggaran} className="bg-white rounded-xl shadow-sm border p-5 relative group">
                <button onClick={() => handleDelete(b.id_anggaran)}
                  className="absolute top-3 right-3 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Trash2 size={16} />
                </button>
                <p className="font-semibold">{b.nama_kategori}</p>
                <p className="text-xs text-gray-400 mb-3">Periode: {b.periode}</p>
                <div className="flex justify-between text-sm mb-1">
                  <span>Terpakai</span>
                  <span>{formatRupiah(b.total_terpakai)} / {formatRupiah(b.limit_anggaran)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className={`h-3 rounded-full transition-all ${
                    pct > 90 ? 'bg-red-500' : pct > 70 ? 'bg-amber-500' : 'bg-green-500'
                  }`} style={{ width: `${Math.min(pct, 100)}%` }} />
                </div>
                <p className="text-sm mt-2">
                  Sisa: <span className={b.sisa_anggaran < 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
                    {formatRupiah(b.sisa_anggaran)}
                  </span>
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
