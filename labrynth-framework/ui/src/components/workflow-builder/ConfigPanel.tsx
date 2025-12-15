import { X, Lightbulb, Trash2 } from 'lucide-react';
import { useTheme } from '../../App';
import { useWorkflowStore } from '../../stores/workflowStore';

export function ConfigPanel() {
  const { theme } = useTheme();
  const { nodes, selectedNodeId, updateNode, deleteNode, setSelectedNodeId, name, description } = useWorkflowStore();

  const selectedNode = nodes.find(n => n.id === selectedNodeId);

  if (!selectedNode) {
    return (
      <div className={`w-[320px] h-full flex flex-col border-l overflow-y-auto ${
        theme === 'dark'
          ? 'bg-[#0F172A] border-[rgba(148,163,184,0.1)]'
          : 'bg-white border-[#E2E8F0]'
      }`}>
        {/* Workflow Settings */}
        <div className="p-4">
          <h3 className={`font-semibold mb-4 ${
            theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
          }`}>
            Workflow Settings
          </h3>

          <div className="space-y-4">
            <div>
              <label className={`block text-sm font-medium mb-2 ${
                theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
              }`}>
                Name
              </label>
              <input
                type="text"
                value={name}
                readOnly
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                  theme === 'dark'
                    ? 'bg-[#0A0F1C] border-[rgba(148,163,184,0.1)] text-[#F5F5F0]'
                    : 'bg-[#F9FAFB] border-[#E2E8F0] text-[#0F172A]'
                }`}
              />
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${
                theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
              }`}>
                Description
              </label>
              <textarea
                value={description}
                readOnly
                rows={3}
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none resize-none ${
                  theme === 'dark'
                    ? 'bg-[#0A0F1C] border-[rgba(148,163,184,0.1)] text-[#F5F5F0]'
                    : 'bg-[#F9FAFB] border-[#E2E8F0] text-[#0F172A]'
                }`}
              />
            </div>
          </div>

          <div className={`mt-6 pt-6 border-t ${
            theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
          }`}>
            <h4 className="text-xs font-medium text-[#64748B] uppercase mb-3">Statistics</h4>
            <div className="space-y-2">
              <StatRow label="Nodes" value={nodes.length} />
              <StatRow label="Connections" value={0} />
              <StatRow label="Last saved" value="Just now" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`w-[320px] h-full flex flex-col border-l overflow-y-auto ${
      theme === 'dark'
        ? 'bg-[#0F172A] border-[rgba(148,163,184,0.1)]'
        : 'bg-white border-[#E2E8F0]'
    }`}>
      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-3 border-b ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <div>
          <h3 className={`font-medium ${
            theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
          }`}>
            {selectedNode.data.label}
          </h3>
          <span className="text-xs text-[#64748B] capitalize">{selectedNode.type} Node</span>
        </div>
        <button
          onClick={() => setSelectedNodeId(null)}
          className={`p-1 rounded transition-colors ${
            theme === 'dark'
              ? 'hover:bg-[rgba(255,255,255,0.05)]'
              : 'hover:bg-[#F9FAFB]'
          }`}
        >
          <X className="w-4 h-4 text-[#64748B]" />
        </button>
      </div>

      {/* Settings */}
      <div className={`p-4 border-b ${
        theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
      }`}>
        <h4 className="text-xs font-medium text-[#64748B] uppercase mb-3">Settings</h4>

        <div className="space-y-3">
          <div>
            <label className={`block text-sm font-medium mb-2 ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
            }`}>
              Display Name
            </label>
            <input
              type="text"
              value={selectedNode.data.label}
              onChange={(e) => updateNode(selectedNode.id, { label: e.target.value })}
              className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                theme === 'dark'
                  ? 'bg-[#0A0F1C] border-[rgba(148,163,184,0.1)] text-[#F5F5F0]'
                  : 'bg-[#F9FAFB] border-[#E2E8F0] text-[#0F172A]'
              }`}
            />
          </div>
        </div>
      </div>

      {/* Inputs */}
      {selectedNode.data.inputs && Object.keys(selectedNode.data.inputs).length > 0 && (
        <div className={`p-4 border-b ${
          theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
        }`}>
          <h4 className="text-xs font-medium text-[#64748B] uppercase mb-3">Inputs</h4>
          {Object.entries(selectedNode.data.inputs).map(([name, config]: [string, any]) => (
            <div key={name} className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-[#94A3B8]">{name} ({config.type})</span>
                <span className={`text-xs ${config.required ? 'text-red-400' : 'text-[#64748B]'}`}>
                  {config.required ? 'Required' : 'Optional'}
                </span>
              </div>
              <input
                type="text"
                placeholder={`{{node.${name}}} or static value`}
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none font-mono ${
                  theme === 'dark'
                    ? 'bg-[#0A0F1C] border-[rgba(148,163,184,0.1)] text-[#F5F5F0]'
                    : 'bg-[#F9FAFB] border-[#E2E8F0] text-[#0F172A]'
                }`}
              />
            </div>
          ))}
          <p className="text-xs text-[#64748B] flex items-center gap-1">
            <Lightbulb className="w-3 h-3" />
            Use {`{{node.output}}`} to reference other nodes
          </p>
        </div>
      )}

      {/* Outputs */}
      {selectedNode.data.outputs && Object.keys(selectedNode.data.outputs).length > 0 && (
        <div className={`p-4 border-b ${
          theme === 'dark' ? 'border-[rgba(148,163,184,0.1)]' : 'border-[#E2E8F0]'
        }`}>
          <h4 className="text-xs font-medium text-[#64748B] uppercase mb-3">Outputs</h4>
          {Object.entries(selectedNode.data.outputs).map(([name, config]: [string, any]) => (
            <div key={name} className="flex items-center justify-between py-1">
              <span className="text-sm text-[#94A3B8]">{name}</span>
              <span className="text-xs text-[#64748B]">{config.type}</span>
            </div>
          ))}
        </div>
      )}

      {/* Delete Button */}
      <div className="p-4">
        <button
          onClick={() => deleteNode(selectedNode.id)}
          className={`w-full px-4 py-2 text-sm rounded-lg border transition-colors ${
            theme === 'dark'
              ? 'text-red-400 border-red-500/30 hover:bg-red-500/10'
              : 'text-red-500 border-red-300 hover:bg-red-50'
          }`}
        >
          <Trash2 className="w-4 h-4 mr-2 inline" />
          Delete Node
        </button>
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  const { theme } = useTheme();

  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-[#94A3B8]">{label}:</span>
      <span className={`text-sm font-medium ${
        theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
      }`}>
        {value}
      </span>
    </div>
  );
}
