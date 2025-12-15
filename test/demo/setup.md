# Labrynth Demo Guide

A step-by-step screen recording guide for demonstrating how to set up and use Labrynth.

> **Source Code Location:** `../temp prefect/labrynth-framework`

---

## Prerequisites

Before starting the demo, ensure you have:
- Python 3.10+ installed
- Node.js (for UI builds, if needed)
- Terminal/command line access

---

## Step 1: Create a New Project Folder

```bash
# Create a new directory for your labrynth project
mkdir my-labrynth-demo

# Navigate into the folder
cd my-labrynth-demo
```

**What to show:** Creating an empty folder where we'll set up our labrynth project.

---

## Step 2: Create a Virtual Environment

```bash
# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

**What to show:** The prompt should change to show `(venv)` indicating the virtual environment is active.

---

## Step 3: Install Labrynth from Source

```bash
# Install labrynth from the local source directory
pip install -e "/Users/amaannawab/research/temp prefect/labrynth-framework"
```

**What to show:**
- The installation process
- Successful installation message

**Verify installation:**
```bash
labrynth --version
```

---

## Step 4: Initialize a Labrynth Project
  pip install -e "$LABRYNTH_SRC"

```bash
# Initialize with the "basic" template (includes example agents)
labrynth init . --template basic
```

**What to show:**
- The initialization output showing created files:
  - `labrynth.yaml` - Project configuration
  - `.labrynthignore` - Files to ignore
  - `agents/` - Directory for your agents
  - `agents/example.py` - Example agent file

**Alternative (minimal init):**
```bash
# For a blank project without examples:
labrynth init . --template blank

# Or minimal config only:
labrynth init .
```

---

## Step 5: Explore the Project Structure

```bash
# Show the project structure
ls -la

# View the configuration file
cat labrynth.yaml
```

**Expected `labrynth.yaml` content:**
```yaml
name: my-labrynth-demo
version: 0.1.0
agents:
  paths:
  - agents/
  auto_discover: true
  watch: true
server:
  host: 127.0.0.1
  port: 8000
  debug: false
```

---

## Step 6: View the Example Agent

```bash
# Open and view the example agent
cat agents/example.py
```

**Example agent code:**
```python
from labrynth import agent

@agent(
    name="Hello World",
    description="A simple example agent that greets the world",
    tags=["example", "demo"]
)
def hello_world():
    """Say hello to the world."""
    print("Hello from Agent!")
    return {"message": "Hello, World!"}
```

**Key points to highlight:**
- The `@agent` decorator registers functions as agents
- `name` - Display name in the UI
- `description` - What the agent does
- `tags` - For organizing/filtering agents

---

## Step 7: Create Your Own Agent (Optional)

Add a new agent to `agents/example.py`:

```python
@agent(
    name="Demo Agent",
    description="A custom agent for the demo",
    tags=["demo", "custom"]
)
def demo_agent(message: str = "Hello"):
    """A demo agent that processes a message.

    Args:
        message: The message to process
    """
    result = f"Processed: {message.upper()}"
    print(result)
    return {"result": result}
```

---

## Step 8: Deploy the Agents

```bash
# Deploy agents to the database
labrynth deploy
```

**What to show:**
- Agents being discovered and registered
- Deployment success message

---

## Step 9: Start the Labrynth Server

```bash
# Start the server
labrynth server start
```

**What to show:**
- Server startup message
- The URL where the server is running (http://127.0.0.1:8000)

---

## Step 10: View Agents in the UI

Open your browser and navigate to:

```
http://localhost:8000
```

**What to show in the UI:**
1. The dashboard/home page
2. List of registered agents
3. Click on an agent to see details
4. Agent parameters and description
5. Run an agent and see the output

---

## Quick Reference Commands

| Command | Description |
|---------|-------------|
| `labrynth init . --template basic` | Initialize project with examples |
| `labrynth deploy` | Deploy/register agents |
| `labrynth server start` | Start the web server |
| `labrynth --help` | Show all available commands |

---

## Development Workflow (Using Makefile)

If using the provided Makefile from the test project:

```bash
# Full development cycle: install + build UI + deploy + start server
make dev

# Quick refresh: reinstall + rebuild UI + auto-deploy server
make refresh

# Just start the server with auto-deploy
make dev-server

# Clean the database
make clean
```

---

## Demo Script Summary

1. **Create folder** → `mkdir my-labrynth-demo && cd my-labrynth-demo`
2. **Virtual env** → `python -m venv venv && source venv/bin/activate`
3. **Install** → `pip install -e "../temp prefect/labrynth-framework"`
4. **Initialize** → `labrynth init . --template basic`
5. **Deploy** → `labrynth deploy`
6. **Start** → `labrynth server start`
7. **View UI** → Open `http://localhost:8000`

---

## Recording Tips

- Use cursor highlighting (Presentify, PowerToys, etc.)
- Zoom in on important commands
- Pause briefly after each command to show output
- Use a clean terminal with larger font size
- Consider using Screen Studio for auto-follow cursor effects


  # Set the variable
  export LABRYNTH_SRC="/Users/amaannawab/research/temp prefect/labrynth-framework"

  # Use it


  The quotes around "$LABRYNTH_SRC" are required because your path has a space in temp prefect.

  You can verify it's set:
  echo $LABRYNTH_SRC
