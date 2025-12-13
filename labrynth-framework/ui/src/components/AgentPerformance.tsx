import { useState, useEffect } from 'react';
import { Loader2, Bot } from 'lucide-react';
import { useThemeColors } from '../hooks/useThemeColors';
import { fetchAgents, Agent } from '../api';

export function AgentPerformance() {
  const { classes } = useThemeColors();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAgents() {
      try {
        setLoading(true);
        const response = await fetchAgents();
        // Take only first 3 agents for the dashboard widget
        setAgents(response.agents.slice(0, 3));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    loadAgents();
  }, []);

  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl overflow-hidden`}>
      {/* Header */}
      <div className={`p-5 border-b ${classes.borderCard}`}>
        <h3 className={`text-base font-semibold ${classes.textPrimary}`}>Deployed Agents</h3>
      </div>

      {/* Content */}
      <div className="p-5">
        {loading && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 text-[#8B5CF6] animate-spin" />
          </div>
        )}

        {error && (
          <div className="text-sm text-red-400 text-center py-4">
            {error}
          </div>
        )}

        {!loading && !error && agents.length === 0 && (
          <div className="text-center py-4">
            <Bot className="w-8 h-8 text-[#64748B] mx-auto mb-2" />
            <p className={`text-sm ${classes.textMuted}`}>No agents deployed</p>
          </div>
        )}

        {!loading && !error && agents.length > 0 && (
          <div className="space-y-5">
            {agents.map((agent) => (
              <AgentRow key={agent.id} agent={agent} classes={classes} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AgentRow({ agent, classes }: { agent: Agent; classes: ReturnType<typeof useThemeColors>['classes'] }) {
  // Since we don't have run tracking yet, show agent info instead of performance metrics
  const paramCount = Object.keys(agent.parameters).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-sm font-medium ${classes.textPrimary}`}>{agent.name}</span>
        <span className={`text-xs ${classes.textMuted}`}>{paramCount} params</span>
      </div>

      {/* Description instead of progress bar */}
      <p className={`text-xs ${classes.textMuted} line-clamp-1 mb-1`}>
        {agent.description || 'No description'}
      </p>

      {/* Tags */}
      {agent.tags.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {agent.tags.slice(0, 2).map((tag) => (
            <span
              key={tag}
              className="text-xs px-1.5 py-0.5 bg-[#8B5CF6]/20 text-[#A78BFA] rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
