import { MoreVertical, Play, Copy, Download, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTheme } from '../../App';
import { MockWorkflow } from '../../data/mockWorkflows';

interface WorkflowCardProps {
  workflow: MockWorkflow;
  onClick: () => void;
}

export function WorkflowCard({ workflow, onClick }: WorkflowCardProps) {
  const { theme } = useTheme();
  const [showMenu, setShowMenu] = useState(false);

  const statusConfig = {
    running: { color: '#3B82F6', label: 'Running', dot: true },
    success: { color: '#10B981', label: 'Success', dot: false },
    draft: { color: '#64748B', label: 'Draft', dot: false },
    failed: { color: '#EF4444', label: 'Failed', dot: true },
    stopped: { color: '#64748B', label: 'Stopped', dot: false },
  };

  const status = statusConfig[workflow.status];

  return (
    <div
      onClick={onClick}
      className={`group relative rounded-xl p-5 border transition-all duration-200 cursor-pointer hover:-translate-y-1 hover:shadow-xl ${
        theme === 'dark'
          ? 'bg-[#1A2642] border-[rgba(212,175,55,0.2)] hover:border-[#D4AF37]'
          : 'bg-white border-[#E5E7EB] hover:border-[#2C5F8D]'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          {/* Icon */}
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#D4AF37] to-[#B8860B] flex items-center justify-center text-xl flex-shrink-0 shadow-lg shadow-[rgba(212,175,55,0.2)]">
            {workflow.icon}
          </div>

          {/* Name */}
          <div className="flex-1 min-w-0">
            <h3 className={`font-semibold truncate mb-1 ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
            }`}>
              {workflow.name}
            </h3>
            <p className={`text-xs line-clamp-2 ${
              theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
            }`}>
              {workflow.description}
            </p>
          </div>
        </div>

        {/* More Menu */}
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className={`p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-all ${
              theme === 'dark'
                ? 'hover:bg-[rgba(212,175,55,0.1)]'
                : 'hover:bg-[#F9FAFB]'
            }`}
          >
            <MoreVertical className="w-4 h-4" style={{ color: theme === 'dark' ? '#94A3B8' : '#64748B' }} />
          </button>

          {/* Dropdown Menu */}
          {showMenu && (
            <div
              className={`absolute right-0 mt-1 w-40 rounded-lg shadow-lg border z-10 ${
                theme === 'dark'
                  ? 'bg-[#1A2642] border-[rgba(212,175,55,0.2)]'
                  : 'bg-white border-[#E5E7EB]'
              }`}
              onClick={(e) => e.stopPropagation()}
            >
              <MenuItem icon={<Play className="w-4 h-4" />} label="Run" />
              <MenuItem icon={<Copy className="w-4 h-4" />} label="Duplicate" />
              <MenuItem icon={<Download className="w-4 h-4" />} label="Export DSL" />
              <div className={`h-px my-1 ${
                theme === 'dark' ? 'bg-[rgba(212,175,55,0.2)]' : 'bg-[#E5E7EB]'
              }`}></div>
              <MenuItem icon={<Trash2 className="w-4 h-4" />} label="Delete" danger />
            </div>
          )}
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {workflow.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              backgroundColor: theme === 'dark' ? 'rgba(212,175,55,0.15)' : 'rgba(44,95,141,0.1)',
              color: theme === 'dark' ? '#D4AF37' : '#2C5F8D',
            }}
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Divider */}
      <div className={`h-px mb-3 ${
        theme === 'dark' ? 'bg-[rgba(212,175,55,0.2)]' : 'bg-[#E5E7EB]'
      }`}></div>

      {/* Status Row */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <div
              className={`w-2 h-2 rounded-full ${status.dot ? 'animate-pulse' : ''}`}
              style={{ backgroundColor: status.color }}
            ></div>
            <span style={{ color: status.color }}>{status.label}</span>
          </div>
          <span className={theme === 'dark' ? 'text-[#64748B]' : 'text-[#94A3B8]'}>•</span>
          <span className={theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'}>
            {workflow.lastRun || 'Never'}
          </span>
        </div>
      </div>

      <div className={`flex items-center gap-3 mt-2 text-xs ${
        theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
      }`}>
        <span>{workflow.runCount.toLocaleString()} runs</span>
        <span>•</span>
        <span>{workflow.successRate}% success</span>
      </div>
    </div>
  );
}

function MenuItem({ icon, label, danger = false }: { icon: React.ReactNode; label: string; danger?: boolean }) {
  const { theme } = useTheme();

  return (
    <button
      className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
        danger
          ? 'text-[#EF4444] hover:bg-[rgba(239,68,68,0.1)]'
          : theme === 'dark'
          ? 'text-[#F5F5F0] hover:bg-[rgba(212,175,55,0.1)]'
          : 'text-[#0F172A] hover:bg-[#F9FAFB]'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
