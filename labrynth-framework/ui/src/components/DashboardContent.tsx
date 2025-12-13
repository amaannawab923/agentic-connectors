import { SystemHealthBanner } from './SystemHealthBanner';
import { StatCards } from './StatCards';
import { ActivePipelines } from './ActivePipelines';
import { RecentRuns } from './RecentRuns';
import { RecentActivity } from './RecentActivity';
import { AgentPerformance } from './AgentPerformance';
import { QuickActions } from './QuickActions';

export function DashboardContent() {
  return (
    <div className="p-6 space-y-6">
      {/* System Health Banner */}
      <SystemHealthBanner />

      {/* Stat Cards */}
      <StatCards />

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivePipelines />
        <RecentRuns />
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <RecentActivity />
        <AgentPerformance />
        <QuickActions />
      </div>
    </div>
  );
}