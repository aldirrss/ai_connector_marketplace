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
    by_transport: dict[str, int]
    by_category: dict[str, int]
