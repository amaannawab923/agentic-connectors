# Publisher Agent - Documentation

## Overview

The Publisher Agent is a specialized agent that publishes generated connector code to a GitHub repository using Git operations with Personal Access Token authentication.

## Features

✅ **Git Repository Management**
- Initializes Git repository if needed
- Configures Git user identity
- Manages remote repository connections

✅ **Token-Based Authentication**
- Secure authentication using GitHub Personal Access Token
- No need for SSH keys or manual login

✅ **Branch Management**
- Creates new branches automatically
- Switches between branches safely
- Auto-generates branch names (format: `connector/<name>`)

✅ **Commit & Push**
- Stages all connector files
- Creates descriptive commit messages
- Pushes to remote repository

✅ **Safety Features**
- No destructive Git operations
- Validates operations before execution
- Clear error messages

## File Location

```
app/agents/publisher.py
```

## Usage

### Method 1: Using the Manual Script (Recommended)

Run the interactive publishing script:

```bash
cd /Users/amaannawab/research/connector-platform/connector-generator
python3 run_manual_publish.py
```

The script will prompt you for:
1. **GitHub Repository Owner** (e.g., `your-username` or `your-org`)
2. **GitHub Repository Name** (e.g., `connectors`)
3. **Personal Access Token** (your GitHub PAT)
4. **Branch Name** (optional, defaults to `connector/google-sheets`)

### Method 2: Programmatic Usage

```python
import asyncio
from pathlib import Path
from app.agents.publisher import PublisherAgent
from app.models.schemas import GeneratedFile

async def publish_connector():
    # Read connector files
    connector_dir = Path("./output/connector-implementations/source-google-sheets")
    generated_files = []

    for py_file in (connector_dir / "src").glob("*.py"):
        with open(py_file, 'r') as f:
            generated_files.append(GeneratedFile(
                path=f"src/{py_file.name}",
                content=f.read()
            ))

    # Create publisher agent
    publisher = PublisherAgent()

    # Execute publishing
    result = await publisher.execute(
        generated_files=generated_files,
        connector_name="google-sheets",
        output_dir=str(connector_dir),
        repo_owner="your-github-username",
        repo_name="connectors",
        personal_access_token="ghp_your_token_here",
        branch_name="connector/google-sheets",  # Optional
    )

    if result.success:
        print(f"✅ Published successfully: {result.output}")
    else:
        print(f"❌ Failed: {result.error}")

# Run
asyncio.run(publish_connector())
```

## API Reference

### PublisherAgent.execute()

Publishes connector code to a GitHub repository.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `generated_files` | `List[GeneratedFile]` | Yes | List of connector files to publish |
| `connector_name` | `str` | Yes | Name of the connector (e.g., "google-sheets") |
| `output_dir` | `str` | Yes | Path to connector directory |
| `repo_owner` | `str` | Yes | GitHub repository owner/org |
| `repo_name` | `str` | Yes | GitHub repository name |
| `personal_access_token` | `str` | Yes | GitHub Personal Access Token |
| `branch_name` | `str` | No | Custom branch name (auto-generated if not provided) |
| `repo_path` | `str` | No | Git repository path (defaults to output_dir) |
| `create_pr` | `bool` | No | Whether to create PR (default: True, requires `gh` CLI) |

**Returns:**

`AgentResult` with:
- `success`: Boolean indicating success/failure
- `output`: Branch name or PR URL
- `error`: Error message if failed
- `duration_seconds`: Execution time
- `tokens_used`: LLM tokens consumed

## GitHub Personal Access Token

### Creating a Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "Connector Generator")
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)

### Token Format

```
ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Security Best Practices

- ❌ **Never commit tokens to Git**
- ❌ **Never share tokens publicly**
- ✅ Store in environment variables
- ✅ Use `.env` files (add to `.gitignore`)
- ✅ Rotate tokens periodically
- ✅ Use minimum required scopes

## Git Operations Performed

The agent performs the following Git operations:

```bash
# 1. Initialize repository (if needed)
git init
git config user.name "Connector Generator"
git config user.email "generator@connectors.ai"

# 2. Configure remote with token authentication
git remote remove origin 2>/dev/null || true
git remote add origin https://<TOKEN>@github.com/<OWNER>/<REPO>.git

# 3. Create and checkout branch
git checkout -b <branch-name>

