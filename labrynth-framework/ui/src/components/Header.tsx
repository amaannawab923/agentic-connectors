import { Search, Bell, Plus, User } from 'lucide-react';
import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useTheme, routes } from '../App';

export function Header() {
  const { theme } = useTheme();
  const location = useLocation();
  const [activeFilter, setActiveFilter] = useState('LAST 7 DAYS');
  const filters = ['TODAY', 'LAST 7 DAYS', 'LAST 30 DAYS'];

  // Get current page name from route
  const currentRoute = routes.find(r => r.path === location.pathname);
  const currentPage = currentRoute?.name || 'Dashboard';

  return (
    <header className={`${
      theme === 'dark'
        ? 'bg-[#0A1628] border-b border-[rgba(212,175,55,0.15)]'
        : 'bg-white border-b border-[#E5E7EB]'
    } px-6 py-4`}>
      <div className="flex items-center justify-between">
        {/* Breadcrumb and Filters */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-sm">
            <span className={`font-greek ${theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'}`}>
              Labyrinth
            </span>
            <span className="text-[#D4AF37]">›</span>
            <span className={theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'}>
              {currentPage}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {filters.map((filter) => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`
                  px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150
                  ${activeFilter === filter
                    ? 'bg-gradient-to-r from-[#D4AF37] to-[#B8860B] text-white shadow-lg shadow-[rgba(212,175,55,0.3)]'
                    : theme === 'dark'
                    ? 'text-[#94A3B8] hover:bg-[rgba(212,175,55,0.1)]'
                    : 'text-[#64748B] hover:bg-[#F9FAFB]'
                  }
                `}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative">
            <div className={`flex items-center gap-2 border rounded-lg px-3 py-2 w-64 transition-colors ${
              theme === 'dark'
                ? 'bg-[#0F1729] border-[rgba(212,175,55,0.2)] hover:border-[rgba(212,175,55,0.4)]'
                : 'bg-[#F9FAFB] border-[#E5E7EB] hover:border-[#D1D5DB]'
            }`}>
              <Search className="w-4 h-4 text-[#64748B]" />
              <input
                type="text"
                placeholder="Search..."
                className={`flex-1 bg-transparent text-sm placeholder:text-[#64748B] outline-none ${
                  theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
                }`}
              />
              <kbd className={`px-1.5 py-0.5 text-xs text-[#64748B] rounded ${
                theme === 'dark' ? 'bg-[rgba(212,175,55,0.1)]' : 'bg-[#E5E7EB]'
              }`}>⌘K</kbd>
            </div>
          </div>

          {/* Notification Bell */}
          <button className={`relative p-2 rounded-lg transition-colors ${
            theme === 'dark'
              ? 'hover:bg-[rgba(212,175,55,0.1)]'
              : 'hover:bg-[#F9FAFB]'
          }`}>
            <Bell className={`w-5 h-5 ${
              theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
            }`} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#E07A5F] rounded-full ring-2 ring-[rgba(224,122,95,0.3)]"></span>
          </button>

          {/* New Pipeline Button */}
          <button className="flex items-center gap-2 bg-gradient-to-r from-[#D4AF37] to-[#B8860B] hover:from-[#B8860B] hover:to-[#9A7510] text-white px-4 py-2 rounded-lg transition-all shadow-lg shadow-[rgba(212,175,55,0.25)] text-sm font-medium">
            <Plus className="w-4 h-4" />
            New Pipeline
          </button>

          {/* User Avatar */}
          <button className={`p-2 rounded-lg transition-colors ${
            theme === 'dark'
              ? 'hover:bg-[rgba(212,175,55,0.1)]'
              : 'hover:bg-[#F9FAFB]'
          }`}>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#B8860B] flex items-center justify-center text-white text-sm font-medium border-2 border-[rgba(212,175,55,0.3)]">
              JD
            </div>
          </button>
        </div>
      </div>
    </header>
  );
}
