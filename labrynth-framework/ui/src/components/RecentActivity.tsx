import { Play, Sparkles, CheckCircle } from 'lucide-react';
import { useThemeColors } from '../hooks/useThemeColors';

const activities = [
  {
    icon: Play,
    iconColor: '#3B82F6',
    title: 'Pipeline started',
    description: 'Data Ingestion Pipeline',
    timeAgo: '2 min ago',
  },
  {
    icon: Sparkles,
    iconColor: '#8B5CF6',
    title: 'AI fixed error',
    description: 'Report Generation',
    timeAgo: '1 hour ago',
  },
  {
    icon: CheckCircle,
    iconColor: '#10B981',
    title: 'Pipeline completed',
    description: 'ML Training Pipeline',
    timeAgo: '1 hour ago',
  },
];

export function RecentActivity() {
  const { classes } = useThemeColors();
  
  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl overflow-hidden`}>
      {/* Header */}
      <div className={`p-5 border-b ${classes.borderCard}`}>
        <h3 className={`text-base font-semibold ${classes.textPrimary}`}>Recent Activity</h3>
      </div>

      {/* Activity List */}
      <div className="p-5 space-y-4">
        {activities.map((activity, index) => {
          const Icon = activity.icon;
          return (
            <div key={index} className="relative pl-8">
              {/* Timeline Line */}
              {index < activities.length - 1 && (
                <div className={`absolute left-[11px] top-8 w-px h-8 ${
                  classes.borderCard.replace('border-', 'bg-')
                }`}></div>
              )}
              
              {/* Icon */}
              <div 
                className="absolute left-0 top-0 w-6 h-6 rounded-full flex items-center justify-center"
                style={{ backgroundColor: `${activity.iconColor}20` }}
              >
                <Icon className="w-3.5 h-3.5" style={{ color: activity.iconColor }} />
              </div>

              {/* Content */}
              <div>
                <div className={`text-sm font-medium mb-0.5 ${classes.textPrimary}`}>
                  {activity.title}
                </div>
                <div className={`text-sm mb-1 ${classes.textSecondary}`}>
                  {activity.description}
                </div>
                <div className={`text-xs ${classes.textMuted}`}>
                  {activity.timeAgo}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}