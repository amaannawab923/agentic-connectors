.PHONY: server stop clean test logs help pipeline-diagram orchestrator orchestrator-dev orchestrator-prod

# Default ports
PORT ?= 8001
ORCHESTRATOR_PORT ?= 8002

help:
	@echo "Connector Generator - Available Commands:"
	@echo ""
	@echo "  Main API Server (port $(PORT)):"
	@echo "    make server           - Start FastAPI server (kills existing process)"
	@echo "    make stop             - Stop the server"
	@echo "    make logs             - Tail the server logs"
	@echo ""
	@echo "  Orchestrator (port $(ORCHESTRATOR_PORT)):"
	@echo "    make orchestrator     - Start orchestrator (test mode, sqlite)"
	@echo "    make orchestrator-dev - Start orchestrator with auto-reload"
	@echo "    make orchestrator-prod- Start orchestrator (production mode)"
	@echo "    make orchestrator-stop- Stop the orchestrator"
	@echo "    make orchestrator-health - Check orchestrator health"
	@echo ""
	@echo "  Testing:"
	@echo "    make test-research    - Test the research agent API"
	@echo "    make clean            - Clean up Python cache files"
	@echo "    make pipeline-diagram - Generate PNG diagram of the LangGraph pipeline"
	@echo ""

# Start the FastAPI server (foreground with logs visible)
server:
	@echo "Stopping any existing process on port $(PORT)..."
	@-lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Starting FastAPI server on port $(PORT)..."
	python3 -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload \
		--reload-dir app

# Start server in background
server-bg:
	@echo "Stopping any existing process on port $(PORT)..."
	@-lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Starting FastAPI server in background on port $(PORT)..."
	python3 -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload \
		--reload-dir app > server.log 2>&1 &
	@echo "Server started. Logs at: server.log"
	@echo "Use 'make logs' to tail the logs"

# Stop the server
stop:
	@echo "Stopping server on port $(PORT)..."
	@-lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	@echo "Server stopped."

# Tail the server logs
logs:
	tail -f server.log

# Test the research agent
test-research:
	@echo "Testing Research Agent API..."
	curl -X POST http://localhost:$(PORT)/api/v1/agents/research \
		-H "Content-Type: application/json" \
		-d '{"connector_name": "Google Sheets"}' | python3 -m json.tool

# Test with async endpoint
test-research-async:
	@echo "Testing Research Agent API (async)..."
	curl -X POST http://localhost:$(PORT)/api/v1/agents/research/async \
		-H "Content-Type: application/json" \
		-d '{"connector_name": "Google Sheets"}' | python3 -m json.tool

# Test the generator agent (requires research doc path)
test-generator:
	@echo "Testing Generator Agent API..."
	@echo "Usage: make test-generator RESEARCH_DOC=/path/to/research.md"
	@if [ -z "$(RESEARCH_DOC)" ]; then \
		echo "Error: RESEARCH_DOC is required"; \
		echo "Example: make test-generator RESEARCH_DOC=./research-docs/google-sheets-research-20251125-123456.md"; \
		exit 1; \
	fi
	curl -X POST http://localhost:$(PORT)/api/v1/agents/generator \
		-H "Content-Type: application/json" \
		-d '{"connector_name": "Google Sheets", "connector_type": "source", "research_doc_path": "$(RESEARCH_DOC)"}' | python3 -m json.tool

# Health check
health:
	curl -s http://localhost:$(PORT)/api/v1/health | python3 -m json.tool

# Clean Python cache
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Generate LangGraph pipeline diagram (PNG and Mermaid)
pipeline-diagram:
	@echo "Generating LangGraph pipeline diagram..."
	python3 scripts/generate_pipeline_diagram.py --output-dir ./docs/diagrams
	@echo ""
	@echo "Output files:"
	@ls -la ./docs/diagrams/ 2>/dev/null || echo "No output files generated"

# ─────────────────────────────────────────────────────────────
# Orchestrator Commands
# ─────────────────────────────────────────────────────────────

# Start orchestrator in test mode with SQLite checkpointing
orchestrator:
	@echo "Stopping any existing process on port $(ORCHESTRATOR_PORT)..."
	@-lsof -ti:$(ORCHESTRATOR_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Starting Orchestrator (TEST MODE, SQLite)..."
	@echo "Health check: http://localhost:$(ORCHESTRATOR_PORT)/orchestrator/health"
	@echo "API docs: http://localhost:$(ORCHESTRATOR_PORT)/docs"
	@echo ""
	. venv/bin/activate && \
	ORCHESTRATOR_TEST_MODE=true \
	ORCHESTRATOR_CHECKPOINTER_TYPE=sqlite \
	python3 -m uvicorn app.orchestrator.app:app --host 0.0.0.0 --port $(ORCHESTRATOR_PORT)

# Start orchestrator in dev mode with auto-reload
orchestrator-dev:
	@echo "Stopping any existing process on port $(ORCHESTRATOR_PORT)..."
	@-lsof -ti:$(ORCHESTRATOR_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Starting Orchestrator (DEV MODE, auto-reload)..."
	@echo "Health check: http://localhost:$(ORCHESTRATOR_PORT)/orchestrator/health"
	@echo "API docs: http://localhost:$(ORCHESTRATOR_PORT)/docs"
	@echo ""
	. venv/bin/activate && \
	ORCHESTRATOR_TEST_MODE=true \
	ORCHESTRATOR_CHECKPOINTER_TYPE=sqlite \
	python3 -m uvicorn app.orchestrator.app:app --host 0.0.0.0 --port $(ORCHESTRATOR_PORT) \
		--reload --reload-dir app/orchestrator --reload-dir app/agents

# Start orchestrator in production mode (no test mode, real agents)
orchestrator-prod:
	@echo "Stopping any existing process on port $(ORCHESTRATOR_PORT)..."
	@-lsof -ti:$(ORCHESTRATOR_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Starting Orchestrator (PRODUCTION MODE)..."
	@echo "Health check: http://localhost:$(ORCHESTRATOR_PORT)/orchestrator/health"
	@echo "API docs: http://localhost:$(ORCHESTRATOR_PORT)/docs"
	@echo ""
	. venv/bin/activate && \
	ORCHESTRATOR_CHECKPOINTER_TYPE=sqlite \
	python3 -m uvicorn app.orchestrator.app:app --host 0.0.0.0 --port $(ORCHESTRATOR_PORT)

# Stop the orchestrator
orchestrator-stop:
	@echo "Stopping orchestrator on port $(ORCHESTRATOR_PORT)..."
	@-lsof -ti:$(ORCHESTRATOR_PORT) | xargs kill -9 2>/dev/null || true
	@echo "Orchestrator stopped."

# Check orchestrator health
orchestrator-health:
	@curl -s http://localhost:$(ORCHESTRATOR_PORT)/orchestrator/health | python3 -m json.tool

# Get pipeline diagram from orchestrator
orchestrator-diagram:
	@curl -s http://localhost:$(ORCHESTRATOR_PORT)/orchestrator/pipeline/diagram | python3 -m json.tool

# List active pipelines
orchestrator-pipelines:
	@curl -s http://localhost:$(ORCHESTRATOR_PORT)/orchestrator/pipelines/active | python3 -m json.tool

# Clean orchestrator checkpoints
orchestrator-clean:
	@echo "Removing checkpoint database..."
	rm -f orchestrator_checkpoints.db
	@echo "Checkpoints cleared."