# 4. Stage files
git add .

# 5. Commit
git commit -m "feat: add <connector-name> connector

Generated connector implementation for <connector-name>.

Features:
- Authentication support
- Rate limiting and retry logic
- Error handling
- Schema inference
- Full type hints and documentation

Generated with Connector Generator v1.0"

# 6. Push to GitHub
git push -u origin <branch-name>

# 7. Get commit hash
git rev-parse HEAD
```

## Authentication URL Format

The agent uses HTTPS authentication with the token embedded in the URL:

```
https://<PERSONAL_ACCESS_TOKEN>@github.com/<OWNER>/<REPO>.git
```

**Example:**
```
https://ghp_abc123xyz@github.com/myorg/connectors.git
```

## Output Format

### Success Response

```json
{
  "success": true,
  "branch_name": "connector/google-sheets",
  "commit_hash": "abc123def456...",
  "remote_url": "https://github.com/owner/repo",
  "files_committed": 15,
  "message": "Successfully published connector to branch connector/google-sheets"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Authentication failed",
  "details": "remote: Permission to owner/repo.git denied..."
}
```

## Troubleshooting

### Common Errors

**1. Authentication Failed**
```
remote: Permission to owner/repo.git denied
```
**Solution:** Check that your Personal Access Token has the correct scopes (`repo` permission).

**2. Repository Not Found**
```
remote: Repository not found
```
**Solution:** Verify the repository owner and name are correct, and that the repository exists.

**3. Branch Already Exists**
```
fatal: A branch named 'connector/google-sheets' already exists
```
**Solution:** The agent will automatically checkout the existing branch. If you want to create a new branch, use a different branch name.

**4. Nothing to Commit**
```
nothing to commit, working tree clean
```
**Solution:** This is OK if files are already committed. The agent will still return success.

**5. Token Invalid**
```
remote: Invalid username or password
```
**Solution:** Your token may be expired or revoked. Generate a new token.

## Example: Complete Publishing Flow

```bash
# 1. Navigate to project
cd /Users/amaannawab/research/connector-platform/connector-generator

# 2. Run the publishing script
python3 run_manual_publish.py

# 3. Follow prompts:
#    - Enter repository owner
#    - Enter repository name
#    - Enter personal access token
#    - Optionally specify branch name

# 4. Confirm and publish

# 5. Check output for success/failure
```

## Integration with Pipeline

The publisher agent is typically the final step in the connector generation pipeline:

```
Research → Generate → Test → Fix → Review → Improve → Publish ✅
```

It can be integrated into the pipeline with:

```python
from app.agents.publisher import PublisherAgent

# In pipeline...
publish_result = await publisher.execute(
    generated_files=final_files,
    connector_name=request.connector_name,
    output_dir=connector_path,
    repo_owner=settings.github_repo_owner,
    repo_name=settings.github_repo_name,
    personal_access_token=settings.github_token.get_secret_value(),
)
```

## Configuration

Publisher agent settings in `app/config.py`:

```python
class Settings(BaseSettings):
    # Publisher allowed tools
    publisher_allowed_tools: List[str] = ["Read", "Bash"]

    # GitHub settings
    github_token: Optional[SecretStr] = None
    github_repo_owner: str = ""
    github_repo_name: str = "connectors"
    github_base_branch: str = "main"
```

Set via environment variables:

```bash
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=connectors
GITHUB_BASE_BRANCH=main
```

## Testing

Test the publisher agent without actually pushing:

```python
# Set create_pr=False and use a test repository
result = await publisher.execute(
    # ... parameters ...
    repo_name="test-connectors",  # Use a test repo
    create_pr=False,  # Don't create PR
)
```

## Best Practices

1. ✅ **Test with a test repository first** before publishing to production
2. ✅ **Use descriptive branch names** that include the connector name
3. ✅ **Review files before publishing** to ensure quality
4. ✅ **Keep tokens secure** in environment variables or secrets managers
5. ✅ **Use token rotation** for better security
6. ✅ **Monitor token usage** in GitHub settings

## Support

For issues or questions:
- Check the troubleshooting section above
- Review agent logs for detailed error messages
- Verify GitHub token permissions
- Ensure repository exists and is accessible

---

**Last Updated:** 2025-11-27
**Version:** 1.0.0
**Agent Type:** Publisher Agent
