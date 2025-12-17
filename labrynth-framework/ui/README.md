# Labrynth UI

A modern visual workflow builder for AI agent orchestration. Build, visualize, and monitor multi-agent pipelines with an intuitive drag-and-drop interface.

## Features

### Visual Workflow Builder
- **Drag-and-drop canvas** - Build pipelines by dragging agents and blocks onto the canvas
- **Visual connections** - Connect nodes to define data flow between agents
- **Auto-layout** - Automatically arrange nodes for optimal readability
- **Real-time execution** - Watch agents execute with live highlighting

### Agent Toolbox
- **7 Specialized Agents** - Research, Generator, Mock Generator, Tester, Test Review, Reviewer, Publisher
- **Dynamic loading** - Agents are fetched from the backend API
- **Searchable** - Filter agents by name, description, or tags

### Triggers & Blocks
- **Triggers** - Start, Schedule, Webhook, GitHub, Gmail, Airtable, Calendly, HubSpot
- **Blocks** - Condition, Loop, Parallel, Memory, Variables, Human in the Loop, Guardrails

### Run Management
- **Run history** - View past workflow executions
- **Status tracking** - Success, error, running, pending states
- **Run details modal** - Deep dive into individual run metrics

### Theming
- **Light/Dark mode** - Toggle between themes
- **Consistent styling** - Tailwind CSS with design tokens

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **React 18** | UI framework |
| **TypeScript** | Type safety |
| **ReactFlow** | Canvas and node rendering |
| **Tailwind CSS** | Styling |
| **Lucide React** | Icons |
| **Vite** | Build tool and dev server |

## Project Structure

```
ui/
├── src/
│   ├── components/
│   │   ├── workflow-builder-v2/    # Main workflow builder
│   │   │   ├── WorkflowBuilderV2.tsx
│   │   │   ├── ConditionEditor.tsx
│   │   │   ├── CustomEdge.tsx
│   │   │   ├── NodeActionButtons.tsx
│   │   │   ├── RunModal.tsx
│   │   │   └── index.ts
│   │   ├── screens/                # Page components
│   │   └── ui/                     # Shared UI components
│   ├── api/                        # API client
│   ├── hooks/                      # Custom React hooks
│   ├── styles/                     # Global styles
│   ├── App.tsx                     # Main app with routing
│   └── main.tsx                    # Entry point
├── public/                         # Static assets
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd ui
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The UI will be available at `http://localhost:3000`

**Important:** The backend must be running on port 8000 for API calls to work. The Vite dev server proxies `/api/*` requests to the backend.

### Production Build

```bash
npm run build
```

Build output will be in the `dist/` directory.

## API Integration

The UI connects to the Labrynth backend API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List all registered agents |
| `/api/agents/{name}` | GET | Get agent by name |
| `/api/health` | GET | Health check |

### Agent Response Schema

```typescript
interface Agent {
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

interface AgentsResponse {
  agents: Agent[];
  count: number;
}
```

## Workflow Builder Components

### WorkflowBuilderV2

The main component containing:
- **Left Sidebar** - Workflow details, run history, navigation
- **Canvas** - ReactFlow-based drag-and-drop area
- **Right Sidebar** - Copilot chat, Toolbar (agents/blocks), Node Editor

### CustomNode

Renders workflow nodes with:
- Header with icon and label
- Configuration fields
- Input/output handles
- Running state animation

### ConditionEditor

Visual editor for condition nodes with:
- If/Else branch configuration
- Expression builder
- Variable references

### RunModal

Displays run details:
- Execution timeline
- Step-by-step status
- Duration metrics
- Comments/notes

## Configuration

### Vite Proxy

The proxy configuration in `vite.config.ts` uses `127.0.0.1` instead of `localhost` to avoid IPv6 issues on macOS:

```typescript
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
},
```

### Theme Context

Theme is managed via React Context in `App.tsx`:

```typescript
const [theme, setTheme] = useState<Theme>('light');

<ThemeContext.Provider value={{ theme, setTheme }}>
  {/* App content */}
</ThemeContext.Provider>
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Delete` / `Backspace` | Delete selected node |
| `Cmd/Ctrl + Z` | Undo |
| `Cmd/Ctrl + Shift + Z` | Redo |
| `Cmd/Ctrl + A` | Select all nodes |

## Contributing

1. Follow the existing code style
2. Use TypeScript for all new files
3. Add proper type definitions
4. Test with both light and dark themes
5. Ensure responsive design

## License

MIT
