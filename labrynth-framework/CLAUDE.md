# Labrynth Framework - Claude Code Context

## Development Workflow

### Running in Development Mode

**Two terminals required:**

1. **Terminal 1 - Backend (port 8000):**
```bash
cd /Users/amaannawab/research/temp\ prefect/labrynth-framework
source venv/bin/activate
LABRYNTH_DEV_PROJECT=/Users/amaannawab/research/test labrynth server start
```

2. **Terminal 2 - Frontend (port 3000):**
```bash
cd /Users/amaannawab/research/temp\ prefect/labrynth-framework/ui
npm run dev
```

**Important:** The UI dev server on port 3000 proxies `/api/*` requests to the backend. The backend MUST be running for API calls to work.

### Vite Proxy Configuration (IPv4 Required)

The Vite proxy in `ui/vite.config.ts` MUST use `127.0.0.1` instead of `localhost`:

```typescript
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',  // NOT localhost!
    changeOrigin: true,
  },
},
```

**Why:** On macOS, `localhost` can resolve to IPv6 (`::1`), but the FastAPI backend listens on IPv4. Using `127.0.0.1` forces IPv4 and avoids `ECONNREFUSED ::1:8000` errors.

### Do NOT build and copy UI during development

When developing, use `npm run dev` in the `ui/` directory. Do NOT run:
- `npm run build`
- Copy dist to server directory

The dev server provides hot reload - changes appear instantly without rebuilding.

### Only build for production/release

Build and copy to server only when:
- Preparing a release
- Testing the bundled package
- User explicitly requests it

## Project Structure

```
labrynth-framework/
├── src/labrynth/          # Python package
│   ├── cli/               # CLI commands
│   ├── core/              # @agent decorator, registry
│   ├── database/          # SQLite models, repository
│   └── server/            # FastAPI server
│       ├── api/           # REST endpoints
│       └── ui/            # Built UI (production only)
├── ui/                    # React frontend source
│   ├── src/
│   │   ├── api/           # API client and types
│   │   └── components/    # React components
│   └── vite.config.ts     # Vite config with proxy
└── docs/                  # Documentation
```

## Key API Endpoints

- `GET /api/agents` - List all deployed agents
- `GET /api/agents/{name}` - Get agent by name
- `GET /api/health` - Health check

## Test Project

Location: `/Users/amaannawab/research/test`

Use with dev mode:
```bash
LABRYNTH_DEV_PROJECT=/Users/amaannawab/research/test labrynth server start
```

This auto-deploys agents from the test project on server startup.
