"""Safe subprocess execution with timeouts. Never uses shell=True."""

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SubprocessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)


_MAX_OUTPUT_CHARS = 10_000


def run_with_timeout(
    cmd: list[str],
    cwd: Path,
    timeout: int,
    env: Optional[dict] = None,
) -> SubprocessResult:
    """Run a command with a timeout. Never uses shell=True.

    Args:
        cmd: Command as a list of strings (never joined into a shell string).
        cwd: Working directory for the command.
        timeout: Maximum seconds to wait.
        env: Optional environment dict (merged with current env if None).

    Returns:
        SubprocessResult with stdout, stderr, returncode, timing.
    """
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            shell=False,  # NEVER shell=True — cmd args could be untrusted repo paths
        )
        duration = time.monotonic() - start
        return SubprocessResult(
            returncode=result.returncode,
            stdout=result.stdout[:_MAX_OUTPUT_CHARS],
            stderr=result.stderr[:_MAX_OUTPUT_CHARS],
            timed_out=False,
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        return SubprocessResult(
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            timed_out=True,
            duration_seconds=duration,
        )
    except FileNotFoundError:
        duration = time.monotonic() - start
        return SubprocessResult(
            returncode=-1,
            stdout="",
            stderr=f"Command not found: {cmd[0]}",
            timed_out=False,
            duration_seconds=duration,
        )
    except Exception as e:
        duration = time.monotonic() - start
        return SubprocessResult(
            returncode=-1,
            stdout="",
            stderr=str(e),
            timed_out=False,
            duration_seconds=duration,
        )


def tool_available(name: str) -> bool:
    """Return True if the named CLI tool is on PATH."""
    return shutil.which(name) is not None
