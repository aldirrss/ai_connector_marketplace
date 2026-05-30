# Roadmap

This document tracks the development phases of AI Connector Marketplace. Each phase is self-contained and leaves the project in a runnable state.

---

## Phase 1 — Backend Core ✅ COMPLETE

The foundation: a FastAPI backend that can read the MCP registry, install MCPs via multiple transports, and manage the Claude Desktop config file.

- [x] Registry JSON schema with 12 seed MCPs (npm, pip, uvx, docker, http, sse)
- [x] Pydantic v2 models (`models/mcp.py`)
- [x] `config_manager.py` — read/write `claude_desktop_config.json` with auto-backup and template resolution
- [x] `registry_service.py` — load, search, filter, stats (with `lru_cache`)
- [x] `installer_service.py` — async install handlers per transport, dependency checks
- [x] `registry_router.py` — `GET /registry/*` (list, search, stats, categories, config-info)
- [x] `installer_router.py` — `POST /install`, `DELETE /install/{id}`, status, dependency check
- [x] `main.py` — app wiring, CORS, request logging, global error handler, health endpoint
- [x] `start.sh` — one-command venv + uvicorn launch
- [x] GitHub Actions CI (ruff + registry validation)
- [x] README + CLAUDE.md

---

## Phase 2 — Frontend UI ✅ COMPLETE

A web interface so users never touch the API directly. Built in `frontend/` with
Next.js (App Router) + Tailwind + TanStack Query. See `frontend/README.md`.

### Goals
- [x] Scaffold Next.js (App Router) + Tailwind in a `frontend/` directory
- [x] **Marketplace grid** — card per MCP, showing icon, name, transport badge, official/stars, install status
- [x] **Sidebar navigation** — filter by transport (npm/pip/http/sse/docker), category, and "Installed"
- [x] **Search bar** — live filter wired to `GET /registry/?q=`
- [x] **Detail panel** — slide-out on card click: long description, homepage link, transport, install command preview
- [x] **Install flow**:
  - MCPs with empty `config_schema` → one-click install
  - MCPs with `config_schema` → render a dynamic form (text/secret fields), then install
  - Secret fields use password inputs; never persisted client-side
- [x] **Status indicators** — installed cards show green badge; poll `GET /install/installed/all`
- [x] **Uninstall** — remove button on installed cards → `DELETE /install/{id}`
- [x] **Dependency banner** — call `GET /install/dependencies/check` on load; warn if npm/pip/docker missing
- [x] **Restart reminder** — after install/uninstall, show "Restart Claude Desktop to apply"

### Design reference
A mockup was created during planning — a 3-pane layout (sidebar / card grid / detail panel) styled like a polished app store. Match that direction: clean, minimal, generous whitespace.

### Technical notes
- Backend already has CORS configured for `localhost:3000`
- All API contracts are in `models/mcp.py` — generate TS types from these to stay in sync
- Consider TanStack Query for server state + polling install status

---

## Phase 3 — Remote MCPs & Claude Web Support ✅ COMPLETE

Extend beyond Claude Desktop to web-based clients.

- [x] Add `claude_web_compatible` and `platforms` fields to registry schema
- [x] **"Use on Claude Web" flow** — for http/sse MCPs, show the URL + a copy button + step-by-step guide (claude.ai → Settings → Integrations → paste URL). No auto-install (no API exists for this).
- [x] Per-platform compatibility badges on cards (Desktop / Web / Copilot / Gemini)
- [x] Filter: "works on Claude Web"
- [x] Real-time install log streaming via SSE (`POST /install/stream`) so users see npm/pip/docker output live
- [x] Docker daemon health check (`GET /install/docker/health`) gates docker-transport installs

### Backend additions
- `RegistryStats.web_compatible` count; `web_only` filter on `GET /registry/`
- `POST /install/stream` — Server-Sent Events with `{type:"log"|"done", …}` frames
- `GET /install/docker/health` → `{installed, daemon_running, message}`

---

## Phase 4 — Power Features ✅ MOSTLY COMPLETE

