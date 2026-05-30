import asyncio
import json
import logging
import shutil
from typing import AsyncGenerator, Optional

import httpx

from backend.models.mcp import (
    MCPEntry,
    InstallResponse,
    TransportType,
    InstallType,
    UpdateInfo,
    Profile,
    ProfileInstallResult,
    SystemDetection,
    SystemDetectionReport,
)
from backend.core.config_manager import (
    add_mcp_to_config,
    remove_mcp_from_config,
    build_claude_config_entry,
    is_mcp_in_config,
)

logger = logging.getLogger(__name__)


async def _run_command(
    cmd: list[str], timeout: int = 120
) -> tuple[int, str, str]:
    """Run a subprocess command asynchronously, return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        logger.error("Command timed out: %s", " ".join(cmd))
        return 1, "", "Command timed out"
    except FileNotFoundError as e:
        logger.error("Command not found: %s", e)
        return 1, "", str(e)


def _is_tool_available(tool: str) -> bool:
    """Check if a CLI tool is available in PATH."""
    return shutil.which(tool) is not None


async def _stream_command(
    cmd: list[str], timeout: int = 300
) -> AsyncGenerator[tuple[str, object], None]:
    """
    Run a subprocess and yield its output line by line.

    Yields ("line", str) for each output line (stdout+stderr merged), then a
    final ("rc", int) with the return code.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError as e:
        yield "line", str(e)
        yield "rc", 1
        return

    assert proc.stdout is not None
    try:
        while True:
            raw = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            if not raw:
                break
            yield "line", raw.decode("utf-8", errors="replace").rstrip("\n")
        await asyncio.wait_for(proc.wait(), timeout=timeout)
        yield "rc", proc.returncode or 0
    except asyncio.TimeoutError:
        logger.error("Command timed out: %s", " ".join(cmd))
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        yield "line", "Command timed out"
        yield "rc", 1


async def docker_health() -> dict:
    """Report whether Docker is installed and its daemon is reachable."""
    if not _is_tool_available("docker"):
        return {
            "installed": False,
            "daemon_running": False,
            "message": "Docker not found. Install Docker Desktop from https://docker.com",
        }
    returncode, _, _ = await _run_command(["docker", "info"])
    if returncode != 0:
        return {
            "installed": True,
            "daemon_running": False,
            "message": "Docker is installed but the daemon is not running. Start Docker Desktop.",
        }
    return {"installed": True, "daemon_running": True, "message": "Docker is ready."}


async def _install_npm(entry: MCPEntry) -> tuple[bool, str]:
    """Install via npm/npx — no global install needed for npx packages."""
    if not _is_tool_available("npx") and not _is_tool_available("npm"):
        return False, "npm/npx not found. Install Node.js from https://nodejs.org"

    if entry.install_type == InstallType.npx:
        # npx packages don't need pre-install; config handles the npx call
        return True, f"npx package '{entry.package}' ready (runs on demand via npx)"

    # Global npm install
    returncode, stdout, stderr = await _run_command(
        ["npm", "install", "-g", entry.package]
    )
    if returncode != 0:
        return False, f"npm install failed:\n{stderr}"
    return True, f"Installed {entry.package} globally via npm"


async def _install_pip(entry: MCPEntry) -> tuple[bool, str]:
    """Install via pip."""
    if not _is_tool_available("pip") and not _is_tool_available("pip3"):
        return False, "pip not found. Install Python from https://python.org"

    pip_cmd = "pip3" if _is_tool_available("pip3") else "pip"
    returncode, stdout, stderr = await _run_command(
        [pip_cmd, "install", "--quiet", entry.package]
    )
    if returncode != 0:
        return False, f"pip install failed:\n{stderr}"
    return True, f"Installed {entry.package} via pip"


