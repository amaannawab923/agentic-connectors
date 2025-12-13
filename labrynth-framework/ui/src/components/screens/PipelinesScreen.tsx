import { Search, Filter, ChevronDown, Plus, ChevronRight, ChevronLeft, Sparkles, MoreVertical } from 'lucide-react';
import { useState } from 'react';

const pipelines = [
  {
    name: 'Data Ingestion Pipeline',
    description: 'ETL pipeline for customer data from Salesforce',
    lastRun: '2 min ago',
    runs: 847,
    status: 'running',
    statusColor: '#3B82F6',
    selfHealing: true,
    errors: 0,
  },
  {
    name: 'ML Training Pipeline',
    description: 'Weekly model retraining pipeline',
    lastRun: '1 hour ago',
    runs: 156,
    status: 'success',
    statusColor: '#10B981',
    selfHealing: true,
    errors: 0,
  },
  {
    name: 'Report Generation',
    description: 'Daily report generation for finance team',
    lastRun: '3 hours ago',
    runs: 89,
    status: 'failed',
    statusColor: '#EF4444',
    selfHealing: false,
    errors: 2,
  },
  {
    name: 'ETL Processing',
    description: 'Legacy data transformation pipeline',
    lastRun: '5 hours ago',
    runs: 1203,
    status: 'stopped',
    statusColor: '#64748B',
    selfHealing: false,
    errors: 0,
  },
];

export function PipelinesScreen() {
  const [activeTab, setActiveTab] = useState('all');

  const tabs = [
    { key: 'all', label: 'All', count: 12 },
    { key: 'running', label: 'Running', count: 3 },
    { key: 'stopped', label: 'Stopped', count: 7 },
    { key: 'failed', label: 'Failed', count: 2 },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-[#F8FAFC] mb-1">Pipelines</h1>
        <p className="text-sm text-[#94A3B8]">Manage your data pipelines</p>
      </div>

      {/* Search and Actions Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
            <input
              type="text"
              placeholder="Search pipelines..."
              className="w-full bg-[#0F172A] border border-[rgba(148,163,184,0.2)] rounded-lg pl-10 pr-4 py-2 text-sm text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#8B5CF6] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
            />
          </div>

          <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
            <Filter className="w-4 h-4" />
            Filter
            <ChevronDown className="w-4 h-4" />
          </button>

          <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
            Sort
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>

        <button className="flex items-center gap-2 bg-[#8B5CF6] hover:bg-[#7C3AED] text-white px-4 py-2 rounded-lg transition-colors text-sm">
          <Plus className="w-4 h-4" />
          Create Pipeline
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-[rgba(148,163,184,0.1)]">
        <div className="flex items-center gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium transition-colors relative ${
                activeTab === tab.key
                  ? 'text-[#F8FAFC]'
                  : 'text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
            >
              {tab.label} ({tab.count})
              {activeTab === tab.key && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#8B5CF6]"></div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Pipeline List */}
      <div className="space-y-4">
        {pipelines.map((pipeline, index) => (
          <PipelineCard key={index} pipeline={pipeline} />
        ))}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between pt-4 border-t border-[rgba(148,163,184,0.1)]">
        <span className="text-sm text-[#64748B]">Showing 1-10 of 12 pipelines</span>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors flex items-center gap-1">
            <ChevronLeft className="w-4 h-4" />
            Prev
          </button>
          <button className="px-3 py-1.5 text-sm bg-[#8B5CF6] text-white rounded">1</button>
          <button className="px-3 py-1.5 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors">2</button>
          <button className="px-3 py-1.5 text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-colors flex items-center gap-1">
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function PipelineCard({ pipeline }: { pipeline: any }) {
  const [isHovered, setIsHovered] = useState(false);

  const statusConfig = {
    running: { label: 'Running', icon: '●' },
    success: { label: 'Success', icon: '✓' },
    failed: { label: 'Failed', icon: '✕' },
    stopped: { label: 'Stopped', icon: '' },
  };

  const config = statusConfig[pipeline.status as keyof typeof statusConfig];

  return (
    <div
      className="bg-[#1E293B] border border-[rgba(148,163,184,0.1)] rounded-xl p-5 hover:bg-[rgba(255,255,255,0.02)] transition-all cursor-pointer"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-4 flex-1">
          <input
            type="checkbox"
            className="mt-1 w-4 h-4 rounded border-[rgba(148,163,184,0.3)] bg-transparent"
            onClick={(e) => e.stopPropagation()}
          />
          <div 
            className="w-2 h-2 rounded-full mt-1.5"
            style={{ backgroundColor: pipeline.statusColor }}
          ></div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-1">{pipeline.name}</h3>
            <p className="text-sm text-[#94A3B8] mb-3">{pipeline.description}</p>
            
            <div className="flex items-center gap-4 text-xs text-[#64748B]">
              <span>Last run: {pipeline.lastRun}</span>
              <span>•</span>
              <span>Runs: {pipeline.runs.toLocaleString()}</span>
              <span>•</span>
              {pipeline.selfHealing ? (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-[rgba(139,92,246,0.2)] text-[#A78BFA] rounded-full">
                  <Sparkles className="w-3 h-3" />
                  Self-Healing enabled
                </span>
              ) : pipeline.errors > 0 ? (
                <span className="text-[#F59E0B]">⚠️ {pipeline.errors} errors</span>
              ) : null}
            </div>
          </div>
        </div>

        <span 
          className={`px-3 py-1 rounded-full text-xs font-medium text-white flex items-center gap-1 ${
            pipeline.status === 'running' ? 'animate-pulse' : ''
          }`}
          style={{ backgroundColor: pipeline.statusColor }}
        >
          {config.label} {config.icon}
        </span>
      </div>

      {isHovered && (
        <div className="flex items-center gap-2 pt-3 border-t border-[rgba(148,163,184,0.1)] animate-in fade-in duration-150">
          <button className="px-3 py-1.5 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors">
            View
          </button>
          <button className="px-3 py-1.5 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors">
            Edit
          </button>
          <button className="px-3 py-1.5 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors">
            Duplicate
          </button>
          <button className="px-2 py-1.5 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors ml-auto">
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
