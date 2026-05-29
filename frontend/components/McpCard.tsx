import type { MCPWithStatus } from "@/lib/types";
import { TransportBadge } from "./TransportBadge";

export function McpCard({
  mcp,
  selected,
  onClick,
}: {
  mcp: MCPWithStatus;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group flex h-full flex-col rounded-xl border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-brand-500 ${
        selected ? "border-brand-500 ring-1 ring-brand-500" : "border-slate-200"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <i className={`ti ${mcp.icon} text-xl`} aria-hidden />
          </span>
          <div className="min-w-0">
            <h3 className="truncate font-semibold text-slate-900">{mcp.name}</h3>
            <p className="truncate text-xs text-slate-500">{mcp.author}</p>
          </div>
        </div>
        {mcp.is_installed && (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
            <i className="ti ti-circle-check" aria-hidden /> Installed
          </span>
        )}
      </div>

      <p className="mt-3 line-clamp-2 flex-1 text-sm text-slate-600">
        {mcp.description}
      </p>

      <div className="mt-4 flex items-center justify-between">
        <TransportBadge transport={mcp.transport} />
        <div className="flex items-center gap-3 text-xs text-slate-500">
          {mcp.official && (
            <span className="inline-flex items-center gap-1 text-brand-600">
              <i className="ti ti-rosette-discount-check-filled" aria-hidden />
              Official
            </span>
          )}
          {mcp.stars > 0 && (
            <span className="inline-flex items-center gap-1">
              <i className="ti ti-star-filled text-amber-400" aria-hidden />
              {mcp.stars.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
