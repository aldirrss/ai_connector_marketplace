import type {
  MCPWithStatus,
  RegistryStats,
  RegistryQuery,
  InstallResponse,
  DependencyCheck,
  DockerHealth,
  InstallStreamEvent,
  Profile,
  ProfileInstallResult,
  UpdateInfo,
  ConfigEntryResponse,
  SyncInfo,
  SyncResult,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8765";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      `Cannot reach the backend at ${API_BASE_URL}. Is it running? Try ./start.sh`,
      0,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // body was not JSON; keep statusText
    }
    throw new ApiError(detail, res.status);
  }

  // DELETE/POST may return JSON; all current endpoints do.
  return (await res.json()) as T;
}

export function buildRegistryQuery(query: RegistryQuery): string {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.transport) params.set("transport", query.transport);
  if (query.category) params.set("category", query.category);
  if (query.official_only) params.set("official_only", "true");
  if (query.free_only) params.set("free_only", "true");
  if (query.installed_only) params.set("installed_only", "true");
  if (query.web_only) params.set("web_only", "true");
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  listMcps(query: RegistryQuery = {}): Promise<MCPWithStatus[]> {
    return request<MCPWithStatus[]>(`/registry/${buildRegistryQuery(query)}`);
  },

  stats(): Promise<RegistryStats> {
    return request<RegistryStats>("/registry/stats");
  },

  categories(): Promise<string[]> {
    return request<string[]>("/registry/categories");
  },

  installedIds(): Promise<string[]> {
    return request<string[]>("/install/installed/all");
  },

  dependencies(): Promise<DependencyCheck> {
    return request<DependencyCheck>("/install/dependencies/check");
  },

  dockerHealth(): Promise<DockerHealth> {
    return request<DockerHealth>("/install/docker/health");
  },

  /**
   * Install an MCP while streaming live progress (POST /install/stream, SSE).
   * Calls onEvent for every log/done event. Resolves when the stream ends.
   * Uses fetch + ReadableStream (not EventSource) so the POST body can carry
   * config values without leaking secrets into a URL.
   */
  async installStream(
    mcp_id: string,
    config_values: Record<string, string>,
    onEvent: (event: InstallStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    let res: Response;
    try {
      res = await fetch(`${API_BASE_URL}/install/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mcp_id, config_values }),
        signal,
      });
    } catch {
      throw new ApiError(
        `Cannot reach the backend at ${API_BASE_URL}. Is it running?`,
        0,
      );
    }
    if (!res.ok || !res.body) {
      throw new ApiError(`Install stream failed (${res.status})`, res.status);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    // Parse SSE frames: messages separated by a blank line, each "data:" line is JSON.
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        for (const line of frame.split("\n")) {
          const trimmed = line.startsWith("data:") ? line.slice(5).trim() : "";
          if (!trimmed) continue;
          try {
            onEvent(JSON.parse(trimmed) as InstallStreamEvent);
          } catch {
            // ignore malformed frame
          }
        }
      }
    }
  },

  install(
    mcp_id: string,
    config_values: Record<string, string>,
  ): Promise<InstallResponse> {
    return request<InstallResponse>("/install/", {
      method: "POST",
      body: JSON.stringify({ mcp_id, config_values }),
    });
  },

  uninstall(mcp_id: string): Promise<InstallResponse> {
    return request<InstallResponse>(`/install/${encodeURIComponent(mcp_id)}`, {
      method: "DELETE",
    });
  },

  // ── Phase 4 ──────────────────────────────────────────────────────────

  profiles(): Promise<Profile[]> {
    return request<Profile[]>("/registry/profiles");
  },

  installProfile(profile_id: string): Promise<ProfileInstallResult> {
    return request<ProfileInstallResult>(
      `/install/profile/${encodeURIComponent(profile_id)}`,
      { method: "POST" },
    );
  },

  updates(): Promise<UpdateInfo[]> {
    return request<UpdateInfo[]>("/install/updates/check");
  },

  getConfig(mcp_id: string): Promise<ConfigEntryResponse> {
    return request<ConfigEntryResponse>(
      `/install/config/${encodeURIComponent(mcp_id)}`,
    );
  },

  updateConfig(
    mcp_id: string,
    config_values: Record<string, string>,
  ): Promise<InstallResponse> {
    return request<InstallResponse>(
      `/install/config/${encodeURIComponent(mcp_id)}`,
      { method: "PUT", body: JSON.stringify({ config_values }) },
    );
  },

  syncInfo(): Promise<SyncInfo> {
    return request<SyncInfo>("/registry/sync/info");
  },

  sync(url?: string): Promise<SyncResult> {
    const qs = url ? `?url=${encodeURIComponent(url)}` : "";
    return request<SyncResult>(`/registry/sync${qs}`, { method: "POST" });
  },
};

export { ApiError };
