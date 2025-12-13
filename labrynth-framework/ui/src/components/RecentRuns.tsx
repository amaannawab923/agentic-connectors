import { ChevronRight } from 'lucide-react';
import { useThemeColors } from '../hooks/useThemeColors';

const runs = [
  {
    name: 'Data Ingestion Pipeline',
    duration: '2m 34s',
    timeAgo: '5 min ago',
    status: 'success',
    statusColor: '#10B981',
  },
  {
    name: 'ML Training Pipeline',
    duration: '12m 18s',
    timeAgo: '1 hour ago',
    status: 'success',
    statusColor: '#10B981',
  },
  {
    name: 'Report Generation',
    duration: '4m 52s',
    timeAgo: '3 hours ago',
    status: 'failed',
    statusColor: '#EF4444',
  },
];

export function RecentRuns() {
  const { classes } = useThemeColors();
  
  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl overflow-hidden`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-5 border-b ${classes.borderCard}`}>
        <h3 className={`text-base font-semibold ${classes.textPrimary}`}>Recent Runs</h3>
        <button className="flex items-center gap-1 text-sm text-[#8B5CF6] hover:text-[#A78BFA] transition-colors">
          View All
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Runs List */}
      <div className={`divide-y ${classes.borderCard}`}>
        {runs.map((run, index) => (
          <div 
            key={index}
            className={`p-4 ${classes.bgHover} transition-colors cursor-pointer`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1">
                <div 
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: run.statusColor }}
                ></div>
                <div>
                  <div className={`text-sm font-medium mb-1 ${classes.textPrimary}`}>
                    {run.name}
                  </div>
                  <div className={`flex items-center gap-3 text-xs ${classes.textMuted}`}>
                    <span>Duration: {run.duration}</span>
                    <span>•</span>
                    <span>{run.timeAgo}</span>
                  </div>
                </div>
              </div>

              <span 
                className="px-3 py-1 rounded-full text-xs font-medium text-white"
                style={{ backgroundColor: run.statusColor }}
              >
                {run.status === 'success' ? 'Success ✓' : 'Failed ✕'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}