import { Handle, Position, NodeProps } from '@xyflow/react';
import { useTheme } from '../../../App';

export function ParallelNode({ data, selected }: NodeProps) {
  const { theme } = useTheme();
  const branchCount = data.branches || 3;

  return (
    <div
      className={`w-[200px] rounded-xl border-2 transition-all ${
        theme === 'dark' ? 'bg-[#1E293B]' : 'bg-white'
      } ${selected ? 'shadow-xl shadow-blue-500/20' : ''}`}
      style={{
        borderColor: selected ? '#3B82F6' : theme === 'dark' ? 'rgba(148,163,184,0.2)' : '#E2E8F0',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-blue-300"
        style={{ top: '30%' }}
      />

      {/* Header */}
      <div className={`flex items-center gap-2 px-4 py-3 border-b ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <span className="text-xl text-blue-500">⫘</span>
        <span className={`font-medium text-sm ${
          theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
        }`}>
          Parallel Split
        </span>
      </div>

      {/* Branch Info */}
      <div className="px-4 py-3">
        <p className="text-xs text-[#64748B] mb-2">Split into {branchCount} branches</p>
        {Array.from({ length: branchCount }).map((_, i) => (
          <div key={i} className="flex items-center justify-end py-1 relative">
            <span className="text-xs text-[#94A3B8]">Branch {i + 1}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={`branch-${i}`}
              className="!w-3 !h-3 !bg-purple-500 !border-2 !border-purple-300 !-right-[6px]"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
