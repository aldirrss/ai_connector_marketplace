from fastapi import APIRouter, HTTPException

from backend.models.mcp import InstallRequest, InstallResponse, StatusResponse, InstallStatus
from backend.services.registry_service import get_mcp_by_id
from backend.services.installer_service import (
    install_mcp,
    uninstall_mcp,
    check_dependencies,
    get_package_version,
)
from backend.core.config_manager import is_mcp_in_config, get_installed_mcp_keys

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
