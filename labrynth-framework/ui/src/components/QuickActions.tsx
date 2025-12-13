import { Play, Pause, FileText, Sparkles } from 'lucide-react';
import { useThemeColors } from '../hooks/useThemeColors';

const actions = [
  { icon: Play, label: 'Run All', color: '#3B82F6' },
  { icon: Pause, label: 'Pause All', color: '#F59E0B' },
  { icon: FileText, label: 'View Logs', color: '#64748B' },
  { icon: Sparkles, label: 'AI Insight', color: '#8B5CF6' },
];

export function QuickActions() {
  const { classes } = useThemeColors();
  
  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl overflow-hidden`}>
      {/* Header */}
      <div className={`p-5 border-b ${classes.borderCard}`}>
        <h3 className={`text-base font-semibold ${classes.textPrimary}`}>Quick Actions</h3>
      </div>

      {/* Actions Grid */}
      <div className="p-5">
        <div className="grid grid-cols-2 gap-3">
          {actions.map((action, index) => {
            const Icon = action.icon;
            return (
              <button
                key={index}
                className={`flex flex-col items-center justify-center gap-2 p-4 border border-dashed rounded-lg transition-all duration-150 group ${
                  classes.borderInput.replace('border-', 'border-dashed border-')
                } ${classes.bgHover}`}
              >
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-transform group-hover:scale-110"
                  style={{ backgroundColor: `${action.color}20` }}
                >
                  <Icon className="w-5 h-5" style={{ color: action.color }} />
                </div>
                <span className={`text-xs font-medium ${classes.textSecondary}`}>
                  {action.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}