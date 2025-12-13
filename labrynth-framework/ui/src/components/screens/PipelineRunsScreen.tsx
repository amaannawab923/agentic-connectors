import { Search, ChevronDown, Download, Calendar } from 'lucide-react';
import { useState } from 'react';

const runs = [
  {
    id: 1247,
    pipeline: 'Data Ingestion Pipeline',
    startedAgo: '2 min ago',
    duration: 'Running...',
    status: 'running',
    statusColor: '#3B82F6',
    trigger: 'Scheduled',
    agent: 'Agent A',
    date: 'today',
  },
  {
    id: 1246,
    pipeline: 'ML Training Pipeline',
    startedAgo: '1 hour ago',
    duration: '12m 45s',
    status: 'success',
    statusColor: '#10B981',
    trigger: 'Scheduled',
    agent: 'Agent B',
    date: 'today',
  },
  {
    id: 1245,
    pipeline: 'Report Generation',
    startedAgo: '3 hours ago',
    duration: '1m 12s',
    status: 'failed',
    statusColor: '#EF4444',
    trigger: 'Manual',
    error: 'API timeout',
    aiFix: true,
    date: 'today',
  },
  {
    id: 1244,
    pipeline: 'Data Ingestion Pipeline',
    startedAgo: 'Yesterday 6:00 AM',
    duration: '2m 34s',
    status: 'success',
    statusColor: '#10B981',
    trigger: 'Scheduled',
    agent: 'Agent A',
    date: 'yesterday',
  },
];

