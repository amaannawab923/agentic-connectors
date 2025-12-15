import { Handle, Position, NodeProps } from '@xyflow/react';
import { useTheme } from '../../../App';

export function OutputNode({ data, selected }: NodeProps) {
  const { theme } = useTheme();
  const variables = data.variables || [{ name: 'result', type: 'any' }];

  return (
    <div
      className={`w-[200px] rounded-xl border-2 transition-all ${
        theme === 'dark' ? 'bg-[#1E293B]' : 'bg-white'
      } ${selected ? 'shadow-xl shadow-red-500/20' : ''}`}
      style={{
        borderColor: selected ? '#EF4444' : 'rgba(239, 68, 68, 0.5)',
      }}
    >
      {/* Header */}
      <div className={`flex items-center gap-2 px-4 py-3 border-b bg-red-500/10 ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <span className="text-red-500">⏹</span>
        <span className={`font-medium text-sm ${
          theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
        }`}>
          Workflow Output
        </span>
      </div>

      {/* Input Variables */}
      <div className="px-4 py-3">
        {variables.map((variable: any) => (
          <div key={variable.name} className="flex items-center gap-2 py-1 relative">
            <Handle
              type="target"
              position={Position.Left}
              id={`var-${variable.name}`}
              className="!w-3 !h-3 !bg-red-500 !border-2 !border-red-300 !-left-[6px]"
            />
            <span className="text-xs text-[#94A3B8]">
              {variable.name} ({variable.type})
            </span>
          </div>
        ))}
      </div>

      {/* Add Variable Button */}
      <button className={`w-full px-4 py-2 text-xs border-t transition-colors ${
        theme === 'dark'
          ? 'text-[#64748B] hover:text-[#F5F5F0] hover:bg-[rgba(255,255,255,0.05)] border-[rgba(148,163,184,0.1)]'
          : 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F9FAFB] border-[#E2E8F0]'
      }`}>
        + Add Variable
      </button>
    </div>
  );
}