- [x] **One-click profiles** — bundles that install multiple MCPs at once (e.g. "Odoo Dev Stack" = PostgreSQL + Filesystem + GitHub). Defined in `registry/profiles.json`; served at `GET /registry/profiles`, installed via `POST /install/profile/{id}` (config-free members install; ones needing config are reported for individual setup).
- [x] **Community registry sync** — pull the registry from a remote JSON (`MARKETPLACE_REGISTRY_URL`) via `POST /registry/sync`; status at `GET /registry/sync/info`. `POST /registry/reload` reverts to the bundled catalog.
- [x] **Update checker** — `GET /install/updates/check` compares installed npm/pip package versions against the latest published on the npm registry / PyPI; surfaces "update available" badges.
- [x] **Config editor** — `GET /install/config/{id}` (with best-effort value decoding) + `PUT /install/config/{id}` let users edit an installed MCP's config values without uninstall/reinstall.
- [ ] **Multi-platform guides** — "How to use this MCP on Copilot / Gemini" pages. *(deferred)*

---

## Phase 5 — Packaging & Distribution 🚧 SCAFFOLDED

Tauri v2 desktop shell in `src-tauri/`. See [`docs/PACKAGING.md`](PACKAGING.md).

- [x] Bundle backend + frontend into a single desktop app via **Tauri** — window
      serves the static frontend export and launches the FastAPI backend as a
      child process (`backend/` + `registry/` bundled as resources)
- [x] System tray icon (Show / Quit) and clean backend shutdown on exit
- [x] Cross-platform installer config (`bundle.targets: "all"` → .dmg / .msi+.exe / .AppImage+.deb+.rpm) and `tauri:dev` / `tauri:build` / `icon` scripts
- [ ] Auto-update mechanism — needs `tauri-plugin-updater` + a signed release feed *(documented, not wired)*
- [ ] Code signing for macOS/Windows — needs maintainer certificates/secrets *(documented)*

> The GUI binary build was not run in the dev sandbox (no WebKit/system deps).
> The web export, Tauri configs, icons, and Rust source are in place; building
> installers requires the per-OS prerequisites in `docs/PACKAGING.md`.

---

## Phase 6 — Claude Code Support 📋 PLANNED

Extend the marketplace beyond Claude Desktop to also manage MCP servers for
**Claude Code (CLI)**. Critical for Linux users (where Claude Desktop is not
officially distributed) and for developers who run both clients.

### Background
- Claude Desktop config lives at OS-specific paths handled by
  `core/config_manager.get_claude_config_path()`.
- Claude Code stores user-scope config at `~/.claude.json` and supports
  project-scope MCPs via `.mcp.json` in a repo root. The `~/.claude.json` file
  also contains many non-MCP fields (`projects`, `theme`, telemetry, etc.) that
  must be preserved on every write.

### Goals
- [ ] **Target switcher in UI** — pick Claude Desktop, Claude Code (user),
      or Claude Code (project) as the active install target. Persist last choice.
- [ ] **Multi-target config manager** — refactor `config_manager` so read/write
      ops accept a `target` enum. Each target implements its own:
      - path resolution
      - safe merge (preserve sibling keys in `~/.claude.json`)
      - backup strategy (don't bloat backups for the huge `~/.claude.json`)
- [ ] **Project-scope `.mcp.json`** — detect when the backend is launched from
      within a repo, surface "Install to this project" as a target.
- [ ] **Schema differences** — verify each registry entry's `claude_config`
      template is valid for both clients; add per-target overrides in the
      registry if a server needs different invocation between Desktop and Code.
- [ ] **Status detection** — extend `get_installed_mcp_keys()` to merge across
      targets; mark each installed MCP with where it lives (badge: "Desktop",
      "Code", "Project").
- [ ] **Cross-target operations** — "copy MCP from Desktop → Code", "move from
      user → project scope", etc.
- [ ] **Restart guidance** — Claude Code picks up MCP changes on next session
      start (not a process restart like Desktop). Update post-install hints
      per target.

### Non-goals for this phase
- Auto-detecting which Claude Code project is "active" beyond the backend's
  current working directory.
- Editing Claude Code's non-MCP settings.

---

## Non-Goals (Explicitly Out of Scope)

- **Not a hosted SaaS.** This is a local tool. There is no cloud account, no multi-tenancy.
- **Not an MCP server registry authority.** We mirror/catalog existing MCPs; we don't host or vet them.
- **No auto-registration for Claude Web.** No public API exists for programmatically adding MCPs to claude.ai — best we can do is guide the user.

---

## Design Principles

1. **The user should never need to know MCP internals** — browse, click install, fill a form if needed, restart. That's it.
2. **The registry is the single source of truth** for what MCPs exist.
3. **Config writes are always backed up** — never risk corrupting a user's Claude config.
4. **Fail loudly and helpfully** — if `npm` is missing, say "Install Node.js from nodejs.org", not a raw stack trace.
5. **Local-first, privacy-first** — secrets go straight into the local config, never to any server or database.
