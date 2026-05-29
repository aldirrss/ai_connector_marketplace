"use client";

import type { TransportType, RegistryStats } from "@/lib/types";
import { TRANSPORTS, TRANSPORT_LABEL, categoryLabel } from "@/lib/labels";

export interface Filters {
  transport: TransportType | null;
  category: string | null;
  installedOnly: boolean;
  webOnly: boolean;
}

export const EMPTY_FILTERS: Filters = {
  transport: null,
  category: null,
  installedOnly: false,
  webOnly: false,
};

function NavItem({
  active,
  onClick,
  icon,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
  count?: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition ${
        active
          ? "bg-brand-50 font-medium text-brand-700"
          : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      <span className="flex items-center gap-2.5">
        <i className={`ti ${icon} text-base`} aria-hidden />
        {label}
      </span>
      {count !== undefined && (
        <span className="text-xs text-slate-400">{count}</span>
      )}
    </button>
  );
}

export function Sidebar({
  filters,
  onChange,
  categories,
  stats,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  categories: string[];
  stats?: RegistryStats;
}) {
  const noFilter =
    !filters.transport &&
    !filters.category &&
    !filters.installedOnly &&
    !filters.webOnly;

  return (
    <nav className="scroll-thin flex h-full w-60 shrink-0 flex-col gap-6 overflow-y-auto border-r border-slate-200 bg-white px-3 py-5">
      <div>
        <div className="flex items-center gap-2 px-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
            <i className="ti ti-building-store" aria-hidden />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-slate-900">Connector</p>
            <p className="text-xs text-slate-400">Marketplace</p>
          </div>
        </div>
      </div>

      <div className="space-y-1">
        <NavItem
          active={noFilter}
          onClick={() => onChange({ ...EMPTY_FILTERS })}
          icon="ti-apps"
          label="All MCPs"
          count={stats?.total}
        />
        <NavItem
          active={filters.installedOnly}
          onClick={() => onChange({ ...EMPTY_FILTERS, installedOnly: true })}
          icon="ti-circle-check"
          label="Installed"
          count={stats?.installed}
        />
        <NavItem
          active={filters.webOnly}
          onClick={() => onChange({ ...EMPTY_FILTERS, webOnly: true })}
          icon="ti-world"
          label="Works on Claude Web"
          count={stats?.web_compatible}
        />
      </div>

      <div>
        <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Transport
        </p>
        <div className="space-y-1">
          {TRANSPORTS.map((t) => (
            <NavItem
              key={t}
              active={filters.transport === t}
              onClick={() =>
                onChange({
                  ...EMPTY_FILTERS,
                  transport: filters.transport === t ? null : t,
                })
              }
              icon="ti-plug-connected"
              label={TRANSPORT_LABEL[t]}
              count={stats?.by_transport?.[t]}
            />
          ))}
        </div>
      </div>

      {categories.length > 0 && (
        <div>
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Category
          </p>
          <div className="space-y-1">
            {categories.map((c) => (
              <NavItem
                key={c}
                active={filters.category === c}
                onClick={() =>
                  onChange({
                    ...EMPTY_FILTERS,
                    category: filters.category === c ? null : c,
                  })
                }
                icon="ti-category"
                label={categoryLabel(c)}
                count={stats?.by_category?.[c]}
              />
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}
