# Connector Generator - Claude Agent SDK Project

This document provides conventions and context for Claude Agent SDK operations within the connector-generator project.

## Project Overview

The Connector Generator is a multi-agent system that automatically generates data connectors using Claude Agent SDK. Each agent specializes in a specific phase of the connector generation pipeline.

## Architecture

### Pipeline Flow
```
Research → Generate → Test → Fix (retry loop) → Review → Improve (retry loop) → Publish
```

### Agent Types

| Agent | Purpose | Allowed Tools |
|-------|---------|---------------|
| ResearchAgent | API documentation research | WebSearch, WebFetch, Read, Bash |
| GeneratorAgent | Code generation | Read, Write, Bash |
| TesterAgent | Test execution | Read, Bash |
| ReviewerAgent | Code review | Read |
| PublisherAgent | Git operations | Read, Bash |

## Claude Agent SDK Configuration

### Tool Allowlists

Each agent has a strict tool allowlist defined in `app/config.py`:

```python
research_allowed_tools: ["Read", "WebFetch", "WebSearch", "Bash"]
generator_allowed_tools: ["Read", "Write", "Bash"]
tester_allowed_tools: ["Read", "Bash"]
reviewer_allowed_tools: ["Read"]
publisher_allowed_tools: ["Read", "Bash"]
```

### Permission Modes

- **Default**: `acceptEdits` - Automatically accepts file edits within working directory
- **Development**: `bypassPermissions` - For testing only
- **Production**: `default` - Requires user approval for destructive operations

### Security Hooks

The project uses PreToolUse hooks to block dangerous operations:

**Blocked Bash Patterns:**
- `rm -rf /` or `rm -rf ~`
- `git push --force`
- `git reset --hard`
- `git --no-verify`
- `curl | sh` or `wget | sh`
- `sudo` commands
- `chmod 777`

**Path Restrictions:**
- Write operations blocked outside working directory
- Path traversal (`..`) not allowed

## Directory Structure

```
connector-generator/
├── app/
│   ├── agents/
│   │   ├── __init__.py      # Agent exports
│   │   ├── base.py          # BaseAgent with SDK client
│   │   ├── research.py      # ResearchAgent
│   │   ├── generator.py     # GeneratorAgent
│   │   ├── tester.py        # TesterAgent
│   │   ├── reviewer.py      # ReviewerAgent
│   │   ├── publisher.py     # PublisherAgent
│   │   ├── hooks.py         # Security hooks
│   │   └── mcp_tools.py     # MCP server tools
│   ├── core/
│   │   ├── pipeline.py      # Pipeline orchestrator
│   │   ├── budget.py        # Budget controller
│   │   └── state.py         # State management
│   ├── models/
│   │   ├── enums.py         # Enumerations
│   │   └── schemas.py       # Pydantic schemas
│   └── config.py            # Settings
├── generated/               # Generated connector output
├── tests/                   # Test files
├── requirements.txt         # Dependencies
└── CLAUDE.md               # This file
```

## Generated Connector Structure

When generating connectors, use this file structure:

```
source-{connector-name}/
├── src/
│   ├── __init__.py         # Package exports
│   ├── auth.py             # Authentication handling
│   ├── client.py           # API client with rate limiting
│   ├── config.py           # Pydantic configuration
│   ├── connector.py        # Main connector class
│   ├── streams.py          # Data stream definitions
│   └── utils.py            # Utility functions
├── tests/
│   └── test_connector.py   # Unit tests
└── requirements.txt        # Dependencies
```

## Code Style Conventions

### Python
- Use Python 3.11+ features
- Complete type hints on all functions
- Pydantic models for configuration
- Custom exceptions for error handling
- Async/await for I/O operations

### Documentation
- Docstrings for all public classes and methods
- Google-style docstring format
- Inline comments for complex logic only

### Error Handling
```python
# Custom exceptions in each module
class ConnectorError(Exception):
    """Base exception for connector errors."""
    pass

class AuthenticationError(ConnectorError):
    """Authentication failed."""
    pass

class RateLimitError(ConnectorError):
    """API rate limit exceeded."""
    pass
```

### Rate Limiting Pattern
```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def make_request(self, endpoint: str) -> dict:
    """Make API request with retry logic."""
    ...
```

## Budget Constraints

- **Max budget**: $7.00 per connector generation
- **Warning threshold**: $5.00 (log warnings)
- **Force publish threshold**: $6.00 (skip remaining iterations)

## Environment Variables

Required environment variables:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
CLAUDE_MODEL=claude-sonnet-4-20250514
MAX_BUDGET=7.0
MAX_TURNS=50
PERMISSION_MODE=acceptEdits
OUTPUT_BASE_DIR=./generated
```

## MCP Server Integration

Custom MCP tools are available for research operations:

```python
# Available MCP tools
mcp__research__fetch_github_file   # Fetch file from GitHub repo
mcp__research__list_github_dir     # List GitHub directory contents
mcp__research__fetch_url           # Fetch and extract URL content
```

## Testing Generated Connectors

The TesterAgent validates code through:

1. **Syntax Check**: `python -m py_compile src/*.py`
2. **Import Validation**: Verify all modules import correctly
3. **Unit Tests**: `pytest tests/ -v` if tests exist
4. **Connection Test**: (if credentials provided)
5. **Data Fetch Test**: (if credentials provided)

## Common Patterns

### Agent Execution
```python
result = await agent.execute(
    connector_name="google-sheets",
    connector_type="source",
    ...
)
if result.success:
    process(result.output)
else:
    handle_error(result.error)
```

### Streaming Responses
```python
async with ClaudeSDKClient(options=options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        process_message(message)
```

### File Generation
Generated files are saved to `{output_base_dir}/source-{connector_name}/`

## Troubleshooting

### Common Issues

1. **Budget Exceeded**: Pipeline stops at force_publish_threshold
2. **Test Failures**: Max 3 retry attempts before failing
3. **Review Rejections**: Max 2 improvement cycles
4. **Hook Denials**: Check hooks.py for blocked patterns

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger("app.agents").setLevel(logging.DEBUG)
```

## References

- [Claude Agent SDK Documentation](https://docs.anthropic.com/claude-agent-sdk)
- [MCP Protocol](https://modelcontextprotocol.io)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
