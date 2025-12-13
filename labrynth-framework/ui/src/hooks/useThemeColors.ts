import { useTheme } from '../App';

export function useThemeColors() {
  const { theme } = useTheme();

  return {
    // Backgrounds
    bgBase: theme === 'dark' ? '#0B1120' : '#F1F5F9',
    bgSidebar: theme === 'dark' ? '#0F172A' : '#FFFFFF',
    bgCard: theme === 'dark' ? '#1E293B' : '#FFFFFF',
    bgHover: theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#F1F5F9',
    bgActive: 'rgba(139,92,246,0.1)',
    bgInput: theme === 'dark' ? '#0F172A' : '#F8FAFC',

    // Borders
    borderDefault: theme === 'dark' ? 'rgba(148,163,184,0.1)' : '#E2E8F0',
    borderHover: theme === 'dark' ? 'rgba(148,163,184,0.2)' : '#CBD5E1',
    borderActive: '#8B5CF6',

    // Text
    textPrimary: theme === 'dark' ? '#F8FAFC' : '#0F172A',
    textSecondary: theme === 'dark' ? '#94A3B8' : '#64748B',
    textMuted: '#64748B',

    // Classes for easier use in Tailwind
    classes: {
      bgCard: theme === 'dark' ? 'bg-[#1E293B]' : 'bg-white',
      borderCard: theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]',
      textPrimary: theme === 'dark' ? 'text-[#F8FAFC]' : 'text-[#0F172A]',
      textSecondary: theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]',
      textMuted: 'text-[#64748B]',
      bgHover: theme === 'dark' ? 'hover:bg-[rgba(255,255,255,0.05)]' : 'hover:bg-[#F1F5F9]',
      bgInput: theme === 'dark' ? 'bg-[#0F172A]' : 'bg-[#F8FAFC]',
      borderInput: theme === 'dark' ? 'border-[rgba(148,163,184,0.2)]' : 'border-[#E2E8F0]',
    }
  };
}
