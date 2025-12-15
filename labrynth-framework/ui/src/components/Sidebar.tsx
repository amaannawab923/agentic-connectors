import { LayoutGrid, GitBranch, Zap, Clock, Bot, GraduationCap, Settings, Sun, Moon, Workflow } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useTheme } from '../App';
import { LabyrinthLogoSimple } from './Logo';

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutGrid },
  { name: 'Workflows', path: '/workflows', icon: Workflow },
  { name: 'Pipelines', path: '/pipelines', icon: GitBranch },
  { name: 'Triggers', path: '/triggers', icon: Zap },
  { name: 'Pipeline Runs', path: '/runs', icon: Clock },
  { name: 'Agentic Assets', path: '/agents', icon: Bot },
  { name: 'Training', path: '/training', icon: GraduationCap },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export function Sidebar() {
  const { theme, setTheme } = useTheme();

  return (
    <div className={`w-[220px] ${
      theme === 'dark' ? 'bg-[#0A1628]' : 'bg-white border-r border-[#E5E7EB]'
    } flex flex-col h-full`}>
      {/* Logo and Version */}
      <div className="px-4 py-6">
        <div className="flex items-center gap-2 mb-1">
          <LabyrinthLogoSimple className="w-7 h-7" />
          <span className={`${
            theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
          } font-semibold font-greek tracking-wide`}>Labyrinth</span>
        </div>
        <div className={`text-xs ml-9 ${
          theme === 'dark' ? 'text-[#64748B]' : 'text-[#94A3B8]'
        }`}>v0.1.0</div>
      </div>

      {/* Divider with Greek pattern */}
      <div className={`h-px mx-4 mb-4 ${
        theme === 'dark' ? 'bg-[rgba(212,175,55,0.2)]' : 'bg-[#E5E7EB]'
      }`}></div>

      {/* Navigation Items */}
      <nav className="flex-1 px-4">
        {/* Dashboard */}
        <div className="space-y-2">
          {navItems.slice(0, 1).map((item) => (
            <NavItem key={item.name} item={item} />
          ))}
        </div>

        {/* Build: Workflows, Pipelines, Triggers, Pipeline Runs */}
        <div className="space-y-2 mt-2">
          {navItems.slice(1, 5).map((item) => (
            <NavItem key={item.name} item={item} />
          ))}
        </div>

        {/* Assets: Agentic Assets, Training */}
        <div className="space-y-2 mt-6">
          {navItems.slice(5, 7).map((item) => (
            <NavItem key={item.name} item={item} />
          ))}
        </div>

        {/* Settings */}
        <div className="space-y-2 mt-6">
          {navItems.slice(7).map((item) => (
            <NavItem key={item.name} item={item} />
          ))}
        </div>
      </nav>

      {/* Bottom Section */}
      <div className="px-4 pb-4 space-y-4">
        {/* Theme Toggle */}
        <div className="flex items-center justify-center gap-2 py-3">
          <Sun className={`w-4 h-4 ${
            theme === 'light' ? 'text-[#D4AF37]' : 'text-[#64748B]'
          }`} />
          <div
            className={`relative w-12 h-6 rounded-full cursor-pointer transition-colors ${
              theme === 'dark' ? 'bg-[#2C5F8D]' : 'bg-[#E5E7EB]'
            }`}
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <div
              className={`absolute top-1 w-4 h-4 rounded-full transition-transform ${
                theme === 'dark'
                  ? 'translate-x-7 bg-[#D4AF37]'
                  : 'translate-x-1 bg-white'
              }`}
            ></div>
          </div>
          <Moon className={`w-4 h-4 ${
            theme === 'dark' ? 'text-[#2C5F8D]' : 'text-[#64748B]'
          }`} />
        </div>

        {/* Divider */}
        <div className={`h-px ${
          theme === 'dark' ? 'bg-[rgba(212,175,55,0.2)]' : 'bg-[#E5E7EB]'
        }`}></div>

        {/* User Profile */}
        <div className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors cursor-pointer ${
          theme === 'dark'
            ? 'hover:bg-[rgba(212,175,55,0.1)]'
            : 'hover:bg-[#F9FAFB]'
        }`}>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#B8860B] flex items-center justify-center text-white text-sm font-medium border-2 border-[rgba(212,175,55,0.3)]">
            JD
          </div>
          <span className={`flex-1 text-sm ${
            theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
          }`}>John Doe</span>
          <Settings className={`w-4 h-4 ${
            theme === 'dark' ? 'text-[#64748B]' : 'text-[#94A3B8]'
          }`} />
        </div>
      </div>
    </div>
  );
}

function NavItem({
  item,
}: {
  item: { name: string; path: string; icon: any };
}) {
  const { theme } = useTheme();
  const Icon = item.icon;

  return (
    <NavLink
      to={item.path}
      end={item.path === '/'}
      className={({ isActive }) => `
        w-full flex items-center gap-[14px] h-12 px-4 rounded-lg transition-all duration-150
        ${isActive
          ? `${
              theme === 'dark'
                ? 'bg-[rgba(212,175,55,0.15)] text-[#F5F5F0]'
                : 'bg-[rgba(44,95,141,0.1)] text-[#0F172A]'
            } border-l-[3px] border-[#D4AF37]`
          : `${
              theme === 'dark'
                ? 'text-[#94A3B8] hover:bg-[rgba(212,175,55,0.08)]'
                : 'text-[#64748B] hover:bg-[#F9FAFB]'
            }`
        }
      `}
    >
      {({ isActive }) => (
        <>
          <Icon
            className={`w-[22px] h-[22px] ${
              isActive
                ? 'text-[#D4AF37]'
                : theme === 'dark' ? 'text-[#64748B]' : 'text-[#94A3B8]'
            }`}
            strokeWidth={2}
          />
          <span className="text-sm font-medium">{item.name}</span>
        </>
      )}
    </NavLink>
  );
}