async def _install_uvx(entry: MCPEntry) -> tuple[bool, str]:
    """Install/verify uvx package availability."""
    if not _is_tool_available("uvx") and not _is_tool_available("uv"):
        return False, (
            "uv/uvx not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )
    return True, f"uvx package '{entry.package}' ready (runs on demand via uvx)"


async def _install_docker(entry: MCPEntry) -> tuple[bool, str]:
    """Pull Docker image."""
    if not _is_tool_available("docker"):
        return False, "Docker not found. Install Docker Desktop from https://docker.com"

    # Check daemon is running
    returncode, _, stderr = await _run_command(["docker", "info"])
    if returncode != 0:
        return False, "Docker daemon is not running. Please start Docker Desktop."

    image = entry.package
    returncode, stdout, stderr = await _run_command(["docker", "pull", image], timeout=300)
    if returncode != 0:
        return False, f"docker pull failed:\n{stderr}"
    return True, f"Pulled Docker image: {image}"


async def _install_url(entry: MCPEntry) -> tuple[bool, str]:
    """HTTP/SSE — no installation needed, just register the URL in config."""
    return True, "HTTP/SSE server registered — no local install required"


async def install_mcp(
    entry: MCPEntry, config_values: dict[str, str]
) -> InstallResponse:
    """
    Main install orchestrator.

    1. Run transport-specific installer (npm/pip/uvx/docker/url)
    2. Build the claude_config entry with user-provided values
    3. Write to claude_desktop_config.json
    """
    logger.info("Installing MCP: %s (transport=%s)", entry.id, entry.transport)

    # Step 1: Transport-specific install
    handlers = {
        TransportType.npm: _install_npm,
        TransportType.pip: _install_pip,
        TransportType.sse: _install_url,
        TransportType.http: _install_url,
        TransportType.docker: _install_docker,
    }

    # uvx uses pip transport type in registry, detect by install_type
    if entry.install_type == InstallType.uvx:
        success, detail = await _install_uvx(entry)
    else:
        handler = handlers.get(entry.transport, _install_url)
        success, detail = await handler(entry)

    if not success:
        return InstallResponse(
            success=False,
            message=f"Installation failed for {entry.name}",
            mcp_id=entry.id,
            details=detail,
        )

    # Step 2: Build config entry
    claude_config_template = entry.claude_config.model_dump(exclude_none=True)
    config_entry = build_claude_config_entry(claude_config_template, config_values)

    # Step 3: Write to Claude Desktop config
    written = add_mcp_to_config(entry.id, config_entry)
    if not written:
        return InstallResponse(
            success=False,
            message=f"Could not write {entry.name} to Claude config",
            mcp_id=entry.id,
            details="Check file permissions on claude_desktop_config.json",
        )

    return InstallResponse(
        success=True,
        message=f"{entry.name} installed successfully. Restart Claude Desktop to activate.",
        mcp_id=entry.id,
        details=detail,
    )


def _log(line: str) -> dict:
    return {"type": "log", "line": line}


def _done(success: bool, message: str, mcp_id: str, details: str = "") -> dict:
    return {
        "type": "done",
        "success": success,
        "message": message,
        "mcp_id": mcp_id,
        "details": details,
    }


async def install_mcp_stream(
    entry: MCPEntry, config_values: dict[str, str]
) -> AsyncGenerator[dict, None]:
    """
    Streaming variant of install_mcp.

    Yields event dicts:
      {"type": "log", "line": str}                      — progress / subprocess output
      {"type": "done", "success": bool, "message": ...} — terminal result

    Mirrors install_mcp's behaviour but surfaces live npm/pip/docker output.
    """
    logger.info("Streaming install: %s (transport=%s)", entry.id, entry.transport)
    yield _log(f"Installing {entry.name} (transport: {entry.transport.value})…")

    success = True
    detail = ""
    rc = 0

    if entry.install_type == InstallType.uvx:
        if not _is_tool_available("uvx") and not _is_tool_available("uv"):
            success, detail = False, "uv/uvx not found. Install from https://astral.sh/uv"
        else:
            detail = f"uvx package '{entry.package}' ready (runs on demand via uvx)"
            yield _log(detail)

    elif entry.transport == TransportType.npm:
        if not _is_tool_available("npx") and not _is_tool_available("npm"):
            success, detail = False, "npm/npx not found. Install Node.js from https://nodejs.org"
        elif entry.install_type == InstallType.npx:
            detail = f"npx package '{entry.package}' ready (runs on demand via npx)"
            yield _log(detail)
        else:
            yield _log(f"$ npm install -g {entry.package}")
            async for kind, payload in _stream_command(["npm", "install", "-g", entry.package]):
                if kind == "line":
                    yield _log(str(payload))
                else:
                    rc = int(payload)  # type: ignore[arg-type]
            success = rc == 0
            detail = (
                f"Installed {entry.package} globally via npm"
                if success
                else "npm install failed — see log above"
            )

    elif entry.transport == TransportType.pip:
        if not _is_tool_available("pip") and not _is_tool_available("pip3"):
            success, detail = False, "pip not found. Install Python from https://python.org"
        else:
            pip_cmd = "pip3" if _is_tool_available("pip3") else "pip"
            yield _log(f"$ {pip_cmd} install {entry.package}")
            async for kind, payload in _stream_command([pip_cmd, "install", entry.package]):
                if kind == "line":
                    yield _log(str(payload))
                else:
                    rc = int(payload)  # type: ignore[arg-type]
            success = rc == 0
            detail = (
                f"Installed {entry.package} via pip"
                if success
                else "pip install failed — see log above"
            )

    elif entry.transport == TransportType.docker:
        if not _is_tool_available("docker"):
            success, detail = False, "Docker not found. Install Docker Desktop from https://docker.com"
        else:
            yield _log("Checking Docker daemon…")
            info_rc, _, _ = await _run_command(["docker", "info"])
            if info_rc != 0:
                success, detail = False, "Docker daemon is not running. Start Docker Desktop."
            else:
                yield _log(f"$ docker pull {entry.package}")
                async for kind, payload in _stream_command(["docker", "pull", str(entry.package)]):
                    if kind == "line":
                        yield _log(str(payload))
                    else:
                        rc = int(payload)  # type: ignore[arg-type]
                success = rc == 0
                detail = (
                    f"Pulled Docker image: {entry.package}"
                    if success
                    else "docker pull failed — see log above"
                )

    else:  # http / sse
        detail = "Remote server — no local install required."
        yield _log(detail)

    if not success:
        yield _done(False, f"Installation failed for {entry.name}", entry.id, detail)
        return

    yield _log("Writing claude_desktop_config.json…")
    claude_config_template = entry.claude_config.model_dump(exclude_none=True)
    config_entry = build_claude_config_entry(claude_config_template, config_values)
    written = add_mcp_to_config(entry.id, config_entry)
    if not written:
        yield _done(
            False,
            f"Could not write {entry.name} to Claude config",
            entry.id,
            "Check file permissions on claude_desktop_config.json",
        )
        return

    yield _log("Done.")
    yield _done(
        True,
        f"{entry.name} installed successfully. Restart Claude Desktop to activate.",
        entry.id,
        detail,
    )


async def uninstall_mcp(entry: MCPEntry) -> InstallResponse:
    """Remove MCP from Claude Desktop config (does not uninstall the package)."""
    removed = remove_mcp_from_config(entry.id)
    if not removed:
        return InstallResponse(
            success=False,
            message=f"{entry.name} was not found in Claude config",
            mcp_id=entry.id,
        )
    return InstallResponse(
        success=True,
        message=f"{entry.name} removed from Claude config. Restart Claude Desktop to apply.",
        mcp_id=entry.id,
        details="Note: pip/npm packages are not uninstalled from your system.",
    )


async def check_dependencies() -> dict[str, bool]:
    """Check which install tools are available on the system."""
    tools = ["npm", "npx", "pip", "pip3", "uvx", "uv", "docker"]
    return {tool: _is_tool_available(tool) for tool in tools}


async def update_mcp_config(
    entry: MCPEntry, config_values: dict[str, str]
) -> InstallResponse:
    """
    Re-apply an installed MCP's config with new values (Phase 4 config editor).

    Rebuilds the mcpServers entry from the registry template + values and writes
    it, overwriting the existing entry. No package (re)install is performed.
    """
    if not is_mcp_in_config(entry.id):
        return InstallResponse(
            success=False,
            message=f"{entry.name} is not installed",
            mcp_id=entry.id,
            details="Install it first before editing its config.",
        )

    claude_config_template = entry.claude_config.model_dump(exclude_none=True)
    config_entry = build_claude_config_entry(claude_config_template, config_values)
    written = add_mcp_to_config(entry.id, config_entry)
    if not written:
        return InstallResponse(
            success=False,
            message=f"Could not update {entry.name} config",
            mcp_id=entry.id,
            details="Check file permissions on claude_desktop_config.json",
        )
    return InstallResponse(
        success=True,
        message=f"{entry.name} config updated. Restart Claude Desktop to apply.",
        mcp_id=entry.id,
    )


async def install_profile(profile: Profile) -> ProfileInstallResult:
    """
    Install every config-free MCP in a profile with one call.

    MCPs that require configuration are reported in `skipped_need_config` so the
    user can install them individually via the normal form flow.
    """
    from backend.services.registry_service import get_mcp_by_id

    installed: list[str] = []
    already: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for mcp_id in profile.mcp_ids:
        entry = get_mcp_by_id(mcp_id)
        if entry is None:
            failed.append(mcp_id)
            continue
        if is_mcp_in_config(mcp_id):
            already.append(mcp_id)
            continue
        if any(field.required for field in entry.config_schema.values()):
            skipped.append(mcp_id)
            continue
        result = await install_mcp(entry, {})
        (installed if result.success else failed).append(mcp_id)

    parts = []
    if installed:
        parts.append(f"installed {len(installed)}")
    if already:
        parts.append(f"{len(already)} already installed")
    if skipped:
        parts.append(f"{len(skipped)} need configuration")
    if failed:
        parts.append(f"{len(failed)} failed")
    message = (
        f"{profile.name}: " + ", ".join(parts) if parts else f"{profile.name}: nothing to do"
    )
    if installed or already:
        message += ". Restart Claude Desktop to apply."

    return ProfileInstallResult(
        profile_id=profile.id,
        installed=installed,
        already_installed=already,
        skipped_need_config=skipped,
        failed=failed,
        message=message,
    )


async def get_latest_version(entry: MCPEntry) -> Optional[str]:
    """Look up the latest published version of an MCP's package (npm/PyPI)."""
    if not entry.package:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            if entry.transport == TransportType.npm:
                r = await client.get(f"https://registry.npmjs.org/{entry.package}/latest")
                if r.status_code == 200:
                    return r.json().get("version")
            elif entry.transport == TransportType.pip:
                r = await client.get(f"https://pypi.org/pypi/{entry.package}/json")
                if r.status_code == 200:
                    return r.json().get("info", {}).get("version")
    except Exception as e:
        logger.debug("Latest-version lookup failed for %s: %s", entry.package, e)
    return None


async def check_updates() -> list[UpdateInfo]:
    """
    Compare installed MCP package versions against the latest published version.

    Only inspects installed MCPs that have a `package` and a comparable
    transport (npm/pip). npx-on-demand packages always run latest, so they have
    no locally pinned version to compare.
    """
    from backend.services.registry_service import get_all_mcps

    results: list[UpdateInfo] = []
    for m in get_all_mcps(include_status=True):
        if not m.is_installed or not m.package:
            continue
        if m.transport not in (TransportType.npm, TransportType.pip):
            continue
        tool = "pip" if m.transport == TransportType.pip else "npm"
        installed_version = await get_package_version(tool, m.package)
        latest = await get_latest_version(m)
        update_available = bool(
            installed_version and latest and installed_version != latest
        )
        results.append(
            UpdateInfo(
                mcp_id=m.id,
                package=m.package,
                installed_version=installed_version,
                latest_version=latest,
                update_available=update_available,
            )
        )
    return results


async def _list_npm_global() -> dict[str, str]:
    """Return {package_name: version} for npm global installs (empty on failure)."""
    if not _is_tool_available("npm"):
        return {}
    rc, out, _ = await _run_command(
        ["npm", "list", "-g", "--depth=0", "--json"], timeout=30
    )
    if rc != 0 or not out:
        return {}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}
    return {
        name: (info.get("version") or "") if isinstance(info, dict) else ""
        for name, info in (data.get("dependencies") or {}).items()
    }


