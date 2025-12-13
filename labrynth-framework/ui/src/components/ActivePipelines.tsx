import { ChevronRight, Sparkles } from 'lucide-react';
import { useThemeColors } from '../hooks/useThemeColors';

const pipelines = [
  {
    name: 'Data Ingestion Pipeline',
    lastRun: '2 min ago',
    status: 'running',
    selfHealing: true,
    statusColor: '#3B82F6',
  },
  {
    name: 'ML Training Pipeline',
    lastRun: '1 hour ago',
    status: 'success',
    selfHealing: true,
    statusColor: '#10B981',
  },
  {
    name: 'Report Generation',
    lastRun: '3 hours ago',
    status: 'failed',
    selfHealing: false,
    statusColor: '#EF4444',
  },
];

export function ActivePipelines() {
  const { classes } = useThemeColors();
  
  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl overflow-hidden`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-5 border-b ${classes.borderCard}`}>
        <h3 className={`text-base font-semibold ${classes.textPrimary}`}>Active Pipelines</h3>
        <button className="flex items-center gap-1 text-sm text-[#8B5CF6] hover:text-[#A78BFA] transition-colors">
          View All
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Pipeline List */}
      <div className={`divide-y ${classes.borderCard}`}>
        {pipelines.map((pipeline, index) => (
          <div 
            key={index}
            className={`p-4 ${classes.bgHover} transition-colors cursor-pointer`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1">
                <div 
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: pipeline.statusColor }}
                ></div>
                <div>
                  <div className={`text-sm font-medium mb-1 ${classes.textPrimary}`}>
                    {pipeline.name}
                  </div>
                  <div className={`flex items-center gap-3 text-xs ${classes.textMuted}`}>
                    <span>Last run: {pipeline.lastRun}</span>
                    {pipeline.selfHealing && (
                      <span className="flex items-center gap-1 px-2 py-0.5 bg-[rgba(139,92,246,0.2)] text-[#A78BFA] rounded-full">
                        <Sparkles className="w-3 h-3" />
                        Self-Healing
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <StatusBadge status={pipeline.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const configs = {
    running: { 
      label: 'Running', 
      bgColor: '#3B82F6', 
      icon: '●',
      animate: true 
    },
    success: { 
      label: 'Success', 
      bgColor: '#10B981', 
      icon: '✓',
      animate: false 
    },
    failed: { 
      label: 'Failed', 
      bgColor: '#EF4444', 
      icon: '✕',
      animate: false 
    },
  };

  const config = configs[status as keyof typeof configs];

  return (
    <span 
      className={`px-3 py-1 rounded-full text-xs font-medium text-white flex items-center gap-1 ${
        config.animate ? 'animate-pulse' : ''
      }`}
      style={{ backgroundColor: config.bgColor }}
    >
      {config.label} {config.icon}
    </span>
  );
}