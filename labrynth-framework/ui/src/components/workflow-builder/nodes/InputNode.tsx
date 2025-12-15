import { Handle, Position, NodeProps } from '@xyflow/react';
import { useTheme } from '../../../App';

export function InputNode({ data, selected }: NodeProps) {
  const { theme } = useTheme();
  const variables = data.variables || [{ name: 'data', type: 'any' }];

  return (
    <div
      className={`w-[200px] rounded-xl border-2 transition-all ${
        theme === 'dark' ? 'bg-[#1E293B]' : 'bg-white'
      } ${selected ? 'shadow-xl shadow-green-500/20' : ''}`}
      style={{
        borderColor: selected ? '#10B981' : 'rgba(16, 185, 129, 0.5)',
      }}
    >
      {/* Header */}
      <div className={`flex items-center gap-2 px-4 py-3 border-b bg-green-500/10 ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <span className="text-green-500">▶</span>
        <span className={`font-medium text-sm ${
          theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
        }`}>
          Workflow Input
        </span>
      </div>

      {/* Output Variables */}
      <div className="px-4 py-3">
        {variables.map((variable: any) => (
          <div key={variable.name} className="flex items-center justify-end gap-2 py-1 relative">
            <span className="text-xs text-[#94A3B8]">
              {variable.name} ({variable.type})
            </span>
            <Handle
              type="source"
              position={Position.Right}
              id={`var-${variable.name}`}
              className="!w-3 !h-3 !bg-green-500 !border-2 !border-green-300 !-right-[6px]"
            />
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
