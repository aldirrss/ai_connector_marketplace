import json
import logging
import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_claude_config_path() -> Path:
    """Resolve claude_desktop_config.json path for current OS."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    if system == "Windows":
        return Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
    # Linux / WSL
    return Path.home() / ".config/claude/claude_desktop_config.json"


def read_config() -> dict[str, Any]:
    """Read current claude_desktop_config.json, return empty structure if missing."""
    config_path = get_claude_config_path()
    if not config_path.exists():
        logger.info("Claude config not found at %s — starting fresh", config_path)
        return {"mcpServers": {}}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        return data
    except json.JSONDecodeError as e:
        logger.error("Failed to parse claude config: %s", e)
        return {"mcpServers": {}}


def write_config(config: dict[str, Any]) -> bool:
    """Write config back to disk, creating backup first."""
    config_path = get_claude_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Backup before writing
    if config_path.exists():
        backup_path = config_path.with_suffix(
            f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        shutil.copy2(config_path, backup_path)
        logger.info("Backup created at %s", backup_path)
        _cleanup_old_backups(config_path.parent)

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("Claude config written to %s", config_path)
        return True
    except OSError as e:
        logger.error("Failed to write claude config: %s", e)
        return False


def _cleanup_old_backups(config_dir: Path, keep: int = 5) -> None:
    """Keep only the N most recent backups."""
    backups = sorted(config_dir.glob("claude_desktop_config.backup_*.json"), reverse=True)
    for old in backups[keep:]:
        old.unlink(missing_ok=True)


def add_mcp_to_config(mcp_key: str, mcp_config: dict[str, Any]) -> bool:
    """Add or update an MCP server entry in the config."""
    config = read_config()
    config["mcpServers"][mcp_key] = mcp_config
    return write_config(config)


def remove_mcp_from_config(mcp_key: str) -> bool:
    """Remove an MCP server entry from the config."""
    config = read_config()
    if mcp_key not in config["mcpServers"]:
        logger.warning("MCP key '%s' not in config, nothing to remove", mcp_key)
        return False
    del config["mcpServers"][mcp_key]
    return write_config(config)


def is_mcp_in_config(mcp_key: str) -> bool:
    """Check if an MCP server is registered in config."""
    config = read_config()
    return mcp_key in config.get("mcpServers", {})


def get_installed_mcp_keys() -> list[str]:
    """Return list of all registered MCP server keys."""
    config = read_config()
    return list(config.get("mcpServers", {}).keys())


def get_config_path_info() -> dict[str, str]:
    """Return config path and existence status."""
    path = get_claude_config_path()
    return {
        "path": str(path),
        "exists": str(path.exists()),
        "os": platform.system(),
    }


def resolve_template_values(
    template: dict[str, Any], values: dict[str, str]
) -> dict[str, Any]:
    """
    Replace {placeholder} tokens in a claude_config template dict with actual values.

    Example:
        template = {"command": "python", "args": ["-m", "mcp", "{db_path}"]}
        values   = {"db_path": "/home/aldi/data.db"}
        → {"command": "python", "args": ["-m", "mcp", "/home/aldi/data.db"]}
    """

    def _replace(obj: Any) -> Any:
        if isinstance(obj, str):
            for k, v in values.items():
                obj = obj.replace(f"{{{k}}}", v)
            return obj
        if isinstance(obj, list):
            return [_replace(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _replace(v) for k, v in obj.items()}
        return obj

    return _replace(template)


def build_claude_config_entry(
    claude_config_template: dict[str, Any], config_values: dict[str, str]
) -> dict[str, Any]:
    """Build the final mcpServers entry from template + user-provided values."""
    resolved = resolve_template_values(claude_config_template, config_values)

    # Strip None / empty keys so the config stays clean
    entry: dict[str, Any] = {}
    if resolved.get("command"):
        entry["command"] = resolved["command"]
    if resolved.get("args"):
        entry["args"] = resolved["args"]
    if resolved.get("env"):
        entry["env"] = {k: v for k, v in resolved["env"].items() if v}
    if resolved.get("url"):
        entry["url"] = resolved["url"]

    return entry


def get_optional_config_field(mcp_key: str) -> Optional[dict[str, Any]]:
    """Return the full config entry for a specific MCP, or None if not present."""
    config = read_config()
    return config.get("mcpServers", {}).get(mcp_key)


def extract_config_values(
    template: dict[str, Any], stored: dict[str, Any], field_keys: list[str]
) -> dict[str, str]:
    """
    Best-effort reverse-map a stored config entry back to its {placeholder} values.

    Walks the template and the stored entry in parallel. Where a template string
    contains a single placeholder (e.g. "{db_path}" or "{ODOO_URL}/mcp"), the
    corresponding stored string is matched to recover the user's value.

    Only field_keys present in config_schema are returned. Values that can't be
    recovered are simply omitted (the editor leaves those fields blank).
    """
    import re

    recovered: dict[str, str] = {}

    def _walk(tmpl: Any, val: Any) -> None:
        if isinstance(tmpl, str) and isinstance(val, str):
            # Find placeholders like {key} in the template string.
            keys = re.findall(r"\{([^{}]+)\}", tmpl)
            if len(keys) == 1 and keys[0] in field_keys:
                key = keys[0]
                # Turn the template into a regex with one capture group.
                pattern = "^" + re.escape(tmpl).replace(
                    re.escape("{" + key + "}"), "(.+)"
                ) + "$"
                m = re.match(pattern, val)
                if m:
                    recovered[key] = m.group(1)
        elif isinstance(tmpl, list) and isinstance(val, list):
            for t, v in zip(tmpl, val):
                _walk(t, v)
        elif isinstance(tmpl, dict) and isinstance(val, dict):
            for k, t in tmpl.items():
                if k in val:
                    _walk(t, val[k])

    _walk(template, stored)
    return recovered
