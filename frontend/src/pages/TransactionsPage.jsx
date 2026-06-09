import { useState, useEffect } from 'react';
import {
  getTransactions, createTransaction, deleteTransaction,
  getWallets, getCategories,
} from '../services/api';
import { Plus, Trash2, ArrowLeftRight, ArrowDownLeft, ArrowUpRight } from 'lucide-react';

function formatRupiah(num) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency', currency: 'IDR', minimumFractionDigits: 0,
  }).format(num);
}

const TIPE_ICONS = {
  PEMASUKAN: <ArrowDownLeft size={16} className="text-green-500" />,
  PENGELUARAN: <ArrowUpRight size={16} className="text-red-500" />,
  TRANSFER: <ArrowLeftRight size={16} className="text-blue-500" />,
};

const TIPE_COLORS = {
  PEMASUKAN: 'bg-green-50 text-green-700',
  PENGELUARAN: 'bg-red-50 text-red-700',
  TRANSFER: 'bg-blue-50 text-blue-700',
};

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    tanggal: new Date().toISOString().split('T')[0],
    tipe: 'PENGELUARAN',
    id_kategori: '',
    id_dompet_asal: '',
    id_dompet_tujuan: '',
    nominal: '',
    catatan: '',
  });

  const fetchAll = () => {
    setLoading(true);
    Promise.all([getTransactions(), getWallets(), getCategories()])
      .then(([txRes, wRes, cRes]) => {
        setTransactions(txRes.data);
        setWallets(wRes.data);
        setCategories(cRes.data);
      })
      .catch(() => setError('Gagal memuat data'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchAll(); }, []);

  const filteredCategories = categories.filter((c) => {
    if (form.tipe === 'TRANSFER') return false;
    return c.tipe === form.tipe;
  });

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const payload = {
        tanggal: form.tanggal,
        tipe: form.tipe,
        nominal: parseFloat(form.nominal),
        catatan: form.catatan || null,
        id_kategori: form.tipe !== 'TRANSFER' ? form.id_kategori : null,
        id_dompet_asal: ['PENGELUARAN', 'TRANSFER'].includes(form.tipe) ? form.id_dompet_asal : null,
        id_dompet_tujuan: ['PEMASUKAN', 'TRANSFER'].includes(form.tipe) ? form.id_dompet_tujuan : null,
      };
      await createTransaction(payload);
      setShowForm(false);
      setForm({
        tanggal: new Date().toISOString().split('T')[0],
        tipe: 'PENGELUARAN', id_kategori: '', id_dompet_asal: '',
        id_dompet_tujuan: '', nominal: '', catatan: '',
      });
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal membuat transaksi');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Hapus transaksi ini?')) return;
    try {
      await deleteTransaction(id);
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal menghapus');
    }
  };

  const getWalletName = (id) => wallets.find((w) => w.id_dompet === id)?.nama_dompet || id;
  const getCategoryName = (id) => categories.find((c) => c.id_kategori === id)?.nama_kategori || id;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl md:text-2xl font-bold">Transaksi</h2>
        <button onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
          <Plus size={16} /> Catat Transaksi
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
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tanggal</label>
              <input type="date" required value={form.tanggal}
                onChange={(e) => setForm({ ...form, tanggal: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipe</label>
              <select value={form.tipe}
                onChange={(e) => setForm({ ...form, tipe: e.target.value, id_kategori: '', id_dompet_asal: '', id_dompet_tujuan: '' })}
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="PENGELUARAN">Pengeluaran</option>
                <option value="PEMASUKAN">Pemasukan</option>
                <option value="TRANSFER">Transfer</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nominal (Rp)</label>
              <input type="number" required min="1" step="1" value={form.nominal}
                onChange={(e) => setForm({ ...form, nominal: e.target.value })}
                placeholder="100000"
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {form.tipe !== 'TRANSFER' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Kategori</label>
                <select required value={form.id_kategori}
                  onChange={(e) => setForm({ ...form, id_kategori: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="">-- Pilih --</option>
                  {filteredCategories.map((c) => (
                    <option key={c.id_kategori} value={c.id_kategori}>{c.nama_kategori}</option>
                  ))}
                </select>
              </div>
            )}
            {['PENGELUARAN', 'TRANSFER'].includes(form.tipe) && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dompet Asal</label>
                <select required value={form.id_dompet_asal}
                  onChange={(e) => setForm({ ...form, id_dompet_asal: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="">-- Pilih --</option>
                  {wallets.map((w) => (
                    <option key={w.id_dompet} value={w.id_dompet}>{w.nama_dompet}</option>
                  ))}
                </select>
              </div>
            )}
            {['PEMASUKAN', 'TRANSFER'].includes(form.tipe) && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dompet Tujuan</label>
                <select required value={form.id_dompet_tujuan}
                  onChange={(e) => setForm({ ...form, id_dompet_tujuan: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="">-- Pilih --</option>
                  {wallets.map((w) => (
                    <option key={w.id_dompet} value={w.id_dompet}>{w.nama_dompet}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Catatan (opsional)</label>
            <input type="text" value={form.catatan}
              onChange={(e) => setForm({ ...form, catatan: e.target.value })}
              placeholder="Keterangan tambahan"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
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
      ) : transactions.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <ArrowLeftRight size={48} className="mx-auto mb-3 opacity-30" />
          <p>Belum ada transaksi. Mulai catat keuangan Anda.</p>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden md:block bg-white rounded-xl shadow-sm border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Tanggal</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Tipe</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Detail</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Nominal</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Catatan</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">{tx.tanggal}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${TIPE_COLORS[tx.tipe]}`}>
                        {TIPE_ICONS[tx.tipe]} {tx.tipe}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {tx.tipe === 'TRANSFER'
                        ? `${getWalletName(tx.id_dompet_asal)} \u2192 ${getWalletName(tx.id_dompet_tujuan)}`
                        : `${getCategoryName(tx.id_kategori)} (${getWalletName(tx.id_dompet_asal || tx.id_dompet_tujuan)})`}
                    </td>
                    <td className="px-4 py-3 text-right font-medium whitespace-nowrap">
                      <span className={tx.tipe === 'PEMASUKAN' ? 'text-green-600' : tx.tipe === 'PENGELUARAN' ? 'text-red-600' : ''}>
                        {tx.tipe === 'PEMASUKAN' ? '+' : tx.tipe === 'PENGELUARAN' ? '-' : ''}{formatRupiah(tx.nominal)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 truncate max-w-[150px]">{tx.catatan || '-'}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => handleDelete(tx.id)}
                        className="text-gray-300 hover:text-red-500 transition-colors">
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards */}
          <div className="md:hidden space-y-3">
            {transactions.map((tx) => (
              <div key={tx.id} className="bg-white rounded-xl shadow-sm border p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${TIPE_COLORS[tx.tipe]}`}>
                      {TIPE_ICONS[tx.tipe]} {tx.tipe}
                    </span>
                    <span className="text-xs text-gray-400">{tx.tanggal}</span>
                  </div>
                  <button onClick={() => handleDelete(tx.id)}
                    className="text-gray-300 hover:text-red-500 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
                <p className="text-sm text-gray-600 mb-1">
                  {tx.tipe === 'TRANSFER'
                    ? `${getWalletName(tx.id_dompet_asal)} \u2192 ${getWalletName(tx.id_dompet_tujuan)}`
                    : `${getCategoryName(tx.id_kategori)}`}
                </p>
                <p className="text-xs text-gray-400 mb-2">
                  {getWalletName(tx.id_dompet_asal || tx.id_dompet_tujuan)}
                  {tx.catatan ? ` \u2022 ${tx.catatan}` : ''}
                </p>
                <p className={`text-base font-bold ${tx.tipe === 'PEMASUKAN' ? 'text-green-600' : tx.tipe === 'PENGELUARAN' ? 'text-red-600' : 'text-gray-900'}`}>
                  {tx.tipe === 'PEMASUKAN' ? '+' : tx.tipe === 'PENGELUARAN' ? '-' : ''}{formatRupiah(tx.nominal)}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
