# Claude Code Complete Setup Guide

> **Version installed:** 2.1.71  
> **Installation path:** `C:\Users\josla\.local\bin\claude.exe`  
> **Date:** March 7, 2026

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation (Completed)](#installation-completed)
3. [Adding to PATH (Completed)](#adding-to-path-completed)
4. [Authentication](#authentication)
5. [First Launch & Getting Started](#first-launch--getting-started)
6. [Essential Commands](#essential-commands)
7. [Configuration & Settings](#configuration--settings)
8. [Memory & Instructions (CLAUDE.md)](#memory--instructions-claudemd)
9. [VS Code Integration](#vs-code-integration)
10. [Best Practices](#best-practices)
11. [Advanced Features](#advanced-features)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before using Claude Code, ensure you have:

- ✅ **Windows with PowerShell** (you're on Windows)
- ✅ **Git for Windows** - Required for Claude Code on Windows. Download from https://git-scm.com/downloads/win if not installed
- ✅ **A Claude subscription** - One of:
  - Claude Pro, Max, Teams, or Enterprise (claude.com/pricing)
  - Claude Console account (console.anthropic.com)
  - Cloud provider access (Amazon Bedrock, Google Vertex AI, or Microsoft Foundry)

---

## Installation (Completed)

You've already installed Claude Code using:

```powershell
irm https://claude.ai/install.ps1 | iex
```

**Other installation methods available:**

| Method | Command |
|--------|---------|
| Windows CMD | `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd` |
| Homebrew | `brew install anthropic/tap/claude-code` |
| WinGet | `winget install Anthropic.ClaudeCode` |

> **Note:** Native installations automatically update in the background.

---

## Adding to PATH (Completed)

The PATH has been updated. The following was added to your User PATH:

```
C:\Users\josla\.local\bin
```

**To verify in a new terminal:**

```powershell
claude --version
```

> **Important:** You may need to restart your terminal or VS Code for the PATH change to take effect in all sessions.

---

## Authentication

### Step 1: Run Claude for the first time

```powershell
cd c:\git\ClaudeCodeSetup   # Or any project directory
claude
```

### Step 2: Log in when prompted

Claude Code will open a browser window for authentication. If it doesn't open automatically, press `c` to copy the login URL to your clipboard.

**Authentication options:**

| Account Type | Description |
|--------------|-------------|
| **Claude Pro/Max** | Personal subscription via claude.com |
| **Claude Teams/Enterprise** | Team account via admin invite |
| **Claude Console** | API-based billing (console.anthropic.com) |
| **Cloud Providers** | Bedrock, Vertex AI, or Microsoft Foundry |

### Step 3: Verify login

Once logged in, your credentials are stored securely. You won't need to log in again.

**Commands:**
- `/login` - Re-authenticate or switch accounts
- `/logout` - Sign out

---

## First Launch & Getting Started

### Start Claude Code in any project

```powershell
cd /path/to/your/project
claude
```

### Your first prompts

Try these to explore your codebase:

```
what does this project do?
what technologies does this project use?
where is the main entry point?
explain the folder structure
```

### Make your first code change

```
add a hello world function to the main file
```

Claude will:
1. Find the appropriate file
2. Show you the proposed changes
3. Ask for your approval
4. Make the edit

---

## Essential Commands

### Terminal Commands

| Command | Description | Example |
|---------|-------------|---------|
| `claude` | Start interactive mode | `claude` |
| `claude "task"` | Run a one-time task | `claude "fix the build error"` |
| `claude -p "query"` | Run query, then exit | `claude -p "explain this function"` |
| `claude -c` | Continue most recent conversation | `claude -c` |
| `claude -r` | Resume a previous conversation | `claude -r` |
| `claude commit` | Create a Git commit | `claude commit` |
| `claude --help` | Show all CLI options | `claude --help` |

### In-Session Commands (Slash Commands)

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/compact` | Compress context to save tokens |
| `/config` | Open settings interface |
| `/init` | Generate starter CLAUDE.md |
| `/memory` | View/edit memory files |
| `/model` | Switch AI model |
| `/permissions` | Configure allowed tools |
| `/status` | Show active settings |
| `/login` | Re-authenticate |
| `/logout` | Sign out |
| `exit` or `Ctrl+C` | Exit Claude Code |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Esc` | Stop Claude mid-action |
| `Esc + Esc` | Open rewind menu |
| `Ctrl+G` | Open plan in editor (Plan Mode) |
| `Shift+Enter` | Add new line without sending |

---

## Configuration & Settings

### Settings Locations

Claude Code uses hierarchical settings with multiple scopes:

| Scope | Location | Purpose |
|-------|----------|---------|
| **User** | `~/.claude/settings.json` | Personal preferences across all projects |
| **Project** | `.claude/settings.json` | Team-shared settings (committed to git) |
| **Local** | `.claude/settings.local.json` | Personal project overrides (gitignored) |

### Create User Settings

```powershell
# Create settings directory if it doesn't exist
mkdir -Force "$env:USERPROFILE\.claude"

# Create settings file
notepad "$env:USERPROFILE\.claude\settings.json"
```

**Example settings.json:**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test *)",
      "Bash(git status)",
      "Bash(git diff *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  },
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1"
  }
}
```

### Permission Modes

| Mode | Description |
|------|-------------|
| **Normal** (default) | Claude asks permission before each action |
| **Plan Mode** | Claude describes what it will do and waits for approval |
| **Auto-accept** | Claude makes edits without asking |
| **Bypass** | Use `--dangerously-skip-permissions` for automation (use with caution!) |

---

## Memory & Instructions (CLAUDE.md)

### What is CLAUDE.md?

CLAUDE.md is a special file that Claude reads at the start of every conversation. Use it for:
- Build commands and test instructions
- Code style preferences
- Project architecture notes
- Workflow rules

### Generate Starter CLAUDE.md

```
/init
```

This analyzes your codebase and creates a starting file.

### CLAUDE.md Locations

| Location | Scope | Purpose |
|----------|-------|---------|
| `~/.claude/CLAUDE.md` | Global | Personal preferences for all projects |
| `./CLAUDE.md` | Project | Team-shared instructions |
| `./.claude/CLAUDE.md` | Project (alt) | Alternative project location |
| `./CLAUDE.local.md` | Local | Personal project-specific (gitignored) |

### Example CLAUDE.md

```markdown
# Code Style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (e.g., import { foo } from 'bar')
- Use 2-space indentation

# Workflow
- Run `npm run lint` before committing
- Prefer running single tests, not the whole test suite

# Project Notes
- Main entry point: src/index.ts
- API handlers live in src/api/handlers/
```

### Tips for CLAUDE.md

- **Keep it under 200 lines** - Longer files reduce adherence
- **Be specific** - "Use 2-space indentation" beats "format code properly"
- **Only include what Claude can't infer** - Skip obvious conventions
- **Review regularly** - Remove outdated instructions

---

## VS Code Integration

### Install the Extension

1. Open VS Code
2. Press `Ctrl+Shift+X` (Extensions view)
3. Search for "Claude Code"
4. Click Install

Or install directly: [Install for VS Code](vscode:extension/anthropic.claude-code)

### Getting Started in VS Code

1. **Open Claude panel** - Click the Spark icon (✱) in the top-right of the editor
2. **Send a prompt** - Ask Claude about your code
3. **Review changes** - Accept, reject, or modify proposed edits

### VS Code Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Esc` / `Ctrl+Esc` | Toggle focus between editor and Claude |
| `Cmd+Shift+Esc` / `Ctrl+Shift+Esc` | Open Claude in new tab |
| `Option+K` / `Alt+K` | Insert @-mention reference to selection |
| `Cmd+N` / `Ctrl+N` | New conversation (when Claude is focused) |

### Key Features

- **@-mentions** - Type `@filename` to reference specific files
- **Selection context** - Claude automatically sees your selected text
- **Diff preview** - Review changes side-by-side before accepting
- **Multiple conversations** - Open in new tabs for parallel work

---

## Best Practices

### 1. Give Claude a Way to Verify Its Work

Include tests, screenshots, or expected outputs:

```
write a validateEmail function. Test cases:
- user@example.com → true
- invalid → false  
- user@.com → false
Run the tests after implementing.
```

### 2. Explore First, Then Plan, Then Code

Use Plan Mode for complex tasks:

1. **Explore** - Enter Plan Mode, ask Claude to read and understand
2. **Plan** - Ask Claude to create a detailed implementation plan
3. **Implement** - Switch to Normal Mode and execute
4. **Commit** - Ask Claude to commit and create a PR

### 3. Be Specific with Context

| Instead of | Try |
|------------|-----|
| "add tests for foo.py" | "write a test for foo.py covering the edge case where the user is logged out. avoid mocks." |
| "fix the login bug" | "users report that login fails after session timeout. check the auth flow in src/auth/, especially token refresh." |

### 4. Manage Context Aggressively

- `/clear` between unrelated tasks
- `/compact` when context is filling up
- Use subagents for investigation tasks

### 5. Use CLI Tools

Claude works great with CLI tools like `gh`, `aws`, `gcloud`:

```
Use 'gh issue view 123' to understand the bug, then fix it
```

---

## Advanced Features

### MCP Servers (Model Context Protocol)

Connect external tools like GitHub, databases, and APIs:

```powershell
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
```

Manage with `/mcp` in a session.

### Skills

Create reusable workflows in `.claude/skills/`:

```markdown
<!-- .claude/skills/fix-issue/SKILL.md -->
---
name: fix-issue
description: Fix a GitHub issue
---
Analyze and fix the GitHub issue: $ARGUMENTS.

1. Use `gh issue view` to get issue details
2. Search the codebase for relevant files
3. Implement the fix
4. Write and run tests
5. Create a descriptive commit
6. Open a PR
```

Invoke with `/fix-issue 1234`

### Hooks

Run scripts automatically at specific points:

```json
{
  "hooks": {
    "PostEdit": [{
      "matcher": "**/*.py",
      "hooks": [{
        "type": "command",
        "command": "black $FILE"
      }]
    }]
  }
}
```

Configure with `/hooks` or edit `.claude/settings.json`.

### Subagents

Delegate tasks to specialized agents:

```
Use a subagent to review the code for security issues
```

Define custom subagents in `.claude/agents/`.

### Git Worktrees

Run isolated sessions:

```powershell
claude --worktree feature-auth
```

---

## Troubleshooting

### Claude Command Not Found

If `claude` command not found after restarting terminal:

```powershell
# Refresh PATH in current session
$env:PATH = [Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [Environment]::GetEnvironmentVariable("PATH", "Machine")

# Verify
claude --version
```

### Authentication Issues

```powershell
# Re-authenticate
claude
# Then run /logout and /login
```

### Context Running Low

```
/compact Focus on the current task
```

Or start fresh:

```
/clear
```

### Check Status

```
/status
```

Shows active settings sources and configuration.

### Get Help

- In Claude Code: `/help`
- Documentation: https://code.claude.com/docs
- Community: https://discord.gg/anthropic

---

## Quick Reference Card

### Daily Workflow

```powershell
# Start session in project
cd your-project
claude

# Or continue previous session
claude -c

# Or run one-off query
claude -p "what does main.py do?"
```

### Common Prompts

```
what does this project do?
explain the @src/auth folder
add error handling to the API endpoint
write tests for the UserService class
commit my changes with a descriptive message
create a PR for this feature
```

### Session Management

```
/clear           # Reset context
/compact         # Compress context
Esc + Esc        # Rewind to checkpoint
/memory          # View/edit instructions
```

---

## Next Steps

1. **Start your first session**: Run `claude` in a project directory
2. **Create a CLAUDE.md**: Run `/init` for a starter file
3. **Install VS Code extension**: For IDE integration
4. **Explore common workflows**: https://code.claude.com/docs/en/common-workflows
5. **Set up MCP servers**: For GitHub, databases, etc.

---

## Resources

- **Documentation**: https://code.claude.com/docs
- **Quickstart**: https://code.claude.com/docs/en/quickstart
- **Settings**: https://code.claude.com/docs/en/settings
- **Best Practices**: https://code.claude.com/docs/en/best-practices
- **Troubleshooting**: https://code.claude.com/docs/en/troubleshooting
