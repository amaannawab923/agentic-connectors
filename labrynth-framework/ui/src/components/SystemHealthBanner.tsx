import { Sparkles, ChevronRight } from 'lucide-react';
import { useTheme } from '../App';

export function SystemHealthBanner() {
  const { theme } = useTheme();
  
  return (
    <div className={`relative rounded-xl p-6 overflow-hidden ${
      theme === 'dark'
        ? 'bg-gradient-to-r from-[#1A2642] to-[#2C5F8D]'
        : 'bg-gradient-to-r from-[#2C5F8D] to-[#4A90C8]'
    }`}>
      {/* Greek pattern overlay */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `repeating-linear-gradient(90deg, transparent, transparent 10px, ${theme === 'dark' ? '#D4AF37' : '#fff'} 10px, ${theme === 'dark' ? '#D4AF37' : '#fff'} 11px)`,
        }}></div>
      </div>
      
      <div className="relative flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Sparkles className={`w-6 h-6 ${
            theme === 'dark' ? 'text-[#D4AF37]' : 'text-white'
          }`} />
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className={`text-lg font-semibold ${
                theme === 'dark' ? 'text-[#F5F5F0]' : 'text-white'
              }`}>AIM System Health</h2>
              <div className="relative">
                <div className="w-3 h-3 bg-[#10B981] rounded-full animate-pulse"></div>
                <div className="absolute inset-0 w-3 h-3 bg-[#10B981] rounded-full animate-ping opacity-75"></div>
              </div>
            </div>
            <p className={`text-sm ${
              theme === 'dark' ? 'text-[#94A3B8]' : 'text-white/90'
            }`}>
              All systems operational • <span className={
                theme === 'dark' ? 'text-[#D4AF37]' : 'text-white font-medium'
              }>34 issues auto-resolved today</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Progress Bar */}
          <div className="flex flex-col items-end gap-2">
            <span className={`text-2xl font-bold ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-white'
            }`}>98%</span>
            <div className={`w-32 h-2 rounded-full overflow-hidden ${
              theme === 'dark' ? 'bg-[rgba(255,255,255,0.1)]' : 'bg-white/20'
            }`}>
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  theme === 'dark'
                    ? 'bg-gradient-to-r from-[#D4AF37] to-[#B8860B]'
                    : 'bg-white'
                }`}
                style={{ width: '98%' }}
              ></div>
            </div>
          </div>

          {/* View Details Button */}
          <button className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${
            theme === 'dark'
              ? 'bg-[rgba(212,175,55,0.2)] hover:bg-[rgba(212,175,55,0.3)] text-[#D4AF37] border border-[rgba(212,175,55,0.3)]'
              : 'bg-white/20 hover:bg-white/30 text-white border border-white/30'
          }`}>
            View Details
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}