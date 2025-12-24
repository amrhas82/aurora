# MCP Setup Guide

This guide explains how to integrate AURORA's MCP (Model Context Protocol) server with Claude Desktop, enabling Claude to search, index, and navigate your codebase directly from conversations.

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [macOS Configuration](#macos-configuration)
  - [Linux Configuration](#linux-configuration)
  - [Windows Configuration](#windows-configuration)
- [Usage Examples](#usage-examples)
- [Operating Modes](#operating-modes)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)
- [FAQ](#faq)

---

## Introduction

AURORA's MCP server provides Claude Desktop with five powerful tools for code navigation:

1. **aurora_search**: Semantic search over your indexed codebase
2. **aurora_index**: Index new files or directories
3. **aurora_stats**: View statistics about your indexed codebase
4. **aurora_context**: Retrieve file or function content
5. **aurora_related**: Find related code chunks through dependency relationships

**Benefits:**
- Natural language code search ("find authentication logic")
- Contextual code understanding (Claude knows your codebase structure)
- Faster development (no manual file copying)
- Memory persistence across conversations

---

## Prerequisites

Before setting up MCP integration, ensure you have:

1. **Python 3.10 or higher**
   ```bash
   python3 --version
   ```

2. **AURORA installed**
   ```bash
   pip install aurora
   # Or for development:
   pip install -e .
   ```

3. **Claude Desktop installed**
   - Download from: https://claude.ai/download
   - Verify installation by opening Claude Desktop

4. **Indexed codebase**
   ```bash
   # Index your project
   cd /path/to/your/project
   aur mem index .

   # Verify indexing worked
   aur mem stats
   ```

---

## Installation

AURORA's MCP server is automatically installed with the `aurora` package. No additional installation is required.

Verify the MCP server is available:

```bash
# Check if aurora-mcp script exists
which aurora-mcp

# Test the MCP server
python -m aurora.mcp.server --test
```

Expected output:
```
Aurora MCP Server initialized successfully
Available tools: aurora_search, aurora_index, aurora_stats, aurora_context, aurora_related
```

---

## Configuration

Configure Claude Desktop to use AURORA's MCP server by editing the Claude Desktop configuration file.

### macOS Configuration

1. **Locate the configuration file:**
   ```bash
   # Configuration file location
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. **Edit the configuration:**
   ```bash
   # Open in your preferred editor
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Or use VS Code
   code ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Add AURORA MCP server:**
   ```json
   {
     "mcpServers": {
       "aurora": {
         "command": "python3",
         "args": [
           "-m",
           "aurora.mcp.server"
         ],
         "env": {
           "AURORA_DB_PATH": "/Users/YOUR_USERNAME/.aurora/memory.db"
         }
       }
     }
   }
   ```

4. **Replace `YOUR_USERNAME`** with your actual username:
   ```bash
   # Find your username
   whoami
   ```

5. **Restart Claude Desktop** for changes to take effect.

### Linux Configuration

1. **Locate the configuration file:**
   ```bash
   # Configuration file location
   ~/.config/Claude/claude_desktop_config.json
   ```

2. **Edit the configuration:**
   ```bash
   # Create directory if it doesn't exist
   mkdir -p ~/.config/Claude

   # Edit configuration
   nano ~/.config/Claude/claude_desktop_config.json
   ```

3. **Add AURORA MCP server:**
   ```json
   {
     "mcpServers": {
       "aurora": {
         "command": "python3",
         "args": [
           "-m",
           "aurora.mcp.server"
         ],
         "env": {
           "AURORA_DB_PATH": "/home/YOUR_USERNAME/.aurora/memory.db"
         }
       }
     }
   }
   ```

4. **Replace `YOUR_USERNAME`** with your actual username:
   ```bash
   # Find your username
   whoami
   ```

5. **Restart Claude Desktop**.

### Windows Configuration

1. **Locate the configuration file:**
   ```powershell
   # Configuration file location
   %APPDATA%\Claude\claude_desktop_config.json

   # Full path (replace YOUR_USERNAME)
   C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\claude_desktop_config.json
   ```

2. **Edit the configuration:**
   - Open File Explorer
   - Paste the path: `%APPDATA%\Claude`
   - Edit `claude_desktop_config.json` with Notepad or VS Code

3. **Add AURORA MCP server:**
   ```json
   {
     "mcpServers": {
       "aurora": {
         "command": "python",
         "args": [
           "-m",
           "aurora.mcp.server"
         ],
         "env": {
           "AURORA_DB_PATH": "C:\\Users\\YOUR_USERNAME\\.aurora\\memory.db"
         }
       }
     }
   }
   ```

   **Note:** Use double backslashes (`\\`) in Windows paths!

4. **Replace `YOUR_USERNAME`** with your actual Windows username.

5. **Restart Claude Desktop**.

---

## Usage Examples

Once configured, you can ask Claude to search and navigate your codebase:

### Example 1: Search for Code

**You:** "Search my codebase for authentication logic"

**Claude uses:** `aurora_search("authentication login user credentials")`

**Claude responds:** "I found 3 relevant chunks in your codebase:
1. `auth.py`: `authenticate_user()` function (lines 45-67)
2. `middleware.py`: `verify_token()` function (lines 112-135)
3. `models.py`: `User` class with authentication methods (lines 89-145)"

### Example 2: Find All Usages

**You:** "Find all usages of the DatabaseConnection class"

**Claude uses:** `aurora_search("DatabaseConnection class usage import")`

**Claude responds:** "The `DatabaseConnection` class is used in 5 files:
- `db/connection.py`: Class definition
- `api/handlers.py`: Import and connection pooling
- `services/data_service.py`: Query execution
- `tests/test_db.py`: Unit tests
- `config/settings.py`: Connection configuration"

### Example 3: Understand a Module

**You:** "What does the UserService module do?"

**Claude uses:**
1. `aurora_search("UserService")`
2. `aurora_context("/path/to/services/user_service.py")`

**Claude responds:** "The `UserService` module provides user management functionality:
- User CRUD operations (create, read, update, delete)
- Password hashing and validation
- Email verification
- Session management
- Integration with authentication middleware"

### Example 4: Find Error Handling

**You:** "Show me error handling in the payment processing code"

**Claude uses:** `aurora_search("payment process error exception handling try catch")`

**Claude responds:** "Payment processing includes error handling in:
1. `payments/processor.py`: Try-except blocks for API failures
2. `payments/validators.py`: Input validation errors
3. `payments/retry.py`: Retry logic for transient failures
..."

---

## Operating Modes

AURORA's MCP server supports two operating modes:

### On-Demand Mode (Default)

- MCP server starts when Claude Desktop launches
- Stops when Claude Desktop closes
- Minimal resource usage
- **Best for:** Most users

**Configuration:** No additional configuration needed (default behavior)

### Always-On Mode

- MCP server runs continuously as a background service
- Slightly faster response times
- Uses more system resources
- **Best for:** Heavy users, large codebases

**Enable Always-On Mode:**
```bash
# Enable always-on mode
aurora-mcp start

# Check status
aurora-mcp status

# Disable always-on mode
aurora-mcp stop
```

---

## Troubleshooting

### Claude Desktop Can't Find MCP Server

**Symptom:** Claude says "I don't have access to aurora_search" or tools are missing

**Solutions:**

1. **Verify Python path in configuration:**
   ```bash
   # Find Python path
   which python3

   # Update claude_desktop_config.json with full path
   # Example: "/usr/local/bin/python3" instead of "python3"
   ```

2. **Check AURORA installation:**
   ```bash
   python3 -c "import aurora.mcp; print('OK')"
   ```

3. **Restart Claude Desktop completely:**
   - Quit Claude Desktop (Cmd+Q on macOS, not just close window)
   - Reopen Claude Desktop

4. **Check MCP logs:**
   ```bash
   # View MCP server logs
   tail -f ~/.aurora/mcp.log
   ```

### MCP Server Fails to Start

**Symptom:** Errors in Claude Desktop or MCP doesn't respond

**Solutions:**

1. **Test MCP server manually:**
   ```bash
   python3 -m aurora.mcp.server --test
   ```

2. **Check database path:**
   ```bash
   # Verify database exists
   ls -lh ~/.aurora/memory.db

   # If missing, reindex your codebase
   aur mem index /path/to/your/project
   ```

3. **Check permissions:**
   ```bash
   # Ensure ~/.aurora/ is writable
   chmod 755 ~/.aurora
   chmod 644 ~/.aurora/memory.db
   ```

### Search Returns No Results

**Symptom:** Claude can use tools but search returns empty results

**Solutions:**

1. **Verify codebase is indexed:**
   ```bash
   aur mem stats
   ```

   Should show:
   ```
   Total chunks: 1,234
   Total files: 56
   Database size: 12.5 MB
   ```

2. **Reindex if needed:**
   ```bash
   aur mem index --force /path/to/your/project
   ```

3. **Check file types:**
   ```bash
   # AURORA indexes .py files by default
   # Check if your files are included
   aur mem index --help
   ```

### Performance Issues

**Symptom:** MCP tools are slow to respond

**Solutions:**

1. **Check database size:**
   ```bash
   aur mem stats
   ```

   Large databases (>1GB) may need optimization.

2. **Enable always-on mode:**
   ```bash
   aurora-mcp start
   ```

3. **Adjust search limit:**
   ```bash
   # Edit ~/.aurora/config.json
   {
     "mcp": {
       "max_results": 5  # Reduce from default 10
     }
   }
   ```

For more troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## Advanced Configuration

### Custom Database Path

Use a project-specific database instead of the global one:

```json
{
  "mcpServers": {
    "aurora": {
      "command": "python3",
      "args": [
        "-m",
        "aurora.mcp.server",
        "--db-path",
        "/path/to/project/.aurora_db"
      ]
    }
  }
}
```

### Custom Configuration File

```json
{
  "mcpServers": {
    "aurora": {
      "command": "python3",
      "args": [
        "-m",
        "aurora.mcp.server",
        "--config",
        "/path/to/custom_config.json"
      ]
    }
  }
}
```

### Performance Tuning

Edit `~/.aurora/config.json`:

```json
{
  "mcp": {
    "always_on": false,
    "log_file": "~/.aurora/mcp.log",
    "max_results": 10
  },
  "context_code": {
    "hybrid_weights": {
      "activation": 0.6,
      "semantic": 0.4
    }
  }
}
```

**Configuration options:**
- `always_on`: Run MCP server continuously (default: false)
- `log_file`: Path to MCP log file
- `max_results`: Maximum search results returned (default: 10)
- `hybrid_weights`: Adjust activation vs semantic scoring

---

## FAQ

### Do I need an API key for MCP?

**No.** AURORA's MCP server uses local embeddings (Sentence-BERT) and doesn't require any API keys or internet connection.

### Can I use multiple MCP servers simultaneously?

**Yes.** Claude Desktop supports multiple MCP servers. Add additional entries to the `mcpServers` object:

```json
{
  "mcpServers": {
    "aurora": { ... },
    "other-mcp-server": { ... }
  }
}
```

### Does MCP slow down Claude Desktop?

**No.** MCP servers run independently and only activate when Claude calls them. There's minimal performance impact in on-demand mode.

### How often should I reindex my codebase?

**When code changes significantly:**
- After pulling major updates from Git
- After creating new modules or files
- Weekly for active development projects

Quick reindex:
```bash
aur mem index --force /path/to/project
```

### Can I index multiple projects?

**Yes, with project-specific databases:**

1. Index each project to its own database:
   ```bash
   aur mem index --db ~/project1.db ~/code/project1
   aur mem index --db ~/project2.db ~/code/project2
   ```

2. Configure Claude Desktop with both:
   ```json
   {
     "mcpServers": {
       "aurora-project1": {
         "command": "python3",
         "args": ["-m", "aurora.mcp.server", "--db-path", "/Users/you/project1.db"]
       },
       "aurora-project2": {
         "command": "python3",
         "args": ["-m", "aurora.mcp.server", "--db-path", "/Users/you/project2.db"]
       }
     }
   }
   ```

### What file types does AURORA index?

**Current support:**
- Python (`.py`)

**Coming soon:**
- JavaScript/TypeScript (`.js`, `.ts`, `.jsx`, `.tsx`)
- Java (`.java`)
- Go (`.go`)
- Rust (`.rs`)

### How much disk space does indexing use?

**Approximately:**
- 100 KB per Python file
- 10-50 MB for typical projects (100-500 files)
- 100-500 MB for large codebases (1,000-5,000 files)

Check your database size:
```bash
aur mem stats
```

### Can I exclude files or directories from indexing?

**Yes, use `.auroraignore` file:**

Create `.auroraignore` in your project root:
```
# Ignore test files
**/test_*.py
**/tests/

# Ignore build artifacts
**/build/
**/dist/
**/__pycache__/

# Ignore dependencies
**/node_modules/
**/venv/
```

Or use CLI flags:
```bash
aur mem index --exclude "tests" --exclude "venv" .
```

### Is my code data sent to Anthropic?

**No.** AURORA processes everything locally:
- Code indexing: local
- Embeddings: local (Sentence-BERT)
- Search: local database
- MCP server: runs on your machine

The only network communication is between Claude Desktop (local app) and Anthropic's servers for Claude's responses, but AURORA's search results are generated locally first.

---

## Getting Help

**Issues or questions?**

1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Run diagnostic: `aur --verify`
3. Check MCP logs: `tail -f ~/.aurora/mcp.log`
4. GitHub Issues: [github.com/your-org/aurora/issues](https://github.com/your-org/aurora/issues)

**Additional Resources:**

- [README.md](../README.md) - Quick start guide
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues
- [API Documentation](./api/) - Developer reference
- [MCP Protocol](https://modelcontextprotocol.io/) - Learn about MCP

---

**Last Updated:** 2025-12-24
**AURORA Version:** 0.2.0
