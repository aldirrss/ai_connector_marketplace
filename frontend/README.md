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
│   └── Toast.tsx         # Feedback + "restart Claude Desktop" reminder
└── lib/
    ├── types.ts          # TS mirror of backend/models/mcp.py
    ├── api.ts            # Typed fetch client for the backend
    └── labels.ts         # Transport/category display helpers
```

## API contracts

`lib/types.ts` mirrors `backend/models/mcp.py`. If you change the Pydantic
models, update the TS types to match.
