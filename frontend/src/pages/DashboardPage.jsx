import { useState, useEffect } from 'react';
import { getDashboard } from '../services/api';
import { Wallet, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts';

const PIE_COLORS = [
  '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899',
  '#14b8a6', '#f97316', '#06b6d4', '#84cc16', '#a855f7', '#e11d48',
  '#0ea5e9', '#d946ef', '#22c55e', '#eab308', '#64748b', '#78716c',
];

function getColors(length) {
  return PIE_COLORS.slice(0, length);
}

function formatRupiah(num) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
  }).format(num);
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboard()
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Gagal memuat dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Memuat dashboard...</div>;
  if (error) return <div className="text-center py-20 text-red-500">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-indigo-100 text-indigo-600 p-2 rounded-lg">
              <DollarSign size={20} />
            </div>
            <span className="text-sm text-gray-500">Total Saldo</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{formatRupiah(data.total_saldo)}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-green-100 text-green-600 p-2 rounded-lg">
              <TrendingUp size={20} />
            </div>
            <span className="text-sm text-gray-500">Dompet Aktif</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{data.dompet_list.length}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-amber-100 text-amber-600 p-2 rounded-lg">
              <Wallet size={20} />
            </div>
            <span className="text-sm text-gray-500">Anggaran Bulan Ini</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{data.anggaran_bulan_ini.length}</p>
        </div>
      </div>

      {/* Wallet Balances */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-4">Saldo per Dompet</h3>
        {data.dompet_list.length === 0 ? (
          <p className="text-gray-400 text-sm">Belum ada dompet terdaftar.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.dompet_list.map((d) => (
              <div key={d.id_dompet} className="border rounded-lg p-4">
                <p className="text-sm text-gray-500">{d.nama_dompet}</p>
                <p className="text-lg font-bold mt-1">{formatRupiah(d.saldo)}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Monthly Trends Chart */}
      {data.tren_bulanan.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Tren Bulanan</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.tren_bulanan}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="periode" />
              <YAxis tickFormatter={(v) => `${(v / 1000000).toFixed(1)}jt`} />
              <Tooltip formatter={(v) => formatRupiah(v)} />
              <Legend />
              <Bar dataKey="total_pemasukan" name="Pemasukan" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="total_pengeluaran" name="Pengeluaran" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Category Breakdown Pie Charts */}
      {(data.pemasukan_per_kategori?.length > 0 || data.pengeluaran_per_kategori?.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {data.pemasukan_per_kategori?.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-semibold mb-4">Pemasukan per Kategori</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={data.pemasukan_per_kategori}
                    dataKey="total"
                    nameKey="nama_kategori"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ nama_kategori, percent }) =>
                      `${nama_kategori} ${(percent * 100).toFixed(0)}%`
                    }
                  >
                    {data.pemasukan_per_kategori.map((_, i) => (
                      <Cell key={i} fill={getColors(data.pemasukan_per_kategori.length)[i]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatRupiah(v)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
          {data.pengeluaran_per_kategori?.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-semibold mb-4">Pengeluaran per Kategori</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={data.pengeluaran_per_kategori}
                    dataKey="total"
                    nameKey="nama_kategori"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ nama_kategori, percent }) =>
                      `${nama_kategori} ${(percent * 100).toFixed(0)}%`
                    }
                  >
                    {data.pengeluaran_per_kategori.map((_, i) => (
                      <Cell key={i} fill={getColors(data.pengeluaran_per_kategori.length)[i]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatRupiah(v)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Budget Status */}
      {data.anggaran_bulan_ini.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Status Anggaran Bulan Ini</h3>
          <div className="space-y-4">
            {data.anggaran_bulan_ini.map((b) => (
              <div key={b.id_kategori}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{b.nama_kategori}</span>
                  <span className="text-gray-500">
                    {formatRupiah(b.total_terpakai)} / {formatRupiah(b.limit_anggaran)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className={`h-2.5 rounded-full transition-all ${
                      b.persentase_terpakai > 90
                        ? 'bg-red-500'
                        : b.persentase_terpakai > 70
                        ? 'bg-amber-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(b.persentase_terpakai, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Sisa: {formatRupiah(b.sisa)} ({(100 - b.persentase_terpakai).toFixed(1)}%)
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
