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

## Phase 3 — Remote MCPs & Claude Web Support

Extend beyond Claude Desktop to web-based clients.

- [ ] Add `claude_web_compatible` and `platforms` fields to registry schema
- [ ] **"Use on Claude Web" flow** — for http/sse MCPs, show the URL + a copy button + step-by-step guide (claude.ai → Settings → Integrations → paste URL). No auto-install (no API exists for this).
- [ ] Per-platform compatibility badges on cards (Desktop / Web / Copilot / Gemini)
- [ ] Filter: "works on Claude Web"
- [ ] Real-time install log streaming (WebSocket or SSE) so users see npm/pip output live
- [ ] Docker daemon health check before docker-transport installs (partially stubbed already)

---

## Phase 4 — Power Features

- [ ] **One-click profiles** — bundles that install multiple MCPs at once (e.g. "Odoo Dev Stack" = PostgreSQL + Filesystem + GitHub). Define profiles in `registry/profiles.json`.
- [ ] **Community registry sync** — pull the registry from a remote GitHub-hosted JSON so new MCPs appear without app updates; allow PRs to add MCPs.
- [ ] **Update checker** — compare installed package versions against latest; surface "update available".
- [ ] **Config editor** — let users edit an installed MCP's config values without uninstall/reinstall.
- [ ] **Multi-platform guides** — "How to use this MCP on Copilot / Gemini" pages.

---

## Phase 5 — Packaging & Distribution

- [ ] Bundle backend + frontend into a single desktop app via **Tauri** (preferred — small binary) or Electron
- [ ] System tray icon, auto-start option
- [ ] Cross-platform installers (.dmg, .exe, .AppImage)
- [ ] Auto-update mechanism
- [ ] Code signing for macOS/Windows

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
