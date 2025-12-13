import { GitBranch, CheckCircle, Sparkles, Clock } from 'lucide-react';
import { useThemeColors } from '../hooks/useThemeColors';

const stats = [
  {
    icon: GitBranch,
    number: '12',
    label: 'Active Pipelines',
    trend: '↑ +2 today',
    trendPositive: true,
    accentColor: '#3B82F6',
  },
  {
    icon: CheckCircle,
    number: '847',
    label: 'Successful Runs',
    trend: '↑ +15% vs last week',
    trendPositive: true,
    accentColor: '#10B981',
  },
  {
    icon: Sparkles,
    number: '34',
    label: 'Issues Resolved',
    trend: 'by AI ✨',
    trendPositive: null,
    accentColor: '#8B5CF6',
  },
  {
    icon: Clock,
    number: '4.2m',
    label: 'Avg Duration',
    trend: '↓ -12% faster',
    trendPositive: true,
    accentColor: '#F59E0B',
  },
];

export function StatCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, index) => (
        <StatCard key={index} {...stat} />
      ))}
    </div>
  );
}

function StatCard({ 
  icon: Icon, 
  number, 
  label, 
  trend, 
  trendPositive, 
  accentColor 
}: {
  icon: any;
  number: string;
  label: string;
  trend: string;
  trendPositive: boolean | null;
  accentColor: string;
}) {
  const { classes } = useThemeColors();
  
  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl p-5 hover:translate-y-[-2px] hover:shadow-lg transition-all duration-150`}>
      <div 
        className="w-10 h-10 rounded-full flex items-center justify-center mb-4"
        style={{ backgroundColor: `${accentColor}20` }}
      >
        <Icon className="w-5 h-5" style={{ color: accentColor }} />
      </div>
      
      <div className={`text-[32px] font-bold mb-1 ${classes.textPrimary}`}>{number}</div>
      <div className={`text-sm ${classes.textMuted} mb-2`}>{label}</div>
      
      <div 
        className={`text-xs font-medium ${
          trendPositive === true 
            ? 'text-[#10B981]' 
            : trendPositive === false 
            ? 'text-[#EF4444]' 
            : 'text-[#A78BFA]'
        }`}
      >
        {trend}
      </div>
    </div>
  );
}