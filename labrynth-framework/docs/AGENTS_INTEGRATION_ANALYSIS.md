# Agents API Integration Analysis

## Overview

This document analyzes the gap between the frontend UI requirements for displaying agents and the current backend API capabilities.

---

## Frontend Requirements

### AgenticAssetsScreen.tsx

The frontend displays agent cards with the following fields:

```typescript
interface Agent {
  name: string;        // Agent display name
  role: string;        // e.g., "Data Analyzer", "ML Specialist"
  model: string;       // e.g., "GPT-4 Turbo", "Claude 3.5"
  tasks: number;       // Total tasks executed
  successRate: number; // Percentage (0-100)
  status: 'active' | 'idle' | 'error' | 'disabled';
  statusColor: string; // Derived from status
}
```

### AgentPerformance.tsx (Dashboard Widget)

```typescript
interface AgentPerformance {
  name: string;
  percentage: number;     // Success rate
  tasksCompleted: number; // Task count
}
```

### UI Features

| Feature | Description |
|---------|-------------|
| Search | Filter agents by name |
| Filter by Model | Dropdown filter |
| Filter by Status | Dropdown filter |
| Create Agent | Button (currently no-op) |
| Agent Card | Shows all agent details |
| Configure | Button per agent |
| Logs | Button per agent |

---

## Backend API

### GET /api/agents

Returns:
```json
{
  "agents": [...],
  "count": 5
}
```

### Agent Model (Database)

```python
class Agent:
    id: UUID
    project_id: str
    name: str
    description: str
    entrypoint: str       # e.g., "agents.example:send_email"
    tags: list[str]
    parameters: dict      # Function parameters with type info
    created_at: datetime
    updated_at: datetime
```

### Agent.to_dict() Response

```json
{
  "id": "uuid-string",
  "project_id": "abc123",
  "name": "send-email",
  "description": "Send an email notification",
  "entrypoint": "agents.notifications:send_email",
  "tags": ["email", "notification"],
  "parameters": {
    "recipient": {
      "name": "recipient",
      "type": "str",
      "required": true,
      "default": null,
      "description": null
    },
    "subject": {
      "name": "subject",
      "type": "str",
      "required": true,
      "default": null,
      "description": null
    }
  },
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

---

## Gap Analysis

| Frontend Field | Backend Field | Status | Notes |
|----------------|---------------|--------|-------|
| `name` | `name` | ✅ Available | Direct mapping |
| `role` | `description` | ⚠️ Partial | Can use description as role |
| `model` | - | ❌ Missing | Not tracked in backend |
| `tasks` | - | ❌ Missing | Requires run tracking |
| `successRate` | - | ❌ Missing | Requires run tracking |
| `status` | - | ❌ Missing | No runtime status tracking |
| - | `id` | ✅ Available | Not shown in UI but useful |
| - | `project_id` | ✅ Available | Could filter by project |
| - | `entrypoint` | ✅ Available | Show in "Configure" modal |
| - | `tags` | ✅ Available | Could use for filtering |
| - | `parameters` | ✅ Available | Show in "Configure" modal |
| - | `created_at` | ✅ Available | Could show in UI |
| - | `updated_at` | ✅ Available | Could show in UI |

### Missing Backend Capabilities

1. **No `model` field** - The backend doesn't track what LLM model an agent uses
2. **No run tracking** - No tables for pipeline runs or task executions
3. **No status tracking** - Agents are static definitions, no runtime state
4. **No success/failure metrics** - Requires run history

---

## Recommendations

### Phase 1: Basic Integration (Immediate)

Update frontend to use available backend data:

```typescript
// Map backend response to frontend model
interface BackendAgent {
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

// Frontend display model (adapted)
interface AgentDisplay {
  id: string;
  name: string;
  role: string;        // Use description
  tags: string[];      // New field
  parameters: Record<string, ParameterInfo>; // New field
  entrypoint: string;  // New field
  created_at: string;  // New field

  // Static/placeholder for now
  model: string;       // Default: "Not configured"
  tasks: number;       // Default: 0
  successRate: number; // Default: 0
  status: 'idle';      // Default: idle (no runs yet)
}
```

**Changes needed:**
1. Create `src/api/agents.ts` - API client
2. Update `AgenticAssetsScreen.tsx` - Fetch from API
3. Update `AgentCard` - Show available fields, hide/default missing ones

### Phase 2: Add Model Configuration (Optional)

Add optional `model` field to agent decorator and database:

```python
@agent(
    name="data-analyzer",
    description="Analyzes data patterns",
    model="gpt-4-turbo",  # New optional field
    tags=["analysis"]
)
def analyze_data(data: dict) -> dict:
    ...
```

**Backend changes:**
- Add `model` column to Agent table
- Update `@agent` decorator to accept `model` parameter

### Phase 3: Run Tracking (Future - with LangGraph)

When pipeline execution is implemented:

```python
# New tables needed
class PipelineRun:
    id: UUID
    pipeline_id: UUID
    status: str  # pending, running, completed, failed
    started_at: datetime
    completed_at: datetime

class AgentExecution:
    id: UUID
    run_id: UUID
    agent_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime
    error: Optional[str]
```

This enables:
- Task count per agent
- Success rate calculation
- Real-time status (check if agent is currently executing)

---

## Implementation Plan

### Step 1: Create API Client

```typescript
// ui/src/api/agents.ts
const API_BASE = '/api';

export async function fetchAgents(): Promise<AgentResponse> {
  const res = await fetch(`${API_BASE}/agents`);
  return res.json();
}

export async function fetchAgent(name: string): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents/${name}`);
  return res.json();
}
```

### Step 2: Update AgenticAssetsScreen

1. Replace hardcoded `agents` array with `useState` + `useEffect`
2. Call `fetchAgents()` on mount
3. Map backend response to display model
4. Handle loading and error states

### Step 3: Update AgentCard

1. Show `description` as role
2. Show `tags` as badges
3. Show parameter count (e.g., "3 parameters")
4. Default model/tasks/status to placeholder values
5. Make "Configure" button show agent details modal

### Step 4: Add Agent Details Modal

Show full agent information:
- Name, description
- Entrypoint
- Tags
- Parameters with types and defaults
- Created/updated timestamps

---

## API Sufficiency Summary

| Requirement | Can Backend Fulfill? |
|-------------|---------------------|
| List agents | ✅ Yes |
| Get agent by name | ✅ Yes |
| Show agent description | ✅ Yes |
| Show agent parameters | ✅ Yes |
| Show agent tags | ✅ Yes |
| Filter by project | ✅ Yes |
| Show LLM model | ❌ No (not tracked) |
| Show task count | ❌ No (no run tracking) |
| Show success rate | ❌ No (no run tracking) |
| Show live status | ❌ No (no runtime tracking) |

**Conclusion:** The backend API can support a basic agent listing with core metadata. Runtime metrics (tasks, success rate, status) require pipeline execution tracking which will come with LangGraph integration.

---

## Next Steps

1. **Immediate:** Integrate available backend data into frontend
2. **Short-term:** Add optional `model` field to agent configuration
3. **Medium-term:** Build pipeline execution with LangGraph
4. **Long-term:** Add run tracking tables and metrics endpoints
