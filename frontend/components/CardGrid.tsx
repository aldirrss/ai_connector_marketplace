"use client";

import type { MCPWithStatus } from "@/lib/types";
import { McpCard } from "./McpCard";

export function CardGrid({
  mcps,
  loading,
  error,
  selectedId,
  updateIds,
  onSelect,
}: {
  mcps: MCPWithStatus[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  updateIds: Set<string>;
  onSelect: (mcp: MCPWithStatus) => void;
}) {
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-center">
        <i className="ti ti-plug-connected-x text-4xl text-rose-400" aria-hidden />
        <p className="font-medium text-slate-700">Couldn&apos;t load the registry</p>
        <p className="max-w-sm text-sm text-slate-500">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-40 animate-pulse rounded-xl border border-slate-200 bg-white"
          />
        ))}
      </div>
    );
  }

  if (mcps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-center">
        <i className="ti ti-search-off text-4xl text-slate-300" aria-hidden />
        <p className="font-medium text-slate-700">No MCPs match your filters</p>
        <p className="text-sm text-slate-500">Try clearing the search or filters.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {mcps.map((mcp) => (
        <McpCard
          key={mcp.id}
          mcp={mcp}
          selected={mcp.id === selectedId}
          updateAvailable={updateIds.has(mcp.id)}
          onClick={() => onSelect(mcp)}
        />
      ))}
    </div>
  );
}
