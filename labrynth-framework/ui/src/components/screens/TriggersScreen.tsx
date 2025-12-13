import { Search, ChevronDown, Plus, Clock, Zap, Folder, Hand } from 'lucide-react';
import { useState } from 'react';

const triggers = [
  {
    icon: Clock,
    iconColor: '#3B82F6',
    name: 'Daily Morning Sync',
    type: 'Scheduled',
    schedule: 'Every day at 6:00 AM UTC',
    pipeline: 'Data Ingestion Pipeline',
    nextRun: 'Tomorrow at 6:00 AM',
    lastRun: 'Today at 6:00 AM',
    enabled: true,
  },
  {
    icon: Clock,
    iconColor: '#3B82F6',
    name: 'Weekly Model Retrain',
    type: 'Scheduled',
    schedule: 'Every Sunday at 2:00 AM UTC',
    pipeline: 'ML Training Pipeline',
    nextRun: 'Sunday at 2:00 AM',
    lastRun: 'Last Sunday',
    enabled: true,
  },
  {
    icon: Zap,
    iconColor: '#F59E0B',
    name: 'Webhook: New Customer',
    type: 'Event-based',
    event: 'POST /webhooks/new-customer',
    pipeline: 'Customer Onboarding Flow',
    triggered: '47 times today',
    enabled: true,
  },
  {
    icon: Folder,
    iconColor: '#10B981',
    name: 'File Upload Trigger',
    type: 'Event-based',
    event: 'New file in S3://data-bucket/incoming/',
    pipeline: 'File Processing Pipeline',
    status: 'Disabled',
    enabled: false,
  },
  {
    icon: Hand,
    iconColor: '#64748B',
    name: 'Manual Trigger',
    type: 'Manual',
    description: 'On-demand execution',
    pipeline: 'Report Generation',
    enabled: true,
  },
];

export function TriggersScreen() {
  const [activeTab, setActiveTab] = useState('all');

  const tabs = [
    { key: 'all', label: 'All', count: 8 },
    { key: 'scheduled', label: 'Scheduled', count: 5 },
    { key: 'event', label: 'Event-based', count: 2 },
    { key: 'manual', label: 'Manual', count: 1 },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-[#F8FAFC] mb-1">Triggers</h1>
        <p className="text-sm text-[#94A3B8]">Configure pipeline execution schedules and events</p>
      </div>

      {/* Search and Actions Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
            <input
              type="text"
              placeholder="Search triggers..."
              className="w-full bg-[#0F172A] border border-[rgba(148,163,184,0.2)] rounded-lg pl-10 pr-4 py-2 text-sm text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#8B5CF6] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
            />
          </div>

          <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
            Type
            <ChevronDown className="w-4 h-4" />
          </button>

          <button className="flex items-center gap-2 px-3 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
            Pipeline
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>

        <button className="flex items-center gap-2 bg-[#8B5CF6] hover:bg-[#7C3AED] text-white px-4 py-2 rounded-lg transition-colors text-sm">
          <Plus className="w-4 h-4" />
          New Trigger
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

      {/* Triggers List */}
      <div className="space-y-4">
        {triggers.map((trigger, index) => (
          <TriggerCard key={index} trigger={trigger} />
        ))}
      </div>
    </div>
  );
}

function TriggerCard({ trigger }: { trigger: any }) {
  const Icon = trigger.icon;

  return (
    <div className="bg-[#1E293B] border border-[rgba(148,163,184,0.1)] rounded-xl p-5 hover:bg-[rgba(255,255,255,0.02)] transition-all">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4 flex-1">
          <div 
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ backgroundColor: `${trigger.iconColor}20` }}
          >
            <Icon className="w-5 h-5" style={{ color: trigger.iconColor }} />
          </div>
          
          <div className="flex-1">
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-2">{trigger.name}</h3>
            
            <div className="space-y-1 text-sm text-[#94A3B8]">
              {trigger.schedule && (
                <p>Schedule: {trigger.schedule}</p>
              )}
              {trigger.event && (
                <p>Event: {trigger.event}</p>
              )}
              {trigger.description && (
                <p>Type: {trigger.description}</p>
              )}
              <p>Pipeline: {trigger.pipeline}</p>
              {trigger.nextRun && trigger.lastRun && (
                <p className="text-xs text-[#64748B]">
                  Next run: {trigger.nextRun} • Last run: {trigger.lastRun}
                </p>
              )}
              {trigger.triggered && (
                <p className="text-xs text-[#64748B]">
                  Triggered: {trigger.triggered}
                </p>
              )}
              {trigger.status && (
                <p className="text-xs text-[#64748B]">
                  Status: {trigger.status}
                </p>
              )}
            </div>

            {trigger.type === 'Manual' && (
              <button className="mt-3 px-3 py-1.5 text-xs bg-[#8B5CF6] hover:bg-[#7C3AED] text-white rounded-lg transition-colors">
                Run Now
              </button>
            )}
          </div>
        </div>

        {/* Toggle Switch */}
        <div className="flex items-center gap-2">
          <div 
            className={`relative w-12 h-6 rounded-full cursor-pointer transition-colors ${
              trigger.enabled ? 'bg-[#10B981]' : 'bg-[rgba(255,255,255,0.1)]'
            }`}
          >
            <div 
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                trigger.enabled ? 'translate-x-7' : 'translate-x-1'
              }`}
            ></div>
          </div>
          <span className={`text-xs font-medium ${
            trigger.enabled ? 'text-[#10B981]' : 'text-[#64748B]'
          }`}>
            {trigger.enabled ? 'ON' : 'OFF'}
          </span>
          {trigger.enabled && (
            <div className="w-2 h-2 bg-[#10B981] rounded-full"></div>
          )}
        </div>
      </div>
    </div>
  );
}
