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
  by_transport: Record<string, number>;
  by_category: Record<string, number>;
}

// GET /install/dependencies/check
export type DependencyCheck = Record<string, boolean>;

// Query params accepted by GET /registry/
export interface RegistryQuery {
  q?: string;
  transport?: string;
  category?: string;
  official_only?: boolean;
  free_only?: boolean;
  installed_only?: boolean;
}
