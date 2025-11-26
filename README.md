# Agentic Connectors

> **AI-powered data connector generation using multi-agent orchestration**

An autonomous system that generates production-ready data connectors using Claude AI agents orchestrated by LangGraph. Give it an API name, and it researches, codes, tests, reviews, and publishes a complete connector—all without human intervention.

---

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Research   │────▶│  Generator  │────▶│   Tester    │────▶│ Test Review  │────▶│  Reviewer   │
│    Agent    │     │    Agent    │     │    Agent    │     │    Agent     │     │    Agent    │
└─────────────┘     └─────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
      │                   ▲                   ▲                    │                    │
      │                   │                   │                    │                    │
      │                   └───────────────────┴────────────────────┘                    │
      │                        (Retry loops with intelligent feedback)                  │
      │                                                                                 ▼
      │                                                                          ┌─────────────┐
      └──────────────────────────────────────────────────────────────────────────│  Publisher  │
                                                                                 │    Agent    │
                                                                                 └─────────────┘
```

### The Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Research Agent** | Searches the web for API documentation, authentication patterns, rate limits, and existing implementations | `WebSearch`, `WebFetch`, `Read` |
| **Generator Agent** | Writes production-quality Python connector code with proper error handling, retries, and type hints | `Read`, `Write`, `Edit`, `Bash` |
| **Tester Agent** | Creates comprehensive test suites with mock servers, runs pytest, identifies bugs | `Read`, `Write`, `Bash`, `WebSearch` |
| **Test Reviewer Agent** | Analyzes test failures to determine root cause—is it buggy code or buggy tests? | `Read` |
| **Reviewer Agent** | Code review for quality, security, and best practices | `Read` |
| **Publisher Agent** | Packages and publishes the connector | `Read`, `Bash` |

### Intelligent Retry Loops

The system doesn't just fail on errors—it learns and adapts:

- **Tests fail?** → Test Reviewer determines if code is buggy (route to Generator) or tests are buggy (route to Tester)
- **Generator fixes code** → Tester runs in `RERUN` mode (fast, just re-runs existing tests)
- **Tests are invalid** → Tester runs in `FIX` mode (repairs test infrastructure)
- **Code review rejects** → Generator improves based on specific feedback

---

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key (Claude)

### Installation

```bash
# Clone the repository
git clone https://github.com/amaannawab923/agentic-connectors.git
cd agentic-connectors

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"
```

### Generate a Connector

```bash
# Start the orchestrator
python -m uvicorn app.orchestrator.app:app --host 0.0.0.0 --port 8002

# In another terminal, trigger a connector generation
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{"connector_name": "google-sheets", "connector_type": "source"}'
```

### Run Individual Agents Manually

```bash
# Research only
python run_research_manually.py

# Generate code
python run_generator_manually.py

# Run tests
python run_tester_manually.py

# Review test results
python run_test_reviewer_manually.py

