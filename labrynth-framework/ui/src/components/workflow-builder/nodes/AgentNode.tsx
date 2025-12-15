import { Handle, Position, NodeProps } from '@xyflow/react';
import { MoreVertical } from 'lucide-react';
import { useTheme } from '../../../App';

export function AgentNode({ data, selected }: NodeProps) {
  const { theme } = useTheme();

  const statusColors = {
    idle: theme === 'dark' ? 'rgba(148, 163, 184, 0.2)' : '#E2E8F0',
    running: '#3B82F6',
    success: '#10B981',
    error: '#EF4444',
  };

  const status = data.status || 'idle';
  const borderColor = statusColors[status as keyof typeof statusColors];

  return (
    <div
      className={`w-[280px] rounded-xl border-2 transition-all ${
        theme === 'dark' ? 'bg-[#1E293B]' : 'bg-white'
      } ${selected ? 'shadow-xl shadow-purple-500/20' : ''}`}
      style={{
        borderColor: selected ? '#8B5CF6' : borderColor,
      }}
    >
      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-3 border-b ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white shadow-lg">
            {data.icon || '🤖'}
          </div>
          <span className={`font-medium text-sm ${
            theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
          }`}>
            {data.label}
          </span>
        </div>
        <button className={`p-1 rounded transition-colors ${
          theme === 'dark' ? 'hover:bg-[rgba(255,255,255,0.05)]' : 'hover:bg-[#F1F5F9]'
        }`}>
          <MoreVertical className="w-4 h-4 text-[#64748B]" />
        </button>
      </div>

      {/* Description */}
      {data.description && (
        <div className={`px-4 py-2 border-b ${
          theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
        }`}>
          <p className="text-xs text-[#94A3B8] line-clamp-2">{data.description}</p>
        </div>
      )}

      {/* Inputs */}
      {data.inputs && Object.keys(data.inputs).length > 0 && (
        <div className={`px-4 py-3 border-b ${
          theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
        }`}>
          <div className="text-xs font-medium text-[#64748B] uppercase mb-2">Inputs</div>
          {Object.entries(data.inputs).map(([name, config]: [string, any]) => (
            <div key={name} className="flex items-center gap-2 py-1 relative">
              <Handle
                type="target"
                position={Position.Left}
                id={`input-${name}`}
                className="!w-3 !h-3 !bg-blue-500 !border-2 !border-blue-300 !-left-[6px]"
              />
              <span className="text-xs text-[#94A3B8]">
                {name} ({config.type}){config.required && ' *'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Outputs */}
      {data.outputs && Object.keys(data.outputs).length > 0 && (
        <div className="px-4 py-3">
          <div className="text-xs font-medium text-[#64748B] uppercase mb-2">Outputs</div>
          {Object.entries(data.outputs).map(([name, config]: [string, any]) => (
            <div key={name} className="flex items-center justify-end gap-2 py-1 relative">
              <span className="text-xs text-[#94A3B8]">
                {name} ({config.type})
              </span>
              <Handle
                type="source"
                position={Position.Right}
                id={`output-${name}`}
                className="!w-3 !h-3 !bg-purple-500 !border-2 !border-purple-300 !-right-[6px]"
              />
            </div>
          ))}
        </div>
      )}

      {/* Status Badge */}
      {data.status && data.status !== 'idle' && (
        <div
          className={`absolute -top-3 -right-3 px-2 py-0.5 rounded-full text-xs font-medium text-white shadow-lg ${
            data.status === 'running' ? 'bg-blue-500 animate-pulse' :
            data.status === 'success' ? 'bg-green-500' :
            'bg-red-500'
          }`}
        >
          {data.status === 'running' && '● Running'}
          {data.status === 'success' && '✓ Done'}
          {data.status === 'error' && '✕ Error'}
        </div>
      )}
    </div>
  );
}
