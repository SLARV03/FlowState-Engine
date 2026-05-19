"""
Sandbox Runner — Isolated Docker-based code execution.

Creates ephemeral containers with strict security constraints to run
agent-generated code and tests. Captures stdout/stderr and enforces
timeouts to prevent runaway execution.
"""

from __future__ import annotations
import os
import uuid
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, Tuple

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from backend.config import get_settings
from backend.models.state import SquadState

logger = logging.getLogger("flowstate.sandbox")


class SandboxResult:
    """Result of a sandbox execution."""

    def __init__(self, exit_code: int, stdout: str, stderr: str, timed_out: bool = False):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        if self.timed_out:
            parts.append(f"\n⏱️ TIMEOUT: Execution exceeded the maximum allowed time.")
        return "\n".join(parts)


class SandboxRunner:
    """
    Manages the lifecycle of ephemeral Docker containers for test execution.

    Security model:
    - No network access (--network none)
    - Memory limited (default 256MB)
    - CPU limited (default 0.5 cores)
    - Read-only root filesystem
    - All capabilities dropped
    - PID limit enforced
    - Hard execution timeout
    """

    def __init__(self):
        self._settings = get_settings()
        try:
            self._client = docker.from_env()
            logger.info("Docker client initialized successfully.")
        except docker.errors.DockerException as e:
            logger.warning(f"Docker not available: {e}. Sandbox will run in mock mode.")
            self._client = None

    def _detect_language(self, state: SquadState) -> str:
        """Detect the project language from file extensions."""
        all_files = {**state["file_system"], **state["test_suite"]}
        extensions = [Path(f).suffix for f in all_files.keys()]

        if any(ext in (".py",) for ext in extensions):
            return "python"
        elif any(ext in (".js", ".ts", ".jsx", ".tsx") for ext in extensions):
            return "javascript"
        elif any(ext in (".go",) for ext in extensions):
            return "go"
        return "python"  # Default

    def _get_base_image(self, language: str) -> str:
        """Get the Docker base image for the detected language."""
        images = {
            "python": self._settings.sandbox.base_image_python,
            "javascript": self._settings.sandbox.base_image_node,
            "go": self._settings.sandbox.base_image_go,
        }
        return images.get(language, self._settings.sandbox.base_image_python)

    def _get_test_command(self, language: str) -> str:
        """Get the test runner command for the detected language."""
        commands = {
            "python": "pip install -r requirements.txt 2>/dev/null; python -m pytest -v --tb=short 2>&1",
            "javascript": "npm install 2>/dev/null && npx jest --verbose 2>&1",
            "go": "go test ./... -v 2>&1",
        }
        return commands.get(language, commands["python"])

    def _generate_requirements(self, state: SquadState) -> str:
        """Auto-detect Python imports and generate requirements.txt content."""
        imports = set()
        all_files = {**state["file_system"], **state["test_suite"]}

        # Standard library modules to exclude
        stdlib = {
            "os", "sys", "json", "re", "math", "random", "datetime", "time",
            "collections", "itertools", "functools", "pathlib", "typing",
            "unittest", "dataclasses", "abc", "enum", "io", "copy",
            "hashlib", "base64", "uuid", "logging", "argparse", "textwrap",
            "string", "struct", "threading", "multiprocessing", "subprocess",
        }

        for content in all_files.values():
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("import "):
                    module = line.split()[1].split(".")[0]
                    if module not in stdlib:
                        imports.add(module)
                elif line.startswith("from ") and " import " in line:
                    module = line.split()[1].split(".")[0]
                    if module not in stdlib:
                        imports.add(module)

        # Always include pytest for Python projects
        imports.add("pytest")

        return "\n".join(sorted(imports))

    def _prepare_workspace(self, state: SquadState, language: str) -> str:
        """Create a temporary directory and dump all files into it."""
        session_id = state.get("session_id", uuid.uuid4().hex[:8])
        tmp_dir = os.path.join(tempfile.gettempdir(), f"flowstate_{session_id}_{uuid.uuid4().hex[:6]}")
        os.makedirs(tmp_dir, exist_ok=True)

        # Write source files
        for path, content in state["file_system"].items():
            full_path = os.path.join(tmp_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Write test files
        for path, content in state["test_suite"].items():
            full_path = os.path.join(tmp_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Generate and write requirements/package files
        if language == "python":
            req_content = self._generate_requirements(state)
            req_path = os.path.join(tmp_dir, "requirements.txt")
            with open(req_path, "w", encoding="utf-8") as f:
                f.write(req_content)

        logger.info(f"Workspace prepared at: {tmp_dir}")
        return tmp_dir

    async def execute(self, state: SquadState) -> SandboxResult:
        """
        Execute tests in an ephemeral Docker container.

        1. Detect language from file extensions
        2. Prepare temporary workspace directory
        3. Spin up a secure Docker container
        4. Run tests and capture output
        5. Clean up workspace
        6. Return results
        """
        language = self._detect_language(state)
        state["detected_language"] = language

        workspace_dir = self._prepare_workspace(state, language)

        try:
            if self._client is None:
                return await self._mock_execute(state, workspace_dir)

            base_image = self._get_base_image(language)
            test_cmd = self._get_test_command(language)
            timeout = self._settings.sandbox.timeout_seconds

            logger.info(
                f"Starting sandbox: image={base_image}, timeout={timeout}s, "
                f"workspace={workspace_dir}"
            )

            # Ensure the image is available
            try:
                self._client.images.get(base_image)
            except ImageNotFound:
                logger.info(f"Pulling image: {base_image}")
                self._client.images.pull(base_image)

            # Run the container with security constraints
            container = self._client.containers.run(
                image=base_image,
                command=["sh", "-c", test_cmd],
                volumes={workspace_dir: {"bind": "/app", "mode": "ro"}},
                working_dir="/app",
                network_mode="none",
                mem_limit=self._settings.sandbox.memory_limit,
                nano_cpus=int(self._settings.sandbox.cpu_limit * 1e9),
                read_only=True,
                tmpfs={"/tmp": "size=64m"},
                cap_drop=["ALL"],
                pids_limit=64,
                remove=True,
                detach=True,
                stdout=True,
                stderr=True,
            )

            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get("StatusCode", 1)
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                return SandboxResult(exit_code=exit_code, stdout=stdout, stderr=stderr)
            except Exception as timeout_err:
                logger.warning(f"Container timed out or errored: {timeout_err}")
                try:
                    container.kill()
                    container.remove(force=True)
                except Exception:
                    pass
                return SandboxResult(
                    exit_code=1,
                    stdout="",
                    stderr=f"Execution timed out after {timeout} seconds.",
                    timed_out=True,
                )

        except (ContainerError, APIError) as e:
            logger.error(f"Docker error: {e}")
            return SandboxResult(
                exit_code=1,
                stdout="",
                stderr=f"Docker execution error: {str(e)}",
            )
        finally:
            # Cleanup workspace
            try:
                shutil.rmtree(workspace_dir, ignore_errors=True)
                logger.info(f"Cleaned up workspace: {workspace_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up workspace: {e}")

    async def _mock_execute(self, state: SquadState, workspace_dir: str) -> SandboxResult:
        """
        Mock sandbox execution when Docker is not available.
        Attempts to run tests directly using subprocess as a fallback.
        """
        import subprocess

        logger.warning("Docker not available — running tests via subprocess (UNSAFE for production).")

        language = self._detect_language(state)

        try:
            if language == "python":
                # Install deps and run pytest
                proc = subprocess.run(
                    ["python", "-m", "pytest", "-v", "--tb=short"],
                    cwd=workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=self._settings.sandbox.timeout_seconds,
                )
            elif language == "javascript":
                proc = subprocess.run(
                    ["npx", "jest", "--verbose"],
                    cwd=workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=self._settings.sandbox.timeout_seconds,
                )
            else:
                return SandboxResult(
                    exit_code=1,
                    stdout="",
                    stderr=f"Mock execution not supported for language: {language}",
                )

            return SandboxResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                exit_code=1, stdout="", stderr="Execution timed out.", timed_out=True
            )
        except FileNotFoundError as e:
            return SandboxResult(
                exit_code=1, stdout="", stderr=f"Runtime not found: {e}"
            )
