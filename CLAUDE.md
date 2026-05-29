# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

**AI Connector Marketplace** is a local "app store" for MCP (Model Context Protocol) servers. It lets users browse, install, and configure MCP servers for **Claude Desktop** through a web interface — eliminating manual editing of `claude_desktop_config.json`.

The core insight: installing MCP servers today is a manual, error-prone process (find the server, run npm/pip, hand-edit JSON config, restart). This project automates all of it behind a one-click UI.

## Architecture

This is a **local-first** application. The backend runs on the user's own machine because it needs to:
1. Read/write `claude_desktop_config.json` (filesystem access)
2. Run installers via subprocess (`npm`, `pip`, `uvx`, `docker`)
3. Handle local environment variables and secrets

It is **NOT** meant to be deployed to a public server. Think of it like a desktop tool with a web UI (similar to how Jupyter or Vite dev servers work).

```
┌─────────────────┐     HTTP      ┌──────────────────┐
│  Frontend (UI)  │ ────────────► │  Backend (API)   │
│  localhost:3000 │ ◄──────────── │  localhost:8000  │
│  [Phase 2]      │               │  [Phase 1 ✅]    │
└─────────────────┘               └────────┬─────────┘
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                   ┌────────────┐  ┌──────────────┐  ┌────────────┐
                   │  Registry  │  │  Installer   │  │   Config   │
                   │  (JSON)    │  │ npm/pip/etc  │  │  Manager   │
                   └────────────┘  └──────────────┘  └─────┬──────┘
                                                           ▼
                                          claude_desktop_config.json
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, uvicorn
- **Frontend** (Phase 2, not yet built): React / Next.js, Tailwind
- **Registry**: Plain JSON file (`registry/mcps.json`)
- **No database** — state lives in `claude_desktop_config.json` and the registry JSON

## Directory Structure

```
backend/
├── main.py                      # FastAPI app, CORS, middleware, lifespan
├── models/mcp.py                # ALL Pydantic schemas (single source of truth)
├── core/config_manager.py       # Read/write claude_desktop_config.json + backups
├── services/
│   ├── registry_service.py      # Load/search/filter registry, lru_cache
│   └── installer_service.py     # Transport-specific install logic (async)
└── routers/
    ├── registry_router.py       # GET /registry/* endpoints
    └── installer_router.py      # POST/DELETE /install/* endpoints
registry/mcps.json               # The MCP catalog — add new MCPs here
```

## Key Concepts

### Transport Types
Every MCP has a `transport` that determines how it's installed:
- `npm` → runs via `npx` on demand (no global install needed for npx type)
- `pip` → `pip install`, runs as Python module
- `uvx` → runs via `uvx` on demand (detected via `install_type`, not `transport`)
- `docker` → `docker pull`, runs as container
- `http` / `sse` → remote URL, NO local install — just registered in config

### Config Templating
MCP entries use `{placeholder}` tokens in their `claude_config` that get replaced with user-provided values at install time. See `config_manager.resolve_template_values()`.

Example:
```json
"claude_config": {
  "command": "python",
  "args": ["-m", "mcp_server_postgres", "{connection_string}"]
}
```
The `{connection_string}` is filled from the user's form input.

### Config Safety
`config_manager.write_config()` ALWAYS creates a timestamped backup before writing, and keeps the last 5 backups. Never bypass this when modifying the config.

## Development Commands

```bash
# Run backend (auto-creates venv, installs deps)
./start.sh

# Or manually
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000

# API docs
open http://localhost:8000/docs

# Validate registry JSON
python -c "import json; json.load(open('registry/mcps.json'))"
```

## Coding Conventions

- **Pydantic v2** — use `model_dump()`, not `.dict()`. All schemas live in `models/mcp.py`.
- **Async everywhere** in `installer_service.py` — subprocess calls use `asyncio.create_subprocess_exec`.
- **Type hints required** — this codebase uses modern Python typing (`list[str]`, `dict[str, Any]`, `X | None`).
- **No secrets in logs** — config values (API keys, connection strings) must never be logged.
- **Cross-platform paths** — always use `pathlib.Path` and `get_claude_config_path()` for OS-specific config location. Never hardcode `~/.config/...`.
- **Keep the registry as the single source of truth** for what MCPs exist; don't hardcode MCP data anywhere else.

## Important Constraints

1. **This serves Claude Desktop, not Claude Web.** Browsers cannot reach `localhost`, so web-based AI clients (claude.ai, Copilot web, Gemini, Grok) cannot use locally-installed MCPs. Remote-URL MCPs (http/sse) are the only ones usable on Claude Web, and even those must be added manually in claude.ai settings (no API to auto-register). This is planned for Phase 3 as a "copy URL + guide" flow, NOT auto-install.

2. **Workflow files require `workflow` scope.** Pushing to `.github/workflows/` via a PAT needs the `workflow` token scope, not just `repo`.

3. **Never uninstall packages on remove** — `uninstall_mcp()` only removes the entry from the config; it intentionally leaves the npm/pip package installed for fast re-install.

## Testing Approach

Tests are not yet written (Phase 1 was scaffolding). When adding tests:
- Use `pytest` + `pytest-asyncio` for async services
- Mock `config_manager` filesystem operations — never write to a real `claude_desktop_config.json` in tests
- Use FastAPI `TestClient` for endpoint tests
- The CI workflow (`.github/workflows/ci.yml`) already runs `ruff` + registry validation

## Current Status

**Phase 1 (Backend core) — COMPLETE.** See `docs/ROADMAP.md` for what's next. The immediate next milestone is **Phase 2: Frontend UI**.
