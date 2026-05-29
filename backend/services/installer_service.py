import asyncio
import logging
import shutil
from typing import AsyncGenerator, Optional

from backend.models.mcp import MCPEntry, InstallResponse, TransportType, InstallType
from backend.core.config_manager import (
    add_mcp_to_config,
    remove_mcp_from_config,
    build_claude_config_entry,
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