# Re-run tests (after code fix)
python run_tester_rerun_manually.py
```

---

## Architecture

### Tech Stack

- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) - StateGraph for agent workflow
- **AI Agents**: [Claude Agent SDK](https://docs.anthropic.com) - Claude Opus 4.5 with tool use
- **State Persistence**: SQLite checkpointing for resumable workflows
- **API Framework**: FastAPI with async support

### Project Structure

```
agentic-connectors/
├── app/
│   ├── agents/                 # Claude Agent SDK implementations
│   │   ├── base.py            # BaseAgent with streaming & token tracking
│   │   ├── research.py        # API documentation research
│   │   ├── generator.py       # Code generation (GENERATE/FIX modes)
│   │   ├── tester.py          # Testing (GENERATE/RERUN/FIX modes)
│   │   ├── test_reviewer.py   # Test failure analysis
│   │   ├── reviewer.py        # Code review
│   │   └── publisher.py       # Publishing
│   ├── orchestrator/          # LangGraph pipeline
│   │   ├── app.py             # FastAPI application
│   │   ├── pipeline.py        # StateGraph definition
│   │   ├── state.py           # PipelineState schema
│   │   └── nodes/             # Node implementations
│   │       ├── real_agents.py # Production agent nodes
│   │       └── mock_agents.py # Testing/development nodes
│   └── models/                # Pydantic schemas
├── output/                    # Generated connectors
│   └── connector-implementations/
│       └── source-google-sheets/
│           ├── src/           # Connector source code
│           └── tests/         # Generated test suite
└── run_*_manually.py          # Manual execution scripts
```

### Generated Connector Structure

Each generated connector follows a consistent, production-ready structure:

```
source-{connector-name}/
├── src/
│   ├── __init__.py         # Package exports
│   ├── connector.py        # Main connector class (spec, check, discover, read)
│   ├── config.py           # Pydantic configuration with validation
│   ├── auth.py             # Authentication handlers
│   ├── client.py           # API client with rate limiting & retries
│   ├── streams.py          # Data stream definitions
│   └── utils.py            # Helper utilities
├── tests/
│   ├── conftest.py         # Mock fixtures (httpretty)
│   ├── test_config.py      # Configuration validation tests
│   ├── test_connection.py  # Connection check tests
│   ├── test_discovery.py   # Schema discovery tests
│   ├── test_read.py        # Data reading tests
│   └── test_results.json   # Structured test output
├── requirements.txt
├── IMPLEMENTATION.md       # Detailed implementation docs
└── README.md
```

---

## Agent Modes

### Tester Agent Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| `GENERATE` | First run | Full test creation with WebSearch for patterns |
| `RERUN` | After Generator fix | Just run existing tests (15 turns, fast) |
| `FIX` | TestReviewer says tests invalid | Fix test infrastructure, then run (40 turns) |

### Generator Agent Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| `GENERATE` | Initial generation | Create connector from research |
| `FIX` | TestReviewer says code buggy | Fix code to pass existing tests (3 retries) |

---

## Example: Google Sheets Connector

The system generated a complete Google Sheets connector with:

- **Authentication**: Service Account & OAuth2 support with Pydantic discriminated unions
- **Rate Limiting**: Configurable requests per minute
- **Batching**: Efficient row fetching with configurable batch sizes
- **Schema Discovery**: Automatic type inference from sheet data
- **Error Handling**: Retry logic with exponential backoff
- **117 Tests**: Comprehensive test suite with mocked Google API

```python
# Generated config.py excerpt
class GoogleSheetsConfig(BaseModel):
    spreadsheet_id: str = Field(..., pattern=r"^[a-zA-Z0-9-_]+$")
    credentials: Union[ServiceAccountCredentials, OAuth2Credentials] = Field(
        ..., discriminator="auth_type"
    )
    row_batch_size: int = Field(default=200, ge=1, le=1000)
    requests_per_minute: int = Field(default=60, ge=1, le=300)
```

---

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
CLAUDE_MODEL=claude-opus-4-5-20251101
ORCHESTRATOR_TEST_MODE=true          # Use SQLite checkpointing
ORCHESTRATOR_CHECKPOINTER_TYPE=sqlite
```

### Pipeline Thresholds

- **Max test retries**: 3 (before failing)
- **Max generator fix retries**: 3 (before failing)
- **Max review cycles**: 2 (before force publish)

---

## Development

### Running Tests

```bash
# Verify syntax
python -m py_compile app/agents/*.py

# Run the orchestrator in test mode
export ORCHESTRATOR_TEST_MODE=true
export ORCHESTRATOR_CHECKPOINTER_TYPE=sqlite
python -m uvicorn app.orchestrator.app:app --port 8002
```

### Adding New Agents

1. Create agent class in `app/agents/` extending `BaseAgent`
2. Define system prompt with tool instructions
3. Implement `execute()` method
4. Add node function in `app/orchestrator/nodes/real_agents.py`
5. Wire into pipeline in `app/orchestrator/pipeline.py`

---

## Roadmap

- [ ] Destination connector support (write to APIs)
- [ ] Parallel agent execution for independent tasks
- [ ] Web UI for monitoring pipeline progress
- [ ] Support for more LLM providers (OpenAI, local models)
- [ ] Connector marketplace integration

---

## License

MIT

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

<p align="center">
  <strong>Built with Claude Agent SDK + LangGraph</strong><br>
  <em>Let AI write your data connectors</em>
</p>