async def _list_pip_packages() -> dict[str, str]:
    """Return {package_name_lower: version} for the active Python's pip (empty on failure)."""
    pip = "pip3" if _is_tool_available("pip3") else ("pip" if _is_tool_available("pip") else None)
    if not pip:
        return {}
    rc, out, _ = await _run_command([pip, "list", "--format=json"], timeout=30)
    if rc != 0 or not out:
        return {}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}
    return {
        (item.get("name") or "").lower(): item.get("version") or ""
        for item in data
        if isinstance(item, dict)
    }


async def _list_docker_images() -> set[str]:
    """Return set of docker image refs (repo and repo:tag) available locally."""
    if not _is_tool_available("docker"):
        return set()
    rc, out, _ = await _run_command(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], timeout=15
    )
    if rc != 0:
        return set()
    images: set[str] = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("<none>"):
            continue
        images.add(line)
        if ":" in line:
            images.add(line.split(":", 1)[0])
    return images


async def _list_uv_tools() -> set[str]:
    """Return set of installed `uv tool` names (uvx-persisted tools)."""
    if not _is_tool_available("uv"):
        return set()
    rc, out, _ = await _run_command(["uv", "tool", "list"], timeout=15)
    if rc != 0:
        return set()
    tools: set[str] = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("-"):
            continue
        first = line.split()[0]
        if first:
            tools.add(first.lower())
    return tools


