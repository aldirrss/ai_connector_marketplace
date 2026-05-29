import type {
  MCPWithStatus,
  RegistryStats,
  RegistryQuery,
  InstallResponse,
  DependencyCheck,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

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
};

export { ApiError };
