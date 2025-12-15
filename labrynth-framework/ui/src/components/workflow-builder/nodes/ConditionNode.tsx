import { Handle, Position, NodeProps } from '@xyflow/react';
import { useTheme } from '../../../App';

export function ConditionNode({ data, selected }: NodeProps) {
  const { theme } = useTheme();
  const branches = data.branches || ['if', 'else'];

  return (
    <div
      className={`w-[220px] rounded-xl border-2 transition-all ${
        theme === 'dark' ? 'bg-[#1E293B]' : 'bg-white'
      } ${selected ? 'shadow-xl shadow-amber-500/20' : ''}`}
      style={{
        borderColor: selected ? '#F59E0B' : theme === 'dark' ? 'rgba(148,163,184,0.2)' : '#E2E8F0',
      }}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-blue-300"
        style={{ top: '50%' }}
      />

      {/* Header */}
      <div className={`flex items-center gap-2 px-4 py-3 border-b ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <span className="text-xl text-amber-500">◇</span>
        <span className={`font-medium text-sm ${
          theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
        }`}>
          Condition
        </span>
      </div>

      {/* Condition Preview */}
      <div className={`px-4 py-3 border-b ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <code className="text-xs text-purple-400 bg-purple-500/10 px-2 py-1 rounded block">
          {data.condition || 'Click to configure'}
        </code>
      </div>

      {/* Output Branches */}
      <div className="px-4 py-3">
        {branches.map((branch: string, index: number) => (
          <div key={branch} className="flex items-center justify-end gap-2 py-1 relative">
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                branch === 'if' ? 'bg-green-500/20 text-green-400' :
                branch === 'elif' ? 'bg-amber-500/20 text-amber-400' :
                'bg-gray-500/20 text-gray-400'
              }`}
            >
              {branch}
            </span>
            <Handle
              type="source"
              position={Position.Right}
              id={`branch-${branch}`}
              className="!w-3 !h-3 !bg-purple-500 !border-2 !border-purple-300 !-right-[6px]"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
