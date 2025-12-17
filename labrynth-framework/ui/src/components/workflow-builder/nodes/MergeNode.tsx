import { Handle, Position, NodeProps } from '@xyflow/react';
import { useTheme } from '../../../App';

export function MergeNode({ data, selected }: NodeProps) {
  const { theme } = useTheme();
  const inputCount = data.inputCount || 3;
  const strategy = data.strategy || 'Wait All';

  return (
    <div
      className={`w-[200px] rounded-xl border-2 transition-all ${
        theme === 'dark' ? 'bg-[#1E293B]' : 'bg-white'
      } ${selected ? 'shadow-xl shadow-blue-500/20' : ''}`}
      style={{
        borderColor: selected ? '#3B82F6' : theme === 'dark' ? 'rgba(148,163,184,0.2)' : '#E2E8F0',
      }}
    >
      {/* Header */}
      <div className={`flex items-center gap-2 px-4 py-3 border-b ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <span className="text-xl text-blue-500">⫗</span>
        <span className={`font-medium text-sm ${
          theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
        }`}>
          Merge
        </span>
      </div>

      {/* Inputs */}
      <div className="px-4 py-3">
        {Array.from({ length: inputCount }).map((_, i) => (
          <div key={i} className="flex items-center py-1 relative">
            <Handle
              type="target"
              position={Position.Left}
              id={`input-${i}`}
              className="!w-3 !h-3 !bg-blue-500 !border-2 !border-blue-300 !-left-[6px]"
            />
            <span className="text-xs text-[#94A3B8]">Input {i + 1}</span>
          </div>
        ))}
        <div className={`mt-2 pt-2 border-t ${
          theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
        }`}>
          <span className="text-xs text-[#64748B]">Strategy: {strategy}</span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!w-3 !h-3 !bg-purple-500 !border-2 !border-purple-300"
        style={{ top: '50%' }}
      />
    </div>
  );
}
