// TypeScript mirror of backend/models/mcp.py — keep in sync with the Pydantic models.

export type TransportType = "npm" | "pip" | "http" | "sse" | "docker";
export type InstallType = "npx" | "pip" | "uvx" | "docker" | "url";
export type InstallStatus = "installed" | "not_installed" | "unknown";

export interface ConfigFieldSchema {
  type: "string" | "secret";
  label: string;
  placeholder: string;
  required: boolean;
  description: string;
}

export interface ClaudeConfig {
  command?: string | null;
  args?: string[] | null;
  env?: Record<string, string> | null;
  url?: string | null;
}

export interface MCPEntry {
  id: string;
  name: string;
  author: string;
  version: string;
  description: string;
  long_description: string;
  transport: TransportType;
  install_type: InstallType;
  package?: string | null;
  install_cmd?: string | null;
  config_schema: Record<string, ConfigFieldSchema>;
  claude_config: ClaudeConfig;
  tags: string[];
  category: string;
  stars: number;
  official: boolean;
  free: boolean;
  homepage: string;
  icon: string;
  claude_web_compatible: boolean;
  platforms: string[];
}

export interface MCPWithStatus extends MCPEntry {
  is_installed: boolean;
  install_status: InstallStatus;
}

export interface InstallRequest {
  mcp_id: string;
  config_values: Record<string, string>;
}

export interface InstallResponse {
  success: boolean;
  message: string;
  mcp_id: string;
  details?: string | null;
}

export interface RegistryStats {
  total: number;
  installed: number;
  web_compatible: number;
  by_transport: Record<string, number>;
  by_category: Record<string, number>;
}

// GET /install/dependencies/check
export type DependencyCheck = Record<string, boolean>;

// GET /install/docker/health
export interface DockerHealth {
  installed: boolean;
  daemon_running: boolean;
  message: string;
}

// ── Phase 4 ───────────────────────────────────────────────────────────────

export interface Profile {
  id: string;
  name: string;
  description: string;
  icon: string;
  mcp_ids: string[];
}

export interface ProfileInstallResult {
  profile_id: string;
  installed: string[];
  already_installed: string[];
  skipped_need_config: string[];
  failed: string[];
  message: string;
}

export interface UpdateInfo {
  mcp_id: string;
  package?: string | null;
  installed_version?: string | null;
  latest_version?: string | null;
  update_available: boolean;
}

export interface ConfigEntryResponse {
  mcp_id: string;
  entry: Record<string, unknown>;
  current_values: Record<string, string>;
}

export interface SyncInfo {
  source?: string | null;
  last_synced?: string | null;
  active: boolean;
  count?: number | null;
}

export interface SyncResult {
  success: boolean;
  message: string;
  count: number;
  source?: string | null;
}

// Query params accepted by GET /registry/
export interface RegistryQuery {
  q?: string;
  transport?: string;
  category?: string;
  official_only?: boolean;
  free_only?: boolean;
  installed_only?: boolean;
  web_only?: boolean;
}

// Server-Sent Events emitted by POST /install/stream
export interface InstallLogEvent {
  type: "log";
  line: string;
}
export interface InstallDoneEvent {
  type: "done";
  success: boolean;
  message: string;
  mcp_id: string;
  details?: string;
}
export type InstallStreamEvent = InstallLogEvent | InstallDoneEvent;
