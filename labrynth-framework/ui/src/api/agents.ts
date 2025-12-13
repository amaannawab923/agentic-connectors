/**
 * Agents API client
 */

import { Agent, AgentsResponse } from './types';

const API_BASE = '/api';

/**
 * Fetch all agents from the backend
 */
export async function fetchAgents(projectId?: string): Promise<AgentsResponse> {
  const url = new URL(`${API_BASE}/agents`, window.location.origin);
  if (projectId) {
    url.searchParams.set('project_id', projectId);
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch a single agent by name
 */
export async function fetchAgent(name: string, projectId?: string): Promise<Agent> {
  const url = new URL(`${API_BASE}/agents/${encodeURIComponent(name)}`, window.location.origin);
  if (projectId) {
    url.searchParams.set('project_id', projectId);
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Agent '${name}' not found`);
    }
    throw new Error(`Failed to fetch agent: ${response.statusText}`);
  }

  return response.json();
}
