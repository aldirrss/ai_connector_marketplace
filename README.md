# AI Connector Marketplace

> **Local MCP Manager** — browse, install, and configure [MCP servers](https://modelcontextprotocol.io) for Claude Desktop from a single web interface. No more manual JSON editing.

---

## What is this?

MCP (Model Context Protocol) lets Claude connect to external tools and services — databases, GitHub, Slack, filesystems, and more. Installing them today requires manually editing `claude_desktop_config.json`. This project automates that.

**AI Connector Marketplace** is a local web app that acts as an "app store" for MCP servers:

- 🔍 Browse a registry of MCP servers
- ⚡ One-click install via npm, pip, uvx, docker, or HTTP/SSE URL
- ⚙️  Auto-fills `claude_desktop_config.json` — no manual editing
- 🔑 Secure config forms for API keys and connection strings

---

## Project Structure

```
ai_connector_marketplace/
├── backend/                    ← FastAPI backend
│   ├── main.py                 ← App entrypoint & middleware
│   ├── routers/
│   │   ├── registry_router.py  ← GET /registry (list, search, stats)
│   │   └── installer_router.py ← POST /install, DELETE /install/{id}
│   ├── services/
│   │   ├── registry_service.py ← Registry loader & search logic
│   │   └── installer_service.py← npm/pip/docker/url install handlers
│   ├── core/
│   │   └── config_manager.py   ← Read/write claude_desktop_config.json
│   ├── models/
│   │   └── mcp.py              ← Pydantic schemas
│   └── requirements.txt
├── frontend/                   ← Next.js + Tailwind web UI (see frontend/README.md)
│   ├── app/                    ← App Router pages + providers
│   ├── components/             ← Cards, sidebar, detail panel, install log, etc.
│   └── lib/                    ← Typed API client + types mirroring backend models
├── registry/
│   ├── mcps.json               ← MCP catalog (add new entries here)
│   └── profiles.json           ← One-click install bundles (Phase 4)
├── docs/                       ← Design docs and plans
├── .github/
│   ├── workflows/ci.yml        ← GitHub Actions CI
│   └── ISSUE_TEMPLATE/
├── start.sh                    ← One-command startup
└── README.md
```

---

## Quickstart

### Prerequisites

- Python 3.11+
- (Optional) Node.js 18+ for npm-based MCPs
- (Optional) Docker for docker-based MCPs

### Run the backend

```bash
git clone https://github.com/aldirrss/ai_connector_marketplace
cd ai_connector_marketplace
./start.sh
```

Backend starts at **http://localhost:8000**
API docs at **http://localhost:8000/docs**

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

UI starts at **http://localhost:3000** (talks to the backend on :8000). See
[`frontend/README.md`](frontend/README.md) for details.

---

## API Reference

### Registry

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/registry/` | List all MCPs (with filters) |
| `GET` | `/registry/{id}` | Get single MCP with status |
| `GET` | `/registry/stats` | Registry statistics |
| `GET` | `/registry/categories` | All categories |
| `GET` | `/registry/config-info` | Claude Desktop config path |
| `GET` | `/registry/profiles` | One-click install bundles |
| `GET` | `/registry/profiles/{id}` | A single profile |
| `POST` | `/registry/sync` | Sync registry from a remote URL (`?url=` or `MARKETPLACE_REGISTRY_URL`) |
| `GET` | `/registry/sync/info` | Community-sync source + status |

**Query params for `GET /registry/`:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Search name, description, tags |
| `transport` | string | Filter: npm, pip, http, sse, docker |
| `category` | string | Filter by category |
| `official_only` | bool | Official MCPs only |
| `free_only` | bool | Free MCPs only |
| `installed_only` | bool | Installed MCPs only |
| `web_only` | bool | Claude Web-compatible MCPs only |

### Installer

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/install/` | Install an MCP |
| `POST` | `/install/stream` | Install an MCP, streaming live progress (SSE) |
| `DELETE` | `/install/{id}` | Remove MCP from config |
| `GET` | `/install/status/{id}` | Check install status |
| `GET` | `/install/installed/all` | List all installed MCP IDs |
| `GET` | `/install/dependencies/check` | Check npm/pip/docker availability |
| `GET` | `/install/docker/health` | Check Docker install + daemon status |
| `POST` | `/install/profile/{id}` | One-click install a profile bundle |
| `GET` | `/install/updates/check` | Compare installed vs latest package versions |
| `GET` | `/install/config/{id}` | Read an installed MCP's config + decoded values |
| `PUT` | `/install/config/{id}` | Edit an installed MCP's config (no reinstall) |

**`POST /install/stream`** returns `text/event-stream`. Each event's `data:` is a JSON object:

```
data: {"type": "log", "line": "$ npm install -g …"}
data: {"type": "done", "success": true, "message": "…", "mcp_id": "…", "details": "…"}
```

**Install request body:**

```json
{
  "mcp_id": "postgres",
  "config_values": {
    "connection_string": "postgresql://user:pass@localhost/mydb"
  }
}
```

---

## Adding MCPs to the Registry

Edit `registry/mcps.json` and add an entry:

```json
{
  "id": "my-mcp",
  "name": "My Custom MCP",
  "author": "Your Name",
  "version": "1.0.0",
  "description": "Short description",
  "long_description": "Detailed description",
  "transport": "pip",
  "install_type": "pip",
  "package": "my-mcp-package",
  "install_cmd": "pip install my-mcp-package",
  "config_schema": {
    "API_KEY": {
      "type": "secret",
      "label": "API Key",
      "placeholder": "sk-xxxx",
      "required": true,
      "description": "Get your API key at example.com"
    }
  },
  "claude_config": {
    "command": "python",
    "args": ["-m", "my_mcp"],
    "env": { "API_KEY": "{API_KEY}" }
  },
  "tags": ["custom"],
  "category": "dev_tools",
  "stars": 4.0,
  "official": false,
  "free": true,
  "homepage": "https://example.com",
  "icon": "ti-plug",
  "claude_web_compatible": false,
  "platforms": ["desktop"]
}
```

> `claude_web_compatible` and `platforms` are optional (default `false` / `["desktop"]`).
> Set `claude_web_compatible: true` and `platforms: ["desktop", "web"]` for remote
> (http/sse) MCPs that expose a reachable URL — these surface a "Use on Claude Web" guide in the UI.

Then call `POST /registry/reload` to pick up the change without restarting.

---

## Profiles & Community Sync (Phase 4)

**Profiles** are curated bundles installed with one click. Define them in `registry/profiles.json`:

```json
{
  "id": "odoo-dev-stack",
  "name": "Odoo Dev Stack",
  "description": "PostgreSQL + Filesystem + GitHub",
  "icon": "ti-stack-2",
  "mcp_ids": ["postgres", "filesystem", "github"]
}
```

Installing a profile registers all config-free members at once; members that need
configuration are reported so you can install them individually.

**Community sync** lets the catalog come from a remote JSON instead of the bundled file.
Set the source via env var, then hit the **Sync** button (or `POST /registry/sync`):

```bash
export MARKETPLACE_REGISTRY_URL="https://example.com/mcps.json"
```

The remote payload may be a bare JSON list of MCP entries or `{ "mcps": [...] }`.
`POST /registry/reload` reverts to the bundled catalog.

---

## Transport Types

| Transport | How it works | Example |
|-----------|-------------|---------|
| `npm` | Runs via `npx` on demand | `@modelcontextprotocol/server-github` |
| `pip` | Installed globally, runs as Python module | `mcp-server-postgres` |
| `sse` / `http` | Remote URL, no local install | `https://mcp.slack.com/sse` |
| `docker` | Pulls image, runs as container | `mcp-grafana` |

---

## Claude Desktop Config

The backend automatically manages:
```
macOS  : ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%/Claude/claude_desktop_config.json
Linux  : ~/.config/claude/claude_desktop_config.json
```

A timestamped backup is created before every write. The last 5 backups are kept.

---

## Roadmap

### Phase 1 — Backend (this release)
- [x] Registry JSON with 12 MCPs
- [x] FastAPI backend with registry + installer endpoints
- [x] npm, pip, uvx, docker, http/sse install support
- [x] Auto config manager (read/write/backup)
- [x] GitHub Actions CI

### Phase 2 — Frontend ✅
- [x] Next.js (App Router) + Tailwind UI (card grid, search, install button)
- [x] Config forms for API keys (secret-aware)
- [x] Sidebar filters, slide-out detail panel, dependency banner, restart reminder

### Phase 3 — Remote MCPs & Claude Web ✅
- [x] `claude_web_compatible` + `platforms` registry fields
- [x] "Use on Claude Web" copy-URL + guide flow for remote MCPs
- [x] Per-platform compatibility badges + "Works on Claude Web" filter
- [x] Real-time install log streaming via SSE
- [x] Docker daemon health check before docker installs

### Phase 4 — Power Features ✅
- [x] One-click profiles (e.g. "Odoo Dev Stack") — `registry/profiles.json`
- [x] Community registry sync from a remote URL (`MARKETPLACE_REGISTRY_URL`)
- [x] Update checker (npm / PyPI latest vs installed)
- [x] Config editor (edit an installed MCP without reinstall)
- [ ] Multi-platform guides (Copilot / Gemini) — deferred

### Phase 5 — Packaging
- [ ] Tauri desktop app packaging
- [ ] System tray, auto-start, cross-platform installers

---

## License

MIT
