import { Search } from 'lucide-react';
import { useState } from 'react';
import { useTheme } from '../../App';
import { mockAgents, logicNodes, utilityNodes, ioNodes } from '../../data/mockWorkflows';

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, type: string, data: any) => void;
}

export function NodePalette({ onDragStart }: NodePaletteProps) {
  const { theme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredAgents = mockAgents.filter(agent =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className={`w-[280px] h-full flex flex-col border-r ${
      theme === 'dark'
        ? 'bg-[#0F172A] border-[rgba(148,163,184,0.1)]'
        : 'bg-white border-[#E2E8F0]'
    }`}>
      {/* Search */}
      <div className="p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`w-full pl-10 pr-4 py-2 text-sm rounded-lg border outline-none transition-colors ${
              theme === 'dark'
                ? 'bg-[#0A0F1C] border-[rgba(148,163,184,0.1)] text-[#F5F5F0] placeholder:text-[#64748B] focus:border-purple-500'
                : 'bg-[#F9FAFB] border-[#E2E8F0] text-[#0F172A] placeholder:text-[#94A3B8] focus:border-purple-500'
            }`}
          />
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {/* Agents Section */}
        <Section title="AGENTS" count={filteredAgents.length}>
          <div className="space-y-2">
            {filteredAgents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} onDragStart={onDragStart} />
            ))}
          </div>
        </Section>

        {/* Logic Section */}
        <Section title="LOGIC" count={logicNodes.length}>
          <div className="grid grid-cols-3 gap-2">
            {logicNodes.map((node) => (
              <NodeCard key={node.id} node={node} type={node.id} onDragStart={onDragStart} />
            ))}
          </div>
        </Section>

        {/* I/O Section */}
        <Section title="I/O" count={ioNodes.length}>
          <div className="grid grid-cols-2 gap-2">
            {ioNodes.map((node) => (
              <NodeCard key={node.id} node={node} type={node.id} onDragStart={onDragStart} />
            ))}
          </div>
        </Section>

        {/* Utility Section */}
        <Section title="UTILITY" count={utilityNodes.length}>
          <div className="grid grid-cols-3 gap-2">
            {utilityNodes.map((node) => (
              <NodeCard key={node.id} node={node} type={node.id} onDragStart={onDragStart} />
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, count, children }: { title: string; count: number; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-[#64748B] uppercase tracking-wider">
          {title}
        </span>
        <span className="text-xs text-[#64748B]">({count})</span>
      </div>
      {children}
    </div>
  );
}

function AgentCard({ agent, onDragStart }: { agent: any; onDragStart: any }) {
  const { theme } = useTheme();

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, 'agent', agent)}
      className={`p-3 rounded-lg border cursor-grab active:cursor-grabbing transition-all hover:shadow-md ${
        theme === 'dark'
          ? 'bg-[#1E293B] border-[rgba(148,163,184,0.1)] hover:border-purple-500'
          : 'bg-white border-[#E2E8F0] hover:border-purple-500'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white text-lg flex-shrink-0 shadow-lg">
          {agent.icon}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className={`text-sm font-medium truncate ${
            theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
          }`}>
            {agent.name}
          </h4>
          <p className="text-xs text-[#94A3B8] line-clamp-2 mt-0.5">
            {agent.description}
          </p>
        </div>
      </div>
    </div>
  );
}

function NodeCard({ node, type, onDragStart }: { node: any; type: string; onDragStart: any }) {
  const { theme } = useTheme();

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, type, node)}
      className={`aspect-square flex flex-col items-center justify-center gap-1.5 rounded-lg border cursor-grab active:cursor-grabbing transition-all hover:shadow-md ${
        theme === 'dark'
          ? 'bg-[#1E293B] border-[rgba(148,163,184,0.1)] hover:border-purple-500'
          : 'bg-white border-[#E2E8F0] hover:border-purple-500'
      }`}
    >
      <span className="text-2xl">{node.icon}</span>
      <span className={`text-xs font-medium ${
        theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
      }`}>
        {node.name}
      </span>
    </div>
  );
}
