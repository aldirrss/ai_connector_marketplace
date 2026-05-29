import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.mcp import (
    InstallRequest,
    InstallResponse,
    StatusResponse,
    InstallStatus,
    DockerHealth,
    ProfileInstallResult,
    UpdateInfo,
    ConfigEntryResponse,
    ConfigUpdateRequest,
)
from backend.services.registry_service import get_mcp_by_id, get_profile_by_id
from backend.services.installer_service import (
    install_mcp,
    install_mcp_stream,
    install_profile,
    uninstall_mcp,
    update_mcp_config,
    check_dependencies,
    check_updates,
    docker_health,
    get_package_version,
)
from backend.core.config_manager import (
    is_mcp_in_config,
    get_installed_mcp_keys,
    get_optional_config_field,
    extract_config_values,
)

router = APIRouter(prefix="/install", tags=["installer"])


@router.post("/", response_model=InstallResponse)
async def install(request: InstallRequest) -> InstallResponse:
    """
    Install an MCP server.

    Runs the appropriate installer (npm/pip/docker/url) and registers
    the MCP in claude_desktop_config.json.
    """
    entry = get_mcp_by_id(request.mcp_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"MCP '{request.mcp_id}' not found in registry")

    if is_mcp_in_config(request.mcp_id):
        return InstallResponse(
            success=True,
            message=f"{entry.name} is already installed",
            mcp_id=request.mcp_id,
            details="Already present in claude_desktop_config.json",
        )

    return await install_mcp(entry, request.config_values)


@router.post("/stream")
async def install_stream(request: InstallRequest) -> StreamingResponse:
    """
    Install an MCP, streaming live progress as Server-Sent Events.

    Each SSE message's `data:` is a JSON object:
      {"type": "log", "line": "..."}                       — progress / subprocess output
      {"type": "done", "success": bool, "message": "...",  — terminal result
       "mcp_id": "...", "details": "..."}
    """
    entry = get_mcp_by_id(request.mcp_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"MCP '{request.mcp_id}' not found in registry")

    async def event_source():
        if is_mcp_in_config(request.mcp_id):
            payload = {
                "type": "done",
                "success": True,
                "message": f"{entry.name} is already installed",
                "mcp_id": request.mcp_id,
                "details": "Already present in claude_desktop_config.json",
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return
        async for event in install_mcp_stream(entry, request.config_values):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/docker/health", response_model=DockerHealth)
async def docker_health_check() -> DockerHealth:
    """Check whether Docker is installed and its daemon is running."""
    return DockerHealth(**await docker_health())


@router.post("/profile/{profile_id}", response_model=ProfileInstallResult)
async def install_profile_endpoint(profile_id: str) -> ProfileInstallResult:
    """
    One-click install a profile (bundle of MCPs).

    Config-free MCPs are installed; MCPs that need configuration are reported in
    `skipped_need_config` so the user can install them via the normal form.
    """
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    return await install_profile(profile)


@router.get("/updates/check", response_model=list[UpdateInfo])
async def updates_check() -> list[UpdateInfo]:
    """Compare installed MCP package versions against the latest published ones."""
    return await check_updates()


@router.get("/config/{mcp_id}", response_model=ConfigEntryResponse)
async def get_config(mcp_id: str) -> ConfigEntryResponse:
    """Return an installed MCP's current config entry + best-effort decoded values."""
    entry = get_mcp_by_id(mcp_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"MCP '{mcp_id}' not found in registry")
    stored = get_optional_config_field(mcp_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"{entry.name} is not installed")
    template = entry.claude_config.model_dump(exclude_none=True)
    current_values = extract_config_values(
        template, stored, list(entry.config_schema.keys())
    )
    return ConfigEntryResponse(mcp_id=mcp_id, entry=stored, current_values=current_values)


@router.put("/config/{mcp_id}", response_model=InstallResponse)
async def update_config(mcp_id: str, request: ConfigUpdateRequest) -> InstallResponse:
    """Re-apply an installed MCP's config with new values (no reinstall)."""
    entry = get_mcp_by_id(mcp_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"MCP '{mcp_id}' not found in registry")
    return await update_mcp_config(entry, request.config_values)


@router.delete("/{mcp_id}", response_model=InstallResponse)
async def uninstall(mcp_id: str) -> InstallResponse:
    """
    Remove an MCP server from Claude Desktop config.

    Note: this does NOT uninstall the npm/pip package from your system.
    """
    entry = get_mcp_by_id(mcp_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"MCP '{mcp_id}' not found in registry")

    return await uninstall_mcp(entry)


@router.get("/status/{mcp_id}", response_model=StatusResponse)
async def install_status(mcp_id: str) -> StatusResponse:
    """Check if a specific MCP is installed (registered in Claude Desktop config)."""
    entry = get_mcp_by_id(mcp_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"MCP '{mcp_id}' not found in registry")

    in_config = is_mcp_in_config(mcp_id)
    version = None

    if in_config and entry.package:
        tool = "pip" if entry.transport.value == "pip" else "npm"
        version = await get_package_version(tool, entry.package)

    return StatusResponse(
        mcp_id=mcp_id,
        is_installed=in_config,
        status=InstallStatus.installed if in_config else InstallStatus.not_installed,
        version=version,
    )


@router.get("/installed/all", response_model=list[str])
async def list_installed() -> list[str]:
    """Return list of all installed MCP IDs (from Claude Desktop config)."""
    return get_installed_mcp_keys()


@router.get("/dependencies/check")
async def dependency_check() -> dict[str, bool]:
    """Check which install tools (npm, pip, docker, uvx) are available on this machine."""
    return await check_dependencies()
