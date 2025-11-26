"""MCP Tools Server for Custom Agent Tools.

This module provides in-process MCP servers for custom tools used by
the connector generator agents. These tools run directly in Python
without subprocess overhead.
"""

import json
import logging
import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agent_sdk import tool, create_sdk_mcp_server

logger = logging.getLogger(__name__)

# HTTP timeout configuration
TIMEOUT_CONFIG = httpx.Timeout(
    connect=5.0,
    read=30.0,
    write=10.0,
    pool=5.0,
)
MAX_CONTENT_SIZE = 50000  # 50KB


# =============================================================================
# Research Tools
# =============================================================================

@tool(
    "fetch_github_file",
    "Fetch a specific file from a GitHub repository",
    {
        "repo": {"type": "string", "description": "Repository in format owner/repo"},
        "path": {"type": "string", "description": "File path within the repository"},
        "branch": {"type": "string", "description": "Branch name", "default": "main"},
    }
)
async def fetch_github_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch a file from GitHub raw content."""
    repo = args.get("repo", "")
    path = args.get("path", "")
    branch = args.get("branch", "main")

    if not repo or not path:
        return {"content": [{"type": "text", "text": "Error: repo and path are required"}]}

    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(url)
            response.raise_for_status()

            content = response.text[:MAX_CONTENT_SIZE]

            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "repo": repo,
                        "path": path,
                        "branch": branch,
                        "content": content,
                    })
                }]
            }

    except httpx.HTTPError as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error fetching {path} from {repo}: {str(e)}"
            }]
        }


@tool(
    "list_github_directory",
    "List files in a GitHub repository directory",
    {
        "repo": {"type": "string", "description": "Repository in format owner/repo"},
        "path": {"type": "string", "description": "Directory path within the repository"},
    }
)
async def list_github_directory(args: Dict[str, Any]) -> Dict[str, Any]:
    """List files in a GitHub directory via API."""
    repo = args.get("repo", "")
    path = args.get("path", "")

    if not repo:
        return {"content": [{"type": "text", "text": "Error: repo is required"}]}

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    try:
        headers = {"Accept": "application/vnd.github.v3+json"}

        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            items = response.json()
            files = []

            for item in items:
                files.append({
                    "name": item["name"],
                    "type": item["type"],
                    "path": item["path"],
                    "size": item.get("size", 0),
                })

            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "repo": repo,
                        "path": path,
                        "files": files,
                    })
                }]
            }

    except httpx.HTTPError as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error listing {path} in {repo}: {str(e)}"
            }]
        }


@tool(
    "fetch_url",
    "Fetch content from a URL with streaming and size limits",
    {
        "url": {"type": "string", "description": "URL to fetch content from"},
    }
)
async def fetch_url(args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch content from a URL with proper size limits."""
    url = args.get("url", "")

    if not url:
        return {"content": [{"type": "text", "text": "Error: url is required"}]}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CONFIG) as client:
            async with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                content_length = int(response.headers.get("content-length", 0))

                if content_length > MAX_CONTENT_SIZE:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Error: Content too large ({content_length} bytes)"
                        }]
                    }

                if "text" in content_type or "json" in content_type:
                    content = ""
                    async for chunk in response.aiter_text():
                        content += chunk
                        if len(content) > MAX_CONTENT_SIZE:
                            content = content[:MAX_CONTENT_SIZE]
                            break

                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "url": url,
                                "status": response.status_code,
                                "content": content,
                            })
                        }]
                    }
                else:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Binary content type: {content_type}"
                        }]
                    }

    except httpx.HTTPError as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error fetching {url}: {str(e)}"
            }]
        }


# =============================================================================
# Generator Tools
# =============================================================================

@tool(
    "save_generated_file",
    "Save a generated file to disk",
    {
        "path": {"type": "string", "description": "Relative file path (e.g., src/auth.py)"},
        "content": {"type": "string", "description": "Complete file content"},
        "description": {"type": "string", "description": "Brief description of the file"},
    }
)
async def save_generated_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save a generated file to the output directory."""
    path = args.get("path", "").strip().lstrip("/")
    content = args.get("content", "")
    description = args.get("description", "")

    if not path or not content:
        return {"content": [{"type": "text", "text": "Error: path and content are required"}]}

    # This will be called within the working directory context
    # The actual file saving happens via the Write tool or manually
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "status": "registered",
                "path": path,
                "size": len(content),
                "description": description,
            })
        }]
    }


# =============================================================================
# Tester Tools
# =============================================================================

@tool(
    "check_python_syntax",
    "Check Python syntax for a file",
    {
        "filepath": {"type": "string", "description": "Path to Python file"},
    }
)
async def check_python_syntax(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check Python syntax using compile()."""
    import ast

    filepath = args.get("filepath", "")

    if not filepath:
        return {"content": [{"type": "text", "text": "Error: filepath is required"}]}

    try:
        file_path = Path(filepath)
        if not file_path.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({"valid": False, "error": f"File not found: {filepath}"})
                }]
            }

        source = file_path.read_text()
        ast.parse(source)

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"filepath": filepath, "valid": True})
            }]
        }

    except SyntaxError as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "filepath": filepath,
                    "valid": False,
                    "error": f"Syntax error at line {e.lineno}: {e.msg}"
                })
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"filepath": filepath, "valid": False, "error": str(e)})
            }]
        }


# =============================================================================
# MCP Server Factory Functions
# =============================================================================

def create_research_mcp_server():
    """Create MCP server with research tools."""
    return create_sdk_mcp_server(
        name="research-tools",
        version="1.0.0",
        tools=[fetch_github_file, list_github_directory, fetch_url],
    )


def create_generator_mcp_server():
    """Create MCP server with generator tools."""
    return create_sdk_mcp_server(
        name="generator-tools",
        version="1.0.0",
        tools=[save_generated_file],
    )


def create_tester_mcp_server():
    """Create MCP server with tester tools."""
    return create_sdk_mcp_server(
        name="tester-tools",
        version="1.0.0",
        tools=[check_python_syntax],
    )


def get_all_mcp_servers() -> Dict[str, Any]:
    """Get all MCP servers for the connector generator.

    Returns:
        Dictionary mapping server names to server instances.
    """
    return {
        "research": create_research_mcp_server(),
        "generator": create_generator_mcp_server(),
        "tester": create_tester_mcp_server(),
    }
