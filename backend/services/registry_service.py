import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx

from backend.models.mcp import (
    MCPEntry,
    MCPWithStatus,
    InstallStatus,
    RegistryStats,
    Profile,
    SyncInfo,
)
from backend.core.config_manager import get_installed_mcp_keys

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).parent.parent.parent / "registry" / "mcps.json"
PROFILES_PATH = Path(__file__).parent.parent.parent / "registry" / "profiles.json"

# Phase 4: community registry sync. When a remote registry is applied, it
# overrides the on-disk catalog in memory until cleared/reloaded.
_remote_registry: Optional[list[dict]] = None
_sync_source: Optional[str] = None
_sync_time: Optional[str] = None


@lru_cache(maxsize=1)
def _load_raw_registry() -> list[dict]:
    """Load registry JSON once and cache it."""
    if not REGISTRY_PATH.exists():
        logger.error("Registry not found at %s", REGISTRY_PATH)
        return []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _active_raw() -> list[dict]:
    """Return the active registry source: synced remote override, else local disk."""
    if _remote_registry is not None:
        return _remote_registry
    return _load_raw_registry()


def _get_all_entries() -> list[MCPEntry]:
    """Parse registry into MCPEntry objects."""
    raw = _active_raw()
    entries = []
    for item in raw:
        try:
            entries.append(MCPEntry(**item))
        except Exception as e:
            logger.warning("Skipping malformed registry entry %s: %s", item.get("id"), e)
    return entries


def reload_registry() -> None:
    """Force reload registry from disk (clears cache and any synced override)."""
    global _remote_registry, _sync_source, _sync_time
    _load_raw_registry.cache_clear()
    _remote_registry = None
    _sync_source = None
    _sync_time = None
    logger.info("Registry cache cleared and synced override reset")


def apply_remote_registry(entries: list[dict], source: str) -> int:
    """
    Replace the active registry with a validated remote catalog (in memory).

    Returns the number of valid entries applied. Raises ValueError if no entry
    is parseable, so a bad remote payload never wipes the catalog.
    """
    global _remote_registry, _sync_source, _sync_time
    valid: list[dict] = []
    for item in entries:
        try:
            MCPEntry(**item)
            valid.append(item)
        except Exception as e:
            logger.warning("Sync: skipping malformed entry %s: %s", item.get("id"), e)
    if not valid:
        raise ValueError("Remote registry contained no valid MCP entries")
    _remote_registry = valid
    _sync_source = source
    _sync_time = datetime.now(timezone.utc).isoformat()
    logger.info("Applied %d MCPs from remote registry %s", len(valid), source)
    return len(valid)


def get_sync_info() -> SyncInfo:
    """Report whether a synced registry is active and where it came from."""
    return SyncInfo(
        source=_sync_source or os.getenv("MARKETPLACE_REGISTRY_URL"),
        last_synced=_sync_time,
        active=_remote_registry is not None,
        count=len(_remote_registry) if _remote_registry is not None else None,
    )


def get_default_registry_url() -> Optional[str]:
    """Remote registry URL from the MARKETPLACE_REGISTRY_URL env var, if set."""
    return os.getenv("MARKETPLACE_REGISTRY_URL")


async def sync_remote_registry(url: Optional[str] = None) -> int:
    """
    Fetch a remote registry JSON and apply it as the active catalog.

    `url` falls back to the MARKETPLACE_REGISTRY_URL env var. The payload may be
    either a bare list of MCP entries or an object with an "mcps" key. Returns
    the number of entries applied; raises ValueError on a missing/invalid source.
    """
    target = url or get_default_registry_url()
    if not target:
        raise ValueError(
            "No registry URL provided. Set MARKETPLACE_REGISTRY_URL or pass ?url=…"
        )
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(target)
        resp.raise_for_status()
        data = resp.json()
    entries = data.get("mcps", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError("Remote registry must be a JSON list or an object with 'mcps'")
    return apply_remote_registry(entries, target)


# ── Profiles (Phase 4) ───────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_profiles() -> list[Profile]:
    """Load curated install bundles from profiles.json."""
    if not PROFILES_PATH.exists():
        return []
    try:
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [Profile(**p) for p in raw]
    except Exception as e:
        logger.error("Failed to load profiles: %s", e)
        return []


def get_profiles() -> list[Profile]:
    """Return all profiles whose member MCP IDs all exist in the registry."""
    known = {e.id for e in _get_all_entries()}
    profiles = []
    for p in _load_profiles():
        valid_ids = [mid for mid in p.mcp_ids if mid in known]
        if valid_ids:
            profiles.append(p.model_copy(update={"mcp_ids": valid_ids}))
    return profiles


def get_profile_by_id(profile_id: str) -> Optional[Profile]:
    for p in get_profiles():
        if p.id == profile_id:
            return p
    return None


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
