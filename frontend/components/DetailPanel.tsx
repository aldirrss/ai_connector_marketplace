"use client";

import { useEffect, useState } from "react";
import type { MCPWithStatus } from "@/lib/types";
import { TransportBadge } from "./TransportBadge";
import { InstallForm } from "./InstallForm";
import { categoryLabel } from "@/lib/labels";

function InstallCommandPreview({ mcp }: { mcp: MCPWithStatus }) {
  const cmd =
    mcp.install_cmd ||
    (mcp.claude_config.command
      ? [mcp.claude_config.command, ...(mcp.claude_config.args ?? [])].join(" ")
      : mcp.claude_config.url) ||
    "—";
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Install command
      </p>
      <pre className="scroll-thin overflow-x-auto rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-100">
        <code>{cmd}</code>
      </pre>
    </div>
  );
}

export function DetailPanel({
  mcp,
  installing,
  uninstalling,
  onClose,
  onInstall,
  onUninstall,
}: {
  mcp: MCPWithStatus | null;
  installing: boolean;
  uninstalling: boolean;
  onClose: () => void;
  onInstall: (values: Record<string, string>) => void;
  onUninstall: () => void;
}) {
  const [showForm, setShowForm] = useState(false);

  // Reset the form view whenever the selected MCP changes.
  useEffect(() => {
    setShowForm(false);
  }, [mcp?.id]);

  const open = mcp !== null;
  const hasConfig = mcp ? Object.keys(mcp.config_schema).length > 0 : false;
  const isRemote = mcp?.transport === "http" || mcp?.transport === "sse";

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-30 bg-slate-900/30 transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden
      />

      {/* Slide-out */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={mcp ? `${mcp.name} details` : "Details"}
        className={`scroll-thin fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col overflow-y-auto bg-white shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {mcp && (
          <>
            <div className="flex items-start justify-between gap-3 border-b border-slate-100 p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                  <i className={`ti ${mcp.icon} text-2xl`} aria-hidden />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    {mcp.name}
                  </h2>
                  <p className="text-sm text-slate-500">
                    {mcp.author} · v{mcp.version}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              >
                <i className="ti ti-x text-lg" aria-hidden />
              </button>
            </div>

            <div className="flex-1 space-y-5 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <TransportBadge transport={mcp.transport} />
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {categoryLabel(mcp.category)}
                </span>
                {mcp.official && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                    <i className="ti ti-rosette-discount-check-filled" aria-hidden />
                    Official
                  </span>
                )}
                {mcp.is_installed && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                    <i className="ti ti-circle-check" aria-hidden />
                    Installed
                  </span>
                )}
              </div>

              <p className="whitespace-pre-line text-sm leading-relaxed text-slate-600">
                {mcp.long_description || mcp.description}
              </p>

              {mcp.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {mcp.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              {mcp.homepage && (
                <a
                  href={mcp.homepage}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700"
                >
                  <i className="ti ti-external-link" aria-hidden />
                  Homepage
                </a>
              )}

              <InstallCommandPreview mcp={mcp} />

              {isRemote && (
                <p className="flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
                  <i className="ti ti-info-circle mt-0.5" aria-hidden />
                  This is a remote MCP — no local install runs; it&apos;s just
                  registered in your Claude config.
                </p>
              )}

              {showForm && hasConfig && !mcp.is_installed && (
                <div className="rounded-xl border border-slate-200 p-4">
                  <p className="mb-3 text-sm font-medium text-slate-700">
                    Configure {mcp.name}
                  </p>
                  <InstallForm
                    schema={mcp.config_schema}
                    installing={installing}
                    onSubmit={onInstall}
                    onCancel={() => setShowForm(false)}
                  />
                </div>
              )}
            </div>

            {/* Sticky action bar */}
            <div className="sticky bottom-0 border-t border-slate-100 bg-white p-4">
              {mcp.is_installed ? (
                <button
                  type="button"
                  onClick={onUninstall}
                  disabled={uninstalling}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
                >
                  {uninstalling ? (
                    <i className="ti ti-loader-2 animate-spin" aria-hidden />
                  ) : (
                    <i className="ti ti-trash" aria-hidden />
                  )}
                  {uninstalling ? "Removing…" : "Uninstall"}
                </button>
              ) : showForm && hasConfig ? null : (
                <button
                  type="button"
                  onClick={() => {
                    if (hasConfig) setShowForm(true);
                    else onInstall({});
                  }}
                  disabled={installing}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
                >
                  {installing ? (
                    <i className="ti ti-loader-2 animate-spin" aria-hidden />
                  ) : (
                    <i className="ti ti-download" aria-hidden />
                  )}
                  {installing
                    ? "Installing…"
                    : hasConfig
                      ? "Configure & Install"
                      : "Install"}
                </button>
              )}
            </div>
          </>
        )}
      </aside>
    </>
  );
}