async def detect_system_installations() -> SystemDetectionReport:
    """
    Scan the local system for registry MCP packages already present (npm/pip/docker/uvx),
    independent of whether they are registered in claude_desktop_config.json.
    """
    from backend.services.registry_service import get_all_mcps

    npm_pkgs, pip_pkgs, docker_imgs, uv_tools = await asyncio.gather(
        _list_npm_global(),
        _list_pip_packages(),
        _list_docker_images(),
        _list_uv_tools(),
    )

    tools_available = {
        "npm": _is_tool_available("npm"),
        "pip": _is_tool_available("pip") or _is_tool_available("pip3"),
        "docker": _is_tool_available("docker"),
        "uv": _is_tool_available("uv"),
    }

    items: list[SystemDetection] = []
    orphan: list[str] = []
    missing: list[str] = []

    for m in get_all_mcps(include_status=True):
        detected = False
        version: Optional[str] = None
        location: Optional[str] = None
        note: Optional[str] = None
        pkg = m.package

        if m.transport == TransportType.npm and pkg:
            if pkg in npm_pkgs:
                detected = True
                version = npm_pkgs[pkg] or None
                location = "npm global"
            elif m.install_type == InstallType.npx:
                note = "npx runs on-demand; no persistent install required"
        elif m.transport == TransportType.pip and pkg:
            key = pkg.lower()
            if key in pip_pkgs:
                detected = True
                version = pip_pkgs[key] or None
                location = "pip (active Python)"
            elif m.install_type == InstallType.uvx:
                if pkg.lower() in uv_tools:
                    detected = True
                    location = "uv tool"
                else:
                    note = "uvx runs on-demand; no persistent install required"
        elif m.transport == TransportType.docker and pkg:
            if pkg in docker_imgs or any(
                img == pkg or img.startswith(pkg + ":") for img in docker_imgs
            ):
                detected = True
                location = "docker image"
        elif m.transport in (TransportType.http, TransportType.sse):
            note = "remote URL — nothing to install locally"

        if detected and not m.is_installed:
            orphan.append(m.id)
        if m.is_installed and pkg and not detected and m.transport in (
            TransportType.npm,
            TransportType.pip,
            TransportType.docker,
        ) and m.install_type not in (InstallType.npx, InstallType.uvx):
            missing.append(m.id)

        items.append(
            SystemDetection(
                mcp_id=m.id,
                name=m.name,
                transport=m.transport,
                package=pkg,
                detected_on_system=detected,
                system_version=version,
                registered_in_claude=m.is_installed,
                location=location,
                note=note,
            )
        )

    return SystemDetectionReport(
        scanned=len(items),
        detected=sum(1 for i in items if i.detected_on_system),
        orphan_packages=orphan,
        missing_packages=missing,
        items=items,
        tools_available=tools_available,
    )


async def get_package_version(tool: str, package: str) -> Optional[str]:
    """Try to detect the installed version of a package."""
    try:
        if tool == "pip":
            pip = "pip3" if _is_tool_available("pip3") else "pip"
            rc, out, _ = await _run_command([pip, "show", package])
            if rc == 0:
                for line in out.splitlines():
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()
        elif tool == "npm":
            rc, out, _ = await _run_command(["npm", "list", "-g", "--depth=0", package])
            if rc == 0 and package in out:
                for line in out.splitlines():
                    if package in line:
                        return line.strip().split("@")[-1]
    except Exception as e:
        logger.debug("Could not get version for %s: %s", package, e)
    return None
