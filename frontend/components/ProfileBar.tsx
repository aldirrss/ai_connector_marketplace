"use client";

import type { Profile } from "@/lib/types";

// Horizontal strip of one-click install bundles (Phase 4).
export function ProfileBar({
  profiles,
  installingId,
  onInstall,
}: {
  profiles: Profile[];
  installingId: string | null;
  onInstall: (profile: Profile) => void;
}) {
  if (profiles.length === 0) return null;

  return (
    <section>
      <div className="mb-2 flex items-center gap-2">
        <i className="ti ti-stack-2 text-slate-500" aria-hidden />
        <h2 className="text-sm font-semibold text-slate-700">Quick-install profiles</h2>
        <span className="text-xs text-slate-400">install a curated bundle at once</span>
      </div>
      <div className="scroll-thin flex gap-3 overflow-x-auto pb-1">
        {profiles.map((p) => {
          const busy = installingId === p.id;
          return (
            <div
              key={p.id}
              className="flex w-64 shrink-0 flex-col rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
            >
              <div className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <i className={`ti ${p.icon}`} aria-hidden />
                </span>
                <p className="font-medium text-slate-900">{p.name}</p>
              </div>
              <p className="mt-2 line-clamp-2 flex-1 text-xs text-slate-500">
                {p.description}
              </p>
              <p className="mt-2 text-xs text-slate-400">
                {p.mcp_ids.length} MCP{p.mcp_ids.length === 1 ? "" : "s"}
              </p>
              <button
                type="button"
                onClick={() => onInstall(p)}
                disabled={busy}
                className="mt-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
              >
                {busy ? (
                  <i className="ti ti-loader-2 animate-spin" aria-hidden />
                ) : (
                  <i className="ti ti-download" aria-hidden />
                )}
                {busy ? "Installing…" : "Install bundle"}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
