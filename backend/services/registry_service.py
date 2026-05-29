import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.models.mcp import MCPEntry, MCPWithStatus, InstallStatus, RegistryStats
from backend.core.config_manager import get_installed_mcp_keys

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).parent.parent.parent / "registry" / "mcps.json"


@lru_cache(maxsize=1)
def _load_raw_registry() -> list[dict]:
    """Load registry JSON once and cache it."""
    if not REGISTRY_PATH.exists():
        logger.error("Registry not found at %s", REGISTRY_PATH)
        return []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_all_entries() -> list[MCPEntry]:
    """Parse registry into MCPEntry objects."""
    raw = _load_raw_registry()
    entries = []
    for item in raw:
        try:
            entries.append(MCPEntry(**item))
        except Exception as e:
            logger.warning("Skipping malformed registry entry %s: %s", item.get("id"), e)
    return entries


def reload_registry() -> None:
    """Force reload registry from disk (clears cache)."""
    _load_raw_registry.cache_clear()
    logger.info("Registry cache cleared")


def get_all_mcps(include_status: bool = True) -> list[MCPWithStatus]:
    """Return all MCPs, optionally enriched with installed status."""
    entries = _get_all_entries()
    if not include_status:
        return [MCPWithStatus(**e.model_dump()) for e in entries]

    installed_keys = set(get_installed_mcp_keys())
    result = []
    for entry in entries:
        is_installed = entry.id in installed_keys
        status = InstallStatus.installed if is_installed else InstallStatus.not_installed
        result.append(
            MCPWithStatus(
                **entry.model_dump(),
                is_installed=is_installed,
                install_status=status,
            )
        )
    return result


def get_mcp_by_id(mcp_id: str) -> Optional[MCPEntry]:
    """Find a single MCP entry by ID."""
    for entry in _get_all_entries():
        if entry.id == mcp_id:
            return entry
    return None


def search_mcps(
    query: Optional[str] = None,
    transport: Optional[str] = None,
    category: Optional[str] = None,
    official_only: bool = False,
    free_only: bool = False,
    installed_only: bool = False,
    web_only: bool = False,
) -> list[MCPWithStatus]:
    """Filter MCPs by search query and/or filters."""
    mcps = get_all_mcps(include_status=True)

    if query:
        q = query.lower()
        mcps = [
            m for m in mcps
            if q in m.name.lower()
            or q in m.description.lower()
            or any(q in tag for tag in m.tags)
            or q in m.author.lower()
        ]

    if transport:
        mcps = [m for m in mcps if m.transport.value == transport]

    if category:
        mcps = [m for m in mcps if m.category == category]

    if official_only:
        mcps = [m for m in mcps if m.official]

    if free_only:
        mcps = [m for m in mcps if m.free]

    if installed_only:
        mcps = [m for m in mcps if m.is_installed]

    if web_only:
        mcps = [m for m in mcps if m.claude_web_compatible]

    return mcps


def get_registry_stats() -> RegistryStats:
    """Return summary statistics about the registry."""
    mcps = get_all_mcps(include_status=True)

    by_transport: dict[str, int] = {}
    by_category: dict[str, int] = {}

    for m in mcps:
        by_transport[m.transport.value] = by_transport.get(m.transport.value, 0) + 1
        by_category[m.category] = by_category.get(m.category, 0) + 1

    return RegistryStats(
        total=len(mcps),
        installed=sum(1 for m in mcps if m.is_installed),
        web_compatible=sum(1 for m in mcps if m.claude_web_compatible),
        by_transport=by_transport,
        by_category=by_category,
    )


def get_categories() -> list[str]:
    """Return sorted list of all unique categories."""
    return sorted({m.category for m in _get_all_entries()})


def get_tags() -> list[str]:
    """Return sorted list of all unique tags."""
    tags: set[str] = set()
    for m in _get_all_entries():
        tags.update(m.tags)
    return sorted(tags)
