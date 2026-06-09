import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, Wallet, ArrowLeftRight, PieChart, Tags, LogOut, Menu, X,
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/wallets', label: 'Dompet', icon: Wallet },
  { to: '/transactions', label: 'Transaksi', icon: ArrowLeftRight },
  { to: '/budgets', label: 'Anggaran', icon: PieChart },
  { to: '/categories', label: 'Kategori', icon: Tags },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const sidebarContent = (
    <>
      <div className="p-4 md:p-6 border-b border-indigo-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-base md:text-lg font-bold">Keuangan</h1>
            <p className="text-indigo-300 text-xs md:text-sm mt-0.5">{user?.username}</p>
          </div>
          <button onClick={() => setMenuOpen(false)} className="md:hidden text-indigo-300">
            <X size={20} />
          </button>
        </div>
      </div>
      <nav className="flex-1 p-2 md:p-4 space-y-0.5 md:space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 md:px-4 py-2.5 md:py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-700 text-white'
                  : 'text-indigo-200 hover:bg-indigo-800 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-2 md:p-4 border-t border-indigo-800">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 md:px-4 py-2.5 md:py-3 rounded-lg text-sm font-medium text-indigo-200 hover:bg-indigo-800 hover:text-white w-full transition-colors"
        >
          <LogOut size={18} />
          Keluar
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Mobile Header */}
      <div className="md:hidden bg-indigo-900 text-white px-4 py-3 flex items-center justify-between z-20">
        <div>
          <h1 className="text-base font-bold">Keuangan</h1>
          <p className="text-indigo-300 text-xs">{user?.username}</p>
        </div>
        <button onClick={() => setMenuOpen(true)} className="text-white">
          <Menu size={24} />
        </button>
      </div>

      {/* Mobile Overlay */}
      {menuOpen && (
        <div className="md:hidden fixed inset-0 bg-black/50 z-30" onClick={() => setMenuOpen(false)} />
      )}

      {/* Mobile Sidebar (slide-in) */}
      {menuOpen && (
        <aside className="md:hidden fixed left-0 top-0 bottom-0 w-64 bg-indigo-900 text-white flex flex-col z-40 shadow-xl animate-slide-in">
          {sidebarContent}
        </aside>
      )}

      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-64 bg-indigo-900 text-white flex-col">
        {sidebarContent}
      </aside>

      {/* Bottom Navigation (mobile) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t flex justify-around items-center py-1 z-20 safe-area-bottom">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 px-2 py-1.5 text-[10px] font-medium transition-colors rounded-lg ${
                isActive ? 'text-indigo-600' : 'text-gray-400 hover:text-gray-600'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Main Content */}
      <main className="flex-1 bg-gray-50 overflow-auto pb-16 md:pb-0">
        <div className="max-w-6xl mx-auto p-3 md:p-6">{children}</div>
      </main>
    </div>
  );
}
