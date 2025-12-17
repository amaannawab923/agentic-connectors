/**
 * API type definitions for Labrynth
 */

// Parameter info from backend
export interface ParameterInfo {
  name: string;
  type: string;
  required: boolean;
  default: unknown;
  description: string | null;
}

// Agent from backend API
export interface Agent {
  id: string;
  project_id: string;
  name: string;
  description: string;
  entrypoint: string;
  tags: string[];
  parameters: Record<string, ParameterInfo>;
  created_at: string;
  updated_at: string;
}

// API response for list agents
export interface AgentsResponse {
  agents: Agent[];
  count: number;
}

// Frontend display model (with defaults for missing runtime data)
export interface AgentDisplay {
  id: string;
  name: string;
  description: string;
  entrypoint: string;
  tags: string[];
  parameters: Record<string, ParameterInfo>;
  created_at: string;
  updated_at: string;
  // Runtime fields (placeholders until execution tracking exists)
  tasks: number;
  successRate: number;
  status: 'active' | 'idle' | 'error' | 'disabled';
  statusColor: string;
}

// Convert backend agent to display model
export function toAgentDisplay(agent: Agent): AgentDisplay {
  return {
    ...agent,
    // Default runtime values (will be real once we have run tracking)
    tasks: 0,
    successRate: 0,
    status: 'idle',
    statusColor: '#F59E0B', // Yellow for idle
  };
}
