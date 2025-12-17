import { useState, useEffect } from 'react';
import { Search, ChevronDown, Plus, Bot, Tag, Code, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchAgents, toAgentDisplay, AgentDisplay } from '../../api';
import { useThemeColors } from '../../hooks/useThemeColors';

export function AgenticAssetsScreen() {
  const { classes, bgCard, borderDefault, textPrimary, textSecondary, bgInput } = useThemeColors();
  const [agents, setAgents] = useState<AgentDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadAgents();
  }, []);

  async function loadAgents() {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchAgents();
      setAgents(response.agents.map(toAgentDisplay));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  }

  // Filter agents by search query
  const filteredAgents = agents.filter(agent => {
    const query = searchQuery.toLowerCase();
    return (
      agent.name.toLowerCase().includes(query) ||
      agent.description.toLowerCase().includes(query) ||
      agent.tags.some(tag => tag.toLowerCase().includes(query))
    );
  });

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className={`text-2xl font-semibold ${classes.textPrimary} mb-1`}>Agentic Assets</h1>
        <p className={`text-sm ${classes.textSecondary}`}>Manage your AI agents and their configurations</p>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${classes.textMuted}`} />
            <input
              type="text"
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`w-full ${classes.bgInput} border ${classes.borderInput} rounded-lg pl-10 pr-4 py-2 text-sm ${classes.textPrimary} placeholder:${classes.textMuted} focus:border-[#8B5CF6] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]`}
            />
          </div>

          <button className={`flex items-center gap-2 px-3 py-2 ${classes.bgCard} border ${classes.borderCard} rounded-lg text-sm ${classes.textSecondary} ${classes.bgHover} transition-colors`}>
            Tags
            <ChevronDown className="w-4 h-4" />
          </button>

          <button className={`flex items-center gap-2 px-3 py-2 ${classes.bgCard} border ${classes.borderCard} rounded-lg text-sm ${classes.textSecondary} ${classes.bgHover} transition-colors`}>
            Status
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={loadAgents}
          className="flex items-center gap-2 bg-[#8B5CF6] hover:bg-[#7C3AED] text-white px-4 py-2 rounded-lg transition-colors text-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-[#8B5CF6] animate-spin" />
          <span className={`ml-3 ${classes.textSecondary}`}>Loading agents...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-500">{error}</span>
          <button
            onClick={loadAgents}
            className="ml-auto text-sm text-red-500 hover:text-red-400 underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && agents.length === 0 && (
        <div className="text-center py-12">
          <Bot className={`w-16 h-16 ${classes.textMuted} mx-auto mb-4`} />
          <h3 className={`text-lg font-medium ${classes.textPrimary} mb-2`}>No agents deployed</h3>
          <p className={`text-sm ${classes.textSecondary} mb-4`}>
            Deploy agents using <code className={`${classes.bgInput} px-2 py-1 rounded`}>labrynth deploy</code>
          </p>
        </div>
      )}

      {/* No Results State */}
      {!loading && !error && agents.length > 0 && filteredAgents.length === 0 && (
        <div className="text-center py-12">
          <Search className={`w-12 h-12 ${classes.textMuted} mx-auto mb-4`} />
          <h3 className={`text-lg font-medium ${classes.textPrimary} mb-2`}>No matching agents</h3>
          <p className={`text-sm ${classes.textSecondary}`}>
            Try a different search term
          </p>
        </div>
      )}

      {/* Agents Grid */}
      {!loading && !error && filteredAgents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentDisplay }) {
  const { classes } = useThemeColors();
  const [showDetails, setShowDetails] = useState(false);

  const statusConfig = {
    active: { label: 'Active', icon: '🟢', color: '#10B981' },
    idle: { label: 'Idle', icon: '🟡', color: '#F59E0B' },
    error: { label: 'Error', icon: '🔴', color: '#EF4444' },
    disabled: { label: 'Disabled', icon: '⚫', color: '#64748B' },
  };

  const status = statusConfig[agent.status];
  const paramCount = Object.keys(agent.parameters).length;

  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl p-6 hover:translate-y-[-4px] hover:shadow-lg transition-all duration-200`}>
      {/* Icon */}
      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#8B5CF6] to-[#3B82F6] flex items-center justify-center mb-4">
        <Bot className="w-6 h-6 text-white" />
      </div>

      {/* Name and Description */}
      <h3 className={`text-lg font-semibold ${classes.textPrimary} mb-1`}>{agent.name}</h3>
      <p className={`text-sm ${classes.textSecondary} mb-3 line-clamp-2`}>{agent.description || 'No description'}</p>

      {/* Tags */}
      {agent.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {agent.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#8B5CF6]/20 text-[#8B5CF6] rounded text-xs"
            >
              <Tag className="w-3 h-3" />
              {tag}
            </span>
          ))}
          {agent.tags.length > 3 && (
            <span className={`text-xs ${classes.textMuted}`}>+{agent.tags.length - 3} more</span>
          )}
        </div>
      )}

      {/* Specs */}
      <div className="space-y-2 mb-4 text-sm">
        <div className="flex justify-between">
          <span className={classes.textMuted}>Parameters:</span>
          <span className={classes.textPrimary}>{paramCount}</span>
        </div>
        <div className="flex justify-between">
          <span className={classes.textMuted}>Runs:</span>
          <span className={`${classes.textMuted} italic`}>{agent.tasks || 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className={classes.textMuted}>Success:</span>
          <span className={`${classes.textMuted} italic`}>{agent.tasks > 0 ? `${agent.successRate}%` : 'N/A'}</span>
        </div>
      </div>

      {/* Status */}
      <div className={`flex items-center gap-2 mb-4 pb-4 border-b ${classes.borderCard}`}>
        <span>{status.icon}</span>
        <span className="text-sm" style={{ color: status.color }}>{status.label}</span>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className={`flex-1 px-3 py-2 text-xs ${classes.bgCard} border ${classes.borderCard} ${classes.textSecondary} hover:${classes.textPrimary} rounded-lg transition-colors ${classes.bgHover}`}
        >
          {showDetails ? 'Hide Details' : 'View Details'}
        </button>
        <button className={`flex-1 px-3 py-2 text-xs ${classes.bgCard} border ${classes.borderCard} ${classes.textSecondary} hover:${classes.textPrimary} rounded-lg transition-colors ${classes.bgHover}`}>
          Logs
        </button>
      </div>

      {/* Details Panel */}
      {showDetails && (
        <div className={`mt-4 pt-4 border-t ${classes.borderCard} space-y-3`}>
          {/* Entrypoint */}
          <div>
            <div className={`flex items-center gap-1 text-xs ${classes.textMuted} mb-1`}>
              <Code className="w-3 h-3" />
              Entrypoint
            </div>
            <code className={`text-xs text-[#8B5CF6] ${classes.bgInput} px-2 py-1 rounded block overflow-x-auto`}>
              {agent.entrypoint}
            </code>
          </div>

          {/* Parameters */}
          {paramCount > 0 && (
            <div>
              <div className={`text-xs ${classes.textMuted} mb-2`}>Parameters</div>
              <div className="space-y-1">
                {Object.values(agent.parameters).map((param) => (
                  <div key={param.name} className="flex items-center justify-between text-xs">
                    <span className={classes.textPrimary}>
                      {param.name}
                      {param.required && <span className="text-red-500 ml-0.5">*</span>}
                    </span>
                    <span className={classes.textMuted}>{param.type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className={`text-xs ${classes.textMuted}`}>
            Created: {new Date(agent.created_at).toLocaleDateString()}
          </div>
        </div>
      )}
    </div>
  );
}
