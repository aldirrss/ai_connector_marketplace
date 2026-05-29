from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum


class TransportType(str, Enum):
    npm = "npm"
    pip = "pip"
    http = "http"
    sse = "sse"
    docker = "docker"


class InstallType(str, Enum):
    npx = "npx"
    pip = "pip"
    uvx = "uvx"
    docker = "docker"
    url = "url"


class InstallStatus(str, Enum):
    installed = "installed"
    not_installed = "not_installed"
    unknown = "unknown"


class ConfigFieldSchema(BaseModel):
    type: str  # "string" | "secret"
    label: str
    placeholder: str = ""
    required: bool = True
    description: str = ""


class ClaudeConfig(BaseModel):
    command: Optional[str] = None
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None
    url: Optional[str] = None


class MCPEntry(BaseModel):
    id: str
    name: str
    author: str
    version: str
    description: str
    long_description: str
    transport: TransportType
    install_type: InstallType
    package: Optional[str] = None
    install_cmd: Optional[str] = None
    config_schema: dict[str, ConfigFieldSchema] = Field(default_factory=dict)
    claude_config: ClaudeConfig
    tags: list[str] = Field(default_factory=list)
    category: str
    stars: float = 0.0
    official: bool = False
    free: bool = True
    homepage: str = ""
    icon: str = "ti-plug"
    # Phase 3: cross-platform compatibility metadata.
    # claude_web_compatible: usable on claude.ai (web) — only remote http/sse URLs qualify.
    # platforms: which AI clients this MCP can run on (e.g. ["desktop", "web"]).
    claude_web_compatible: bool = False
    platforms: list[str] = Field(default_factory=lambda: ["desktop"])


class MCPWithStatus(MCPEntry):
    is_installed: bool = False
    install_status: InstallStatus = InstallStatus.unknown


class InstallRequest(BaseModel):
    mcp_id: str
    config_values: dict[str, str] = Field(default_factory=dict)


class InstallResponse(BaseModel):
    success: bool
    message: str
    mcp_id: str
    details: Optional[str] = None


class UninstallRequest(BaseModel):
    mcp_id: str


class StatusResponse(BaseModel):
    mcp_id: str
    is_installed: bool
    status: InstallStatus
    version: Optional[str] = None


class ClaudeConfigFile(BaseModel):
    mcpServers: dict[str, Any] = Field(default_factory=dict)


class RegistryStats(BaseModel):
    total: int
    installed: int
    web_compatible: int = 0
    by_transport: dict[str, int]
    by_category: dict[str, int]


class DockerHealth(BaseModel):
    installed: bool
    daemon_running: bool
    message: str


# ── Phase 4: Power Features ──────────────────────────────────────────────


class Profile(BaseModel):
    """A curated bundle of MCPs installed together with one click."""

    id: str
    name: str
    description: str = ""
    icon: str = "ti-stack-2"
    mcp_ids: list[str] = Field(default_factory=list)


class ProfileInstallResult(BaseModel):
    profile_id: str
    installed: list[str] = Field(default_factory=list)
    already_installed: list[str] = Field(default_factory=list)
    skipped_need_config: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    message: str


class UpdateInfo(BaseModel):
    mcp_id: str
    package: Optional[str] = None
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    update_available: bool = False


class ConfigEntryResponse(BaseModel):
    """Current config for an installed MCP plus best-effort decoded values."""

    mcp_id: str
    entry: dict[str, Any] = Field(default_factory=dict)
    current_values: dict[str, str] = Field(default_factory=dict)


class ConfigUpdateRequest(BaseModel):
    config_values: dict[str, str] = Field(default_factory=dict)


class SyncInfo(BaseModel):
    source: Optional[str] = None
    last_synced: Optional[str] = None
    active: bool = False
    count: Optional[int] = None


class SyncResult(BaseModel):
    success: bool
    message: str
    count: int = 0
    source: Optional[str] = None