export function PipelineRunsScreen() {
  const [selectedRun, setSelectedRun] = useState<any>(null);

  const groupedRuns = {
    today: runs.filter(r => r.date === 'today'),
    yesterday: runs.filter(r => r.date === 'yesterday'),
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-[#F8FAFC] mb-1">Pipeline Runs</h1>
        <p className="text-sm text-[#94A3B8]">Execution history and logs</p>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
          <input
            type="text"
            placeholder="Search runs..."
            className="w-full bg-[#0F172A] border border-[rgba(148,163,184,0.2)] rounded-lg pl-10 pr-4 py-2 text-sm text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#8B5CF6] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
          />
        </div>

        <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
          Status
          <ChevronDown className="w-4 h-4" />
        </button>

        <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
          Pipeline
          <ChevronDown className="w-4 h-4" />
        </button>

        <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
          <Calendar className="w-4 h-4" />
          Date Range
        </button>

        <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors ml-auto">
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {/* Runs List */}
      <div className="space-y-6">
        {/* Today */}
        <div>
          <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider mb-3">TODAY</h3>
          <div className="space-y-3">
            {groupedRuns.today.map((run) => (
              <RunCard key={run.id} run={run} onViewLogs={() => setSelectedRun(run)} />
            ))}
          </div>
        </div>

        {/* Yesterday */}
        <div>
          <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider mb-3">YESTERDAY</h3>
          <div className="space-y-3">
            {groupedRuns.yesterday.map((run) => (
              <RunCard key={run.id} run={run} onViewLogs={() => setSelectedRun(run)} />
            ))}
          </div>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between pt-4 border-t border-[rgba(148,163,184,0.1)]">
        <span className="text-sm text-[#64748B]">Showing 1-20 of 1,247 runs</span>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors">← Prev</button>
          <button className="px-3 py-1.5 text-sm bg-[#8B5CF6] text-white rounded">1</button>
          <button className="px-3 py-1.5 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors">2</button>
          <button className="px-3 py-1.5 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors">3</button>
          <button className="px-3 py-1.5 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors">Next →</button>
        </div>
      </div>

      {/* Log Detail Modal */}
      {selectedRun && (
        <LogDetailModal run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
    </div>
  );
}

function RunCard({ run, onViewLogs }: { run: any; onViewLogs: () => void }) {
  const statusConfig = {
    running: { label: 'Running', icon: '●' },
    success: { label: 'Success', icon: '✓' },
    failed: { label: 'Failed', icon: '✕' },
  };

  const config = statusConfig[run.status as keyof typeof statusConfig];

  return (
    <div className="bg-[#1E293B] border border-[rgba(148,163,184,0.1)] rounded-xl p-4 hover:bg-[rgba(255,255,255,0.02)] transition-all">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-mono text-[#64748B]">#{run.id}</span>
            <span className="text-base font-semibold text-[#F8FAFC]">{run.pipeline}</span>
          </div>
          
          <div className="flex items-center gap-3 text-sm text-[#94A3B8] mb-1">
            <span>Started: {run.startedAgo}</span>
            <span>•</span>
            <span>Duration: {run.duration}</span>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#64748B]">
            <span>Trigger: {run.trigger}</span>
            {run.agent && (
              <>
                <span>•</span>
                <span>Agent: {run.agent}</span>
              </>
            )}
            {run.error && (
              <>
                <span>•</span>
                <span>Error: {run.error}</span>
              </>
            )}
          </div>

          {run.aiFix && (
            <div className="mt-2 text-xs text-[#A78BFA] flex items-center gap-1">
              ✨ AI Fix Available
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span 
            className={`px-3 py-1 rounded-full text-xs font-medium text-white flex items-center gap-1 ${
              run.status === 'running' ? 'animate-pulse' : ''
            }`}
            style={{ backgroundColor: run.statusColor }}
          >
            {config.label} {config.icon}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[rgba(148,163,184,0.1)]">
        <button
          onClick={onViewLogs}
          className="px-3 py-1.5 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors"
        >
          View Logs
        </button>
        {run.status === 'running' ? (
          <button className="px-3 py-1.5 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors">
            Stop
          </button>
        ) : (
          <button className="px-3 py-1.5 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors">
            Rerun
          </button>
        )}
      </div>
    </div>
  );
}

function LogDetailModal({ run, onClose }: { run: any; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState('logs');

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-[#1E293B] rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-[rgba(148,163,184,0.1)]">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-[#F8FAFC] mb-2">
                Run #{run.id} - {run.pipeline}
              </h2>
              <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <div>
                  <span className="text-[#64748B]">Status: </span>
                  <span className="text-[#F8FAFC] font-medium">{run.status} {run.status === 'failed' ? '✕' : '✓'}</span>
                </div>
                <div>
                  <span className="text-[#64748B]">Started: </span>
                  <span className="text-[#F8FAFC]">{run.startedAgo}</span>
                </div>
                <div>
                  <span className="text-[#64748B]">Duration: </span>
                  <span className="text-[#F8FAFC]">{run.duration}</span>
                </div>
                <div>
                  <span className="text-[#64748B]">Trigger: </span>
                  <span className="text-[#F8FAFC]">{run.trigger}</span>
                </div>
                {run.agent && (
                  <div>
                    <span className="text-[#64748B]">Agent: </span>
                    <span className="text-[#F8FAFC]">{run.agent}</span>
                  </div>
                )}
                {run.error && (
                  <div>
                    <span className="text-[#64748B]">Error: </span>
                    <span className="text-[#EF4444]">{run.error}</span>
                  </div>
                )}
              </div>
            </div>
            <button 
              onClick={onClose}
              className="text-[#64748B] hover:text-[#F8FAFC] transition-colors text-xl"
            >
              ✕
            </button>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 border-b border-[rgba(148,163,184,0.1)] -mb-px">
            {['Overview', 'Logs', 'Errors', 'AI Analysis'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab.toLowerCase())}
                className={`px-4 py-2 text-sm font-medium transition-colors relative ${
                  activeTab === tab.toLowerCase()
                    ? 'text-[#F8FAFC]'
                    : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                {tab}
                {activeTab === tab.toLowerCase() && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#8B5CF6]"></div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'logs' && (
            <div>
              <h3 className="text-sm font-semibold text-[#F8FAFC] mb-3 uppercase tracking-wider">Logs</h3>
              <div className="bg-[#0B1120] rounded-lg p-4 font-mono text-xs space-y-1">
                <div className="text-[#64748B]">10:32:01  <span className="text-[#3B82F6]">INFO</span>   <span className="text-[#94A3B8]">Starting pipeline execution</span></div>
                <div className="text-[#64748B]">10:32:01  <span className="text-[#3B82F6]">INFO</span>   <span className="text-[#94A3B8]">Step 1: Initialize - Started</span></div>
                <div className="text-[#64748B]">10:32:01  <span className="text-[#3B82F6]">INFO</span>   <span className="text-[#94A3B8]">Step 1: Initialize - Completed</span></div>
                <div className="text-[#64748B]">10:32:02  <span className="text-[#3B82F6]">INFO</span>   <span className="text-[#94A3B8]">Step 2: Fetch Data - Started</span></div>
                <div className="text-[#64748B]">10:32:47  <span className="text-[#3B82F6]">INFO</span>   <span className="text-[#94A3B8]">Step 2: Fetch Data - Fetched 1,247 records</span></div>
                <div className="text-[#64748B]">10:32:47  <span className="text-[#3B82F6]">INFO</span>   <span className="text-[#94A3B8]">Step 3: Transform - Started</span></div>
                <div className="text-[#64748B]">10:33:14  <span className="text-[#EF4444]">ERROR</span>  <span className="text-[#94A3B8]">Step 3: Transform - API timeout after 30s</span></div>
                <div className="text-[#64748B]">10:33:14  <span className="text-[#EF4444]">ERROR</span>  <span className="text-[#94A3B8]">Pipeline failed at step 3</span></div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[rgba(148,163,184,0.1)] flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors"
          >
            Close
          </button>
          <button className="px-4 py-2 text-sm bg-[#8B5CF6] hover:bg-[#7C3AED] text-white rounded-lg transition-colors">
            Retry Run
          </button>
        </div>
      </div>
    </div>
  );
}
