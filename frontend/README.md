# Frontend — AI Connector Marketplace (Phase 2)

A Next.js (App Router) + Tailwind web UI for browsing and installing MCP servers
for Claude Desktop. It talks to the FastAPI backend (Phase 1) over HTTP.

## Stack

- **Next.js 15** (App Router, client-rendered — the backend is localhost-only)
- **Tailwind CSS 3** for styling
- **TanStack Query** for server state, polling, and mutations
- **Tabler Icons** (webfont) for the `icon` field on each registry entry

## Prerequisites

The backend must be running on `http://localhost:8000`:

```bash
# from the repo root
./start.sh
```

## Develop

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

The backend already allows CORS from `localhost:3000`.

## Configuration

The API base URL defaults to `http://localhost:8000`. Override it via
`frontend/.env.local`:

```bash
cp .env.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Scripts

| Script              | Purpose                          |
| ------------------- | -------------------------------- |
| `npm run dev`       | Dev server with hot reload       |
| `npm run build`     | Production build                 |
| `npm run start`     | Serve the production build       |
| `npm run typecheck` | `tsc --noEmit` type checking     |

## Structure

```
frontend/
├── app/
│   ├── layout.tsx        # Root layout + <Providers>
│   ├── providers.tsx     # TanStack Query client
│   ├── page.tsx          # 3-pane orchestrator (state, queries, mutations)
│   └── globals.css       # Tailwind + Tabler webfont
├── components/
│   ├── Sidebar.tsx       # Transport / category / Installed filters
│   ├── SearchBar.tsx     # Debounced live search
│   ├── CardGrid.tsx      # Grid + loading / empty / error states
│   ├── McpCard.tsx       # Single MCP card
│   ├── DetailPanel.tsx   # Slide-out detail + install/uninstall actions
│   ├── InstallForm.tsx   # Dynamic config form (text/secret fields)
│   ├── DependencyBanner.tsx
│   ├── TransportBadge.tsx
│   ├── PlatformBadges.tsx # Desktop / Web / Copilot / Gemini compatibility
│   ├── ClaudeWebGuide.tsx # "Use on Claude Web" copy-URL + manual guide
│   ├── InstallLog.tsx    # Live console for streamed install output
│   ├── ProfileBar.tsx    # One-click install bundles (Phase 4)
│   └── Toast.tsx         # Feedback + "restart Claude Desktop" reminder
└── lib/
    ├── types.ts          # TS mirror of backend/models/mcp.py
    ├── api.ts            # Typed fetch client (incl. SSE install stream)
    └── labels.ts         # Transport/category/platform display helpers
```

## Phase 3 — Remote MCPs & Claude Web

- **Platform badges** on every card and in the detail panel (Desktop / Web / Copilot / Gemini).
- **"Works on Claude Web" filter** in the sidebar (`web_only` query param).
- **"Use on Claude Web"** section for remote (http/sse) MCPs — shows the URL, a
  copy button, and a step-by-step manual guide (no auto-registration API exists).
- **Live install logs** — installs stream via `POST /install/stream` (SSE) and
  render in a console in the detail panel.
- **Docker daemon gate** — docker-transport installs are disabled with a warning
  when `GET /install/docker/health` reports the daemon is offline.

## Phase 4 — Power Features

- **Quick-install profiles** — a strip of curated bundles (`GET /registry/profiles`)
  installed in one click via `POST /install/profile/{id}`.
- **Update badges** — `GET /install/updates/check` flags installed MCPs with a newer
  published version; the detail panel shows `installed → latest`.
- **Config editor** — installed MCPs with a config schema get an "Edit config" button
  that loads current values (`GET /install/config/{id}`) and re-applies them
  (`PUT /install/config/{id}`) without reinstalling.
- **Sync** button in the header pulls a remote community registry
  (`POST /registry/sync`, needs `MARKETPLACE_REGISTRY_URL` on the backend).

## API contracts

`lib/types.ts` mirrors `backend/models/mcp.py`. If you change the Pydantic
models, update the TS types to match.
