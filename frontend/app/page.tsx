"use client";

import { useEffect, useMemo, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { MCPWithStatus, InstallStreamEvent } from "@/lib/types";
import { Sidebar, EMPTY_FILTERS, type Filters } from "@/components/Sidebar";
import { SearchBar } from "@/components/SearchBar";
import { CardGrid } from "@/components/CardGrid";
import { DetailPanel } from "@/components/DetailPanel";
import { DependencyBanner } from "@/components/DependencyBanner";
import { Toast, type ToastState } from "@/components/Toast";

export default function HomePage() {
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);

  // Debounce the search box so we don't hit the API on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => clearTimeout(t);
  }, [search]);

  const registryQuery = {
    q: debouncedSearch || undefined,
    transport: filters.transport ?? undefined,
    category: filters.category ?? undefined,
    installed_only: filters.installedOnly || undefined,
    web_only: filters.webOnly || undefined,
  };

  const mcpsQuery = useQuery({
    queryKey: ["mcps", registryQuery],
    queryFn: () => api.listMcps(registryQuery),
  });

  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: api.categories,
  });
  const depsQuery = useQuery({
    queryKey: ["deps"],
    queryFn: api.dependencies,
  });
  const dockerHealthQuery = useQuery({
    queryKey: ["docker-health"],
    queryFn: api.dockerHealth,
    // Daemon state can change while the app is open; re-check periodically.
    refetchInterval: 15000,
  });

  // Poll installed status so cards reflect live state (roadmap: poll installed/all).
  const installedQuery = useQuery({
    queryKey: ["installed"],
    queryFn: api.installedIds,
    refetchInterval: 5000,
  });

  const installedSet = useMemo(
    () => new Set(installedQuery.data ?? []),
    [installedQuery.data],
  );

  // Merge live install status onto the registry results.
  const mcps: MCPWithStatus[] = useMemo(() => {
    const base = mcpsQuery.data ?? [];
    if (!installedQuery.data) return base;
    return base.map((m) => ({ ...m, is_installed: installedSet.has(m.id) }));
  }, [mcpsQuery.data, installedQuery.data, installedSet]);

  const selectedMcp = useMemo(
    () => mcps.find((m) => m.id === selectedId) ?? null,
    [mcps, selectedId],
  );

  function refreshAfterMutation() {
    queryClient.invalidateQueries({ queryKey: ["mcps"] });
    queryClient.invalidateQueries({ queryKey: ["installed"] });
    queryClient.invalidateQueries({ queryKey: ["stats"] });
  }

  // Streaming install state (POST /install/stream). We track which MCP is
  // installing and accumulate its live log output for the detail panel console.
  const [installingId, setInstallingId] = useState<string | null>(null);
  const [installLog, setInstallLog] = useState<string[]>([]);
  const [logOwnerId, setLogOwnerId] = useState<string | null>(null);

  async function runInstall(id: string, values: Record<string, string>) {
    setInstallLog([]);
    setLogOwnerId(id);
    setInstallingId(id);
    const onEvent = (event: InstallStreamEvent) => {
      if (event.type === "log") {
        setInstallLog((prev) => [...prev, event.line]);
      } else {
        refreshAfterMutation();
        setToast({
          kind: event.success ? "restart" : "error",
          message: event.success
            ? `${event.message} — restart Claude Desktop to apply.`
            : event.message,
        });
      }
    };
    try {
      await api.installStream(id, values, onEvent);
    } catch (err) {
      setToast({
        kind: "error",
        message: err instanceof ApiError ? err.message : "Install failed.",
      });
    } finally {
      setInstallingId(null);
    }
  }

  const uninstallMutation = useMutation({
    mutationFn: (id: string) => api.uninstall(id),
    onSuccess: (res) => {
      refreshAfterMutation();
      setToast({
        kind: res.success ? "restart" : "error",
        message: res.success
          ? `${res.message} — restart Claude Desktop to apply.`
          : res.message,
      });
    },
    onError: (err) => {
      setToast({
        kind: "error",
        message: err instanceof ApiError ? err.message : "Uninstall failed.",
      });
    },
  });

  const errorMessage =
    mcpsQuery.error instanceof Error ? mcpsQuery.error.message : null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        filters={filters}
        onChange={setFilters}
        categories={categoriesQuery.data ?? []}
        stats={statsQuery.data}
      />

      <main className="scroll-thin flex-1 overflow-y-auto">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50/80 px-6 py-4 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold text-slate-900">
                MCP Marketplace
              </h1>
              <p className="text-sm text-slate-500">
                One-click install MCP servers for Claude Desktop.
              </p>
            </div>
            <SearchBar value={search} onChange={setSearch} />
          </div>
        </header>

        <div className="space-y-5 p-6">
          <DependencyBanner deps={depsQuery.data} />
          <CardGrid
            mcps={mcps}
            loading={mcpsQuery.isLoading}
            error={errorMessage}
            selectedId={selectedId}
            onSelect={(m) => setSelectedId(m.id)}
          />
        </div>
      </main>

      <DetailPanel
        mcp={selectedMcp}
        installing={!!selectedMcp && installingId === selectedMcp.id}
        uninstalling={uninstallMutation.isPending}
        installLog={
          selectedMcp && logOwnerId === selectedMcp.id ? installLog : []
        }
        dockerHealth={dockerHealthQuery.data}
        onClose={() => setSelectedId(null)}
        onInstall={(values) =>
          selectedMcp && runInstall(selectedMcp.id, values)
        }
        onUninstall={() =>
          selectedMcp && uninstallMutation.mutate(selectedMcp.id)
        }
      />

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
