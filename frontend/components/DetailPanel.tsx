"use client";

import { useEffect, useState } from "react";
import type { MCPWithStatus, DockerHealth, UpdateInfo } from "@/lib/types";
import { api } from "@/lib/api";
import { TransportBadge } from "./TransportBadge";
import { InstallForm } from "./InstallForm";
import { PlatformBadges } from "./PlatformBadges";
import { ClaudeWebGuide } from "./ClaudeWebGuide";
import { InstallLog } from "./InstallLog";
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
  savingConfig,
  installLog,
  dockerHealth,
  updateInfo,
  onClose,
  onInstall,
  onUninstall,
  onSaveConfig,
}: {
  mcp: MCPWithStatus | null;
  installing: boolean;
  uninstalling: boolean;
  savingConfig: boolean;
  installLog: string[];
  dockerHealth?: DockerHealth;
  updateInfo?: UpdateInfo;
  onClose: () => void;
  onInstall: (values: Record<string, string>) => void;
  onUninstall: () => void;
  onSaveConfig: (values: Record<string, string>) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [editLoading, setEditLoading] = useState(false);

  // Reset transient views whenever the selected MCP changes.
  useEffect(() => {
    setShowForm(false);
    setEditMode(false);
    setEditValues({});
  }, [mcp?.id]);

  async function openEditor() {
    if (!mcp) return;
    setEditLoading(true);
    try {
      const cfg = await api.getConfig(mcp.id);
      setEditValues(cfg.current_values);
    } catch {
      setEditValues({});
    } finally {
      setEditLoading(false);
      setEditMode(true);
    }
  }

  const open = mcp !== null;
  const hasConfig = mcp ? Object.keys(mcp.config_schema).length > 0 : false;
  const isRemote = mcp?.transport === "http" || mcp?.transport === "sse";
  const webUrl = mcp?.claude_config.url ?? "";
  const showWebGuide = !!mcp?.claude_web_compatible && !!webUrl;
  // Block install only for docker transports when the daemon is known to be down.
  const dockerBlocked =
    mcp?.transport === "docker" &&
    dockerHealth !== undefined &&
    !dockerHealth.daemon_running;

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

              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Compatible with
                </p>
                <PlatformBadges platforms={mcp.platforms} size="md" />
              </div>

              {mcp.is_installed && updateInfo && updateInfo.installed_version && (
                <p
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${
                    updateInfo.update_available
                      ? "bg-amber-50 text-amber-800"
                      : "bg-slate-50 text-slate-500"
                  }`}
                >
                  <i
                    className={`ti ${updateInfo.update_available ? "ti-arrow-up-circle" : "ti-circle-check"}`}
                    aria-hidden
                  />
                  {updateInfo.update_available ? (
                    <span>
                      Update available: {updateInfo.installed_version} →{" "}
                      <span className="font-semibold">{updateInfo.latest_version}</span>
                    </span>
                  ) : (
                    <span>Up to date (v{updateInfo.installed_version})</span>
                  )}
                </p>
              )}

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

              {showWebGuide && <ClaudeWebGuide url={webUrl} />}

              {dockerBlocked && (
                <p className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  <i className="ti ti-alert-triangle mt-0.5" aria-hidden />
                  {dockerHealth?.message ??
                    "Docker daemon is not running. Start Docker Desktop to install."}
                </p>
              )}

              <InstallLog lines={installLog} />

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

              {editMode && hasConfig && mcp.is_installed && (
                <div className="rounded-xl border border-slate-200 p-4">
                  <p className="mb-3 text-sm font-medium text-slate-700">
                    Edit {mcp.name} config
                  </p>
                  <InstallForm
                    schema={mcp.config_schema}
                    installing={savingConfig}
                    initialValues={editValues}
                    submitLabel="Save changes"
                    busyLabel="Saving…"
                    onSubmit={onSaveConfig}
                    onCancel={() => setEditMode(false)}
                  />
                </div>
              )}
            </div>

            {/* Sticky action bar */}
            <div className="sticky bottom-0 border-t border-slate-100 bg-white p-4">
              {mcp.is_installed ? (
                <div className="flex gap-2">
                  {hasConfig && (
                    <button
                      type="button"
                      onClick={openEditor}
                      disabled={editLoading || editMode}
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                    >
                      {editLoading ? (
                        <i className="ti ti-loader-2 animate-spin" aria-hidden />
                      ) : (
                        <i className="ti ti-settings" aria-hidden />
                      )}
                      Edit config
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={onUninstall}
                    disabled={uninstalling}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
                  >
                    {uninstalling ? (
                      <i className="ti ti-loader-2 animate-spin" aria-hidden />
                    ) : (
                      <i className="ti ti-trash" aria-hidden />
                    )}
                    {uninstalling ? "Removing…" : "Uninstall"}
                  </button>
                </div>
              ) : showForm && hasConfig ? null : (
                <button
                  type="button"
                  onClick={() => {
                    if (hasConfig) setShowForm(true);
                    else onInstall({});
                  }}
                  disabled={installing || dockerBlocked}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {installing ? (
                    <i className="ti ti-loader-2 animate-spin" aria-hidden />
                  ) : (
                    <i className="ti ti-download" aria-hidden />
                  )}
                  {installing
                    ? "Installing…"
                    : dockerBlocked
                      ? "Docker daemon offline"
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
