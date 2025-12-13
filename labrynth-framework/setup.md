# Labrynth Development Setup

This guide covers setting up Labrynth for local development.

## Prerequisites

- Python 3.10+
- Node.js 18+ (for UI development)
- uv (recommended) or pip

## Quick Start

### 1. Clone and Create Virtual Environment

```bash
cd labrynth-framework

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# With uv (recommended - faster)
uv pip install -e .

# Or with pip
pip install -e .
```

Verify installation:

```bash
labrynth --help
```

### 3. Start Development Server

```bash
# Navigate to your test project
cd /path/to/your/test-project

# Start the server
labrynth server start
```

## Development Mode (Auto-Deploy)

For rapid development, Labrynth supports automatic agent deployment via the `LABRYNTH_DEV_PROJECT` environment variable. When set, the server will:

1. Check if the path exists and contains a `labrynth.yaml`
2. Discover all agents in the project
3. Auto-deploy them to the database on server startup

### Usage

```bash
# Set the dev project path
export LABRYNTH_DEV_PROJECT=/path/to/your/test-project

# Start the server (from anywhere)
labrynth server start
```

Or in one line:

```bash
LABRYNTH_DEV_PROJECT=/path/to/your/test-project labrynth server start
```

### Example with Test Project

```bash
# Using the test project
export LABRYNTH_DEV_PROJECT=/Users/amaannawab/research/test

# Start server - agents will be auto-deployed
labrynth server start

# Output will show:
# [Dev Mode] Auto-deploying from: /Users/amaannawab/research/test
# [Dev Mode] Project ID: abc12345
# [Dev Mode] Found 2 agent(s)
# [Dev Mode]   - my-agent
# [Dev Mode]   - another-agent
# [Dev Mode] Deployed 2 agent(s)
```

## UI Development

The UI is a Vite + React application located in the `ui/` directory.

### Running UI in Development Mode

1. **Start the API server** (in one terminal):

```bash
cd labrynth-framework
LABRYNTH_DEV_PROJECT=/path/to/test-project labrynth server start
# Server runs on http://localhost:8000
```

2. **Start the UI dev server** (in another terminal):

```bash
cd labrynth-framework/ui
npm install
npm run dev
# UI runs on http://localhost:3000
```

The UI dev server proxies `/api` requests to `http://localhost:8000`, so you get hot reload for UI changes while the API remains stable.

### Building the UI for Production

```bash
cd labrynth-framework

# Build and copy to server directory
./scripts/build-ui.sh

# Or manually:
cd ui
npm install
npm run build
cp -r dist ../src/labrynth/server/ui
```

## Project Structure

```
labrynth-framework/
├── src/labrynth/
│   ├── cli/              # CLI commands
│   ├── config/           # Configuration loading
│   ├── core/             # Core decorators and registry
│   ├── database/         # SQLite database layer
│   ├── discovery/        # Agent discovery
│   └── server/           # FastAPI server
│       ├── api/          # API routes
│       ├── static.py     # SPA static file handler
│       ├── app.py        # FastAPI app factory
│       └── ui/           # Built UI assets (production)
├── ui/                   # UI source (Vite + React)
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   └── build-ui.sh       # UI build script
└── pyproject.toml
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LABRYNTH_DEV_PROJECT` | Path to a project for auto-deployment in dev mode |

## Workflow Summary

> **Note:** Always ensure your virtual environment is activated before running commands:
> ```bash
> source venv/bin/activate
> ```

### For Backend Development

1. Activate venv: `source venv/bin/activate`
2. Make changes to Python code in `src/labrynth/`
3. Changes are picked up automatically (editable install)
4. Restart the server to see changes

### For UI Development

1. Run `npm run dev` in `ui/` for hot reload
2. Make changes to React components
3. Changes appear instantly in browser

### For Full Stack Development

1. Terminal 1: `source venv/bin/activate && LABRYNTH_DEV_PROJECT=/path/to/project labrynth server start`
2. Terminal 2: `cd ui && npm run dev`
3. Open http://localhost:3000 for UI with hot reload
4. API changes require server restart
