import type { TransportType } from "./types";

export const TRANSPORTS: TransportType[] = ["npm", "pip", "http", "sse", "docker"];

// Tailwind classes per transport badge (text + background).
export const TRANSPORT_STYLE: Record<TransportType, string> = {
  npm: "bg-rose-100 text-rose-700",
  pip: "bg-blue-100 text-blue-700",
  http: "bg-emerald-100 text-emerald-700",
  sse: "bg-amber-100 text-amber-700",
  docker: "bg-sky-100 text-sky-700",
};

export const TRANSPORT_LABEL: Record<TransportType, string> = {
  npm: "npm",
  pip: "pip",
  http: "HTTP",
  sse: "SSE",
  docker: "Docker",
};

// Human-friendly category names. Falls back to title-casing the raw slug.
const CATEGORY_LABELS: Record<string, string> = {
  dev_tools: "Dev Tools",
  database: "Database",
  ai_search: "AI & Search",
  communication: "Communication",
};

export function categoryLabel(slug: string): string {
  return (
    CATEGORY_LABELS[slug] ??
    slug
      .split(/[_\s-]+/)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  );
}

// Tools required per transport, used by the dependency banner.
export const TRANSPORT_TOOL: Record<TransportType, string | null> = {
  npm: "npx",
  pip: "pip",
  http: null,
  sse: null,
  docker: "docker",
};

// Known AI client platforms, shown as compatibility badges (Phase 3).
export interface PlatformMeta {
  key: string;
  label: string;
  icon: string;
}

export const PLATFORMS: PlatformMeta[] = [
  { key: "desktop", label: "Desktop", icon: "ti-device-desktop" },
  { key: "web", label: "Web", icon: "ti-world" },
  { key: "copilot", label: "Copilot", icon: "ti-brand-github-copilot" },
  { key: "gemini", label: "Gemini", icon: "ti-sparkles" },
];
