from fastapi import APIRouter, Query
from typing import Optional

from backend.models.mcp import MCPWithStatus, RegistryStats
from backend.services.registry_service import (
    get_all_mcps,
    search_mcps,
    get_mcp_by_id,
    get_registry_stats,
    get_categories,
    get_tags,
    reload_registry,
)
from backend.core.config_manager import get_config_path_info

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/", response_model=list[MCPWithStatus])
async def list_mcps(
    q: Optional[str] = Query(None, description="Search query"),
    transport: Optional[str] = Query(None, description="Filter by transport: npm, pip, http, sse, docker"),
    category: Optional[str] = Query(None, description="Filter by category"),
    official_only: bool = Query(False, description="Show only official MCPs"),
    free_only: bool = Query(False, description="Show only free MCPs"),
    installed_only: bool = Query(False, description="Show only installed MCPs"),
) -> list[MCPWithStatus]:
    """List all MCPs with optional search and filters."""
    if any([q, transport, category, official_only, free_only, installed_only]):
        return search_mcps(
            query=q,
            transport=transport,
            category=category,
            official_only=official_only,
            free_only=free_only,
            installed_only=installed_only,
        )
    return get_all_mcps()


@router.get("/stats", response_model=RegistryStats)
async def registry_stats() -> RegistryStats:
    """Return statistics about the registry."""
    return get_registry_stats()


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    """Return all unique categories."""
    return get_categories()


@router.get("/tags", response_model=list[str])
async def list_tags() -> list[str]:
    """Return all unique tags."""
    return get_tags()


@router.get("/config-info")
async def config_info() -> dict:
    """Return the path to Claude Desktop config and whether it exists."""
    return get_config_path_info()


@router.post("/reload")
async def reload() -> dict:
    """Force reload registry from disk."""
    reload_registry()
    return {"message": "Registry reloaded"}


@router.get("/{mcp_id}", response_model=MCPWithStatus)
async def get_mcp(mcp_id: str) -> MCPWithStatus:
    """Get a single MCP by ID with install status."""
    from fastapi import HTTPException
    entry = get_mcp_by_id(mcp_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"MCP '{mcp_id}' not found")
    mcps = get_all_mcps()
    for m in mcps:
        if m.id == mcp_id:
            return m
    return MCPWithStatus(**entry.model_dump())
