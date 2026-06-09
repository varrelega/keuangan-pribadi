import { useState, useEffect } from 'react';
import { getCategories, createCategory, deleteCategory } from '../services/api';
import { Plus, Trash2, Tags } from 'lucide-react';

export default function CategoriesPage() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ nama_kategori: '', tipe: 'PENGELUARAN' });

  const fetchCategories = () => {
    setLoading(true);
    getCategories()
      .then((res) => setCategories(res.data))
      .catch(() => setError('Gagal memuat kategori'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchCategories(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await createCategory(form);
      setForm({ nama_kategori: '', tipe: 'PENGELUARAN' });
      setShowForm(false);
      fetchCategories();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal membuat kategori');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Hapus kategori ini?')) return;
    try {
      await deleteCategory(id);
      fetchCategories();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal menghapus');
    }
  };

  const pemasukan = categories.filter((c) => c.tipe === 'PEMASUKAN');
  const pengeluaran = categories.filter((c) => c.tipe === 'PENGELUARAN');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl md:text-2xl font-bold">Kategori</h2>
        <button onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
          <Plus size={16} /> Tambah Kategori
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Nama Kategori</label>
              <input type="text" required value={form.nama_kategori}
                onChange={(e) => setForm({ ...form, nama_kategori: e.target.value })}
                placeholder="contoh: Makanan & Minuman"
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipe</label>
              <select value={form.tipe}
                onChange={(e) => setForm({ ...form, tipe: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="PENGELUARAN">Pengeluaran</option>
                <option value="PEMASUKAN">Pemasukan</option>
              </select>
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
      ) : categories.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Tags size={48} className="mx-auto mb-3 opacity-30" />
          <p>Belum ada kategori. Tambahkan kategori pertama.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold mb-3 text-green-700">Pemasukan</h3>
            {pemasukan.length === 0 ? (
              <p className="text-gray-400 text-sm">Belum ada kategori pemasukan.</p>
            ) : (
              <div className="space-y-2">
                {pemasukan.map((c) => (
                  <div key={c.id_kategori}
                    className="bg-white border rounded-lg px-4 py-3 flex items-center justify-between group">
                    <div>
                      <span className="font-medium text-sm">{c.nama_kategori}</span>
                      <span className="ml-2 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                        Pemasukan
                      </span>
                    </div>
                    <button onClick={() => handleDelete(c.id_kategori)}
                      className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-3 text-red-700">Pengeluaran</h3>
            {pengeluaran.length === 0 ? (
              <p className="text-gray-400 text-sm">Belum ada kategori pengeluaran.</p>
            ) : (
              <div className="space-y-2">
                {pengeluaran.map((c) => (
                  <div key={c.id_kategori}
                    className="bg-white border rounded-lg px-4 py-3 flex items-center justify-between group">
                    <div>
                      <span className="font-medium text-sm">{c.nama_kategori}</span>
                      <span className="ml-2 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                        Pengeluaran
                      </span>
                    </div>
                    <button onClick={() => handleDelete(c.id_kategori)}
                      className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
