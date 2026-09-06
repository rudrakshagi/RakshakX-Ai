"""RakshakX Benchmark Protocol v2.0 -- environment freeze and benchmark runner."""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _run_cmd(cmd: list[str], timeout: int = 10) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return "unavailable"


def _read_proc_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except Exception:
        return "unavailable"


# ------------------------------------------------------------------
# Python
# ------------------------------------------------------------------

@dataclass
class PythonEnvironment:
    """Frozen snapshot of the Python runtime environment."""

    version: str = field(default_factory=lambda: sys.version)
    implementation: str = field(default_factory=lambda: platform.python_implementation())
    compiler: str = field(default_factory=lambda: platform.python_compiler())
    executable: str = field(default_factory=lambda: sys.executable)
    prefix: str = field(default_factory=lambda: sys.prefix)
    installed_packages: dict[str, str] = field(default_factory=dict)

    def freeze_installed(self) -> None:
        try:
            from importlib.metadata import packages_distributions
            from importlib.metadata import version as pkg_version

            dists = packages_distributions()
            self.installed_packages = {}
            for pkg_name in dists:
                try:
                    self.installed_packages[pkg_name] = pkg_version(pkg_name)
                except Exception:
                    self.installed_packages[pkg_name] = "unknown"
        except ImportError:
            self.installed_packages = self._freeze_via_pip()

    def _freeze_via_pip(self) -> dict[str, str]:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze", "--exclude-editable"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            packages: dict[str, str] = {}
            for line in result.stdout.strip().splitlines():
                if "==" in line:
                    name, ver = line.split("==", 1)
                    packages[name.strip()] = ver.strip()
            return packages
        except Exception:
            logger.warning("Failed to capture pip freeze output")
            return {}


# ------------------------------------------------------------------
# System / Hardware
# ------------------------------------------------------------------

@dataclass
class SystemEnvironment:
    """Frozen snapshot of the host operating system and hardware."""

    os_name: str = field(default_factory=platform.system)
    os_release: str = field(default_factory=platform.release)
    os_version: str = field(default_factory=platform.version)
    architecture: str = field(default_factory=platform.machine)
    hostname: str = field(default_factory=platform.node)
    processor: str = field(default_factory=platform.processor)


@dataclass
class HardwareEnvironment:
    """Frozen snapshot of CPU / RAM / GPU / Disk."""

    cpu_model: str = ""
    cpu_cores_logical: int = 0
    cpu_cores_physical: int = 0
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    gpu_model: str = ""
    gpu_vram_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0

    def freeze(self) -> None:
        try:
            import psutil

            self.cpu_cores_logical = psutil.cpu_count(logical=True) or 0
            self.cpu_cores_physical = psutil.cpu_count(logical=False) or 0
            vm = psutil.virtual_memory()
            self.ram_total_gb = round(vm.total / (1024**3), 2)
            self.ram_available_gb = round(vm.available / (1024**3), 2)
            du = psutil.disk_usage("/")
            self.disk_total_gb = round(du.total / (1024**3), 2)
            self.disk_free_gb = round(du.free / (1024**3), 2)
        except Exception:
            pass
        # CPU model from /proc/cpuinfo
        try:
            cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8")
            for line in cpuinfo.splitlines():
                if "model name" in line:
                    self.cpu_model = line.split(":", 1)[1].strip()
                    break
        except Exception:
            self.cpu_model = _run_cmd(["lscpu"])
        # GPU
        gpu_out = _run_cmd(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], timeout=5)
        if gpu_out and gpu_out != "unavailable":
            self.gpu_model = gpu_out.split(",")[0].strip()
            try:
                vram_str = gpu_out.split(",")[1].strip().replace("MiB", "").strip()
                self.gpu_vram_gb = round(float(vram_str) / 1024, 2)
            except Exception:
                pass
        else:
            lspci = _run_cmd(["lspci"], timeout=5)
            if "VGA" in lspci or "3D" in lspci:
                for line in lspci.splitlines():
                    if "VGA" in line or "3D" in line:
                        self.gpu_model = line.strip()
                        break
            if not self.gpu_model:
                self.gpu_model = "unavailable"


@dataclass
class SecurityToolsEnvironment:
    """Frozen versions of offensive security tools."""

    tools: dict[str, str] = field(default_factory=dict)

    TOOL_CMDS: dict[str, list[str]] = field(default_factory=lambda: {
        "nmap": ["nmap", "--version"],
        "nuclei": ["nuclei", "-version"],
        "semgrep": ["semgrep", "--version"],
        "sqlmap": ["sqlmap", "--version"],
        "ffuf": ["ffuf", "-V"],
        "trufflehog": ["trufflehog", "--version"],
        "trivy": ["trivy", "--version"],
        "gitleaks": ["gitleaks", "version"],
        "httpx": ["httpx", "-version"],
        "katana": ["katana", "-version"],
        "caido-cli": ["caido-cli", "--version"],
        "govulncheck": ["govulncheck", "-version"],
    })

    def _sandbox_cmd(self, cmd: list[str]) -> str:
        """Try running tool inside sandbox image to avoid host-missing binaries and entrypoint issues."""
        sandbox_image = "rakshakx/sandbox:latest"
        if _run_cmd(["docker", "inspect", "--format", "{{.Id}}", sandbox_image], timeout=5) in ("", "unavailable"):
            return ""
        shell_cmd = " ".join(cmd) + " 2>&1 | cat"
        out = _run_cmd(["docker", "run", "--rm", "--entrypoint", "bash", sandbox_image, "-c", shell_cmd], timeout=12)
        if not out or "unavailable" in out.lower() or "operation not permitted" in out.lower():
            return ""
        # Remove Caido/RakshakX banner lines
        lines = [ln for ln in out.splitlines() if ln.strip() and "RakshakX" not in ln and not ln.strip().startswith("[RakshakX")]
        cleaned = []
        for ln in lines:
            # strip ANSI
            import re as _re
            plain = _re.sub(r'\x1b\[[0-9;]*m', '', ln)
            if "INF" in plain and "Version" not in plain and "version" not in plain and "Nuclei" not in plain:
                continue
            cleaned.append(plain)
        if not cleaned:
            return ""
        # Prefer line with version/semver, skipping upgrade notices
        for ln in cleaned:
            low = ln.lower()
            if "new version" in low:
                continue
            if "version" in low or _re.search(r'\d+\.\d+\.\d+', ln):
                # nuclei version line: "Nuclei Engine Version: v3.11.0"
                # for httpx/katana the ascii art contains no version; skip those
                if ln.strip().lower() in ("projectdiscovery.io",):
                    continue
                return ln.strip()
        # Fallback: last non-empty line that looks like a version (e.g., semgrep 1.173.0)
        for ln in reversed(cleaned):
            if ln.strip() and "new version" not in ln.lower() and _re.search(r'\d+\.\d+', ln):
                return ln.strip()
        # Last resort: first non-banner line
        for ln in reversed(cleaned):
            if ln.strip() and "new version" not in ln.lower():
                return ln.strip()
        return cleaned[0].strip()

    def freeze(self) -> None:
        for name, cmd in self.TOOL_CMDS.items():
            # Prefer sandbox image (authoritative toolchain), fallback to host
            out = self._sandbox_cmd(cmd)
            if not out or out == "unavailable":
                out = _run_cmd(cmd, timeout=8)
            # keep first meaningful line only
            first = out.splitlines()[0] if out else "unavailable"
            # Special handling: semgrep prints blank + version on second line due to upgrade notice
            if name == "semgrep" and first.strip() == "":
                for ln in out.splitlines()[1:]:
                    if ln.strip() and "new version" not in ln.lower():
                        first = ln.strip()
                        break
            if name in ("httpx", "katana") and "version" not in first.lower() and len(out.splitlines()) > 1:
                # httpx/katana have ASCII art header; find version line
                for ln in out.splitlines():
                    if "version" in ln.lower() or ln.strip().startswith("v"):
                        first = ln.strip()
                        break
            self.tools[name] = first[:200] if first else "unavailable"


@dataclass
class DockerEnvironment:
    """Frozen snapshot of the Docker daemon and sandbox image state."""

    docker_version: str = ""
    docker_api_version: str = ""
    sandbox_image: str = ""
    sandbox_image_digest: str = ""
    container_running: bool = False

    def freeze(self) -> None:
        self.docker_version = _run_cmd(["docker", "version", "--format", "{{.Server.Version}}"]) or "unavailable"
        self.docker_api_version = _run_cmd(["docker", "version", "--format", "{{.Server.APIVersion}}"]) or "unavailable"
        # Auto-detect sandbox image if not explicitly set
        if not self.sandbox_image:
            for cand in ["rakshakx/sandbox:latest", "rakshakx/sandbox"]:
                cand_id = _run_cmd(["docker", "inspect", "--format", "{{.Id}}", cand], timeout=5)
                if cand_id and cand_id != "unavailable" and "sha256" in cand_id:
                    self.sandbox_image = cand
                    break
        if self.sandbox_image:
            digest = _run_cmd(["docker", "inspect", "--format", "{{.Id}}", self.sandbox_image], timeout=10)
            if digest and digest != "unavailable":
                self.sandbox_image_digest = digest[:80]


@dataclass
class LLMEnvironment:
    """Frozen snapshot of LLM provider and model configuration."""

    model: str = ""
    provider: str = ""
    api_base: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    reasoning_effort: str | None = None


@dataclass
class TargetEnvironment:
    """Frozen snapshot of the benchmark target."""

    name: str = ""
    version: str = ""
    image: str = ""
    digest: str = ""
    url_or_ip: str = ""
    snapshot: str = ""


@dataclass
class RakshakEnvironmentFreeze:
    """Complete frozen environment state for a benchmark run (Protocol v2.0)."""

    freeze_version: str = "2.0"
    benchmark_version: str = "2.0"
    frozen_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    python: PythonEnvironment = field(default_factory=PythonEnvironment)
    system: SystemEnvironment = field(default_factory=SystemEnvironment)
    hardware: HardwareEnvironment = field(default_factory=HardwareEnvironment)
    security_tools: SecurityToolsEnvironment = field(default_factory=SecurityToolsEnvironment)
    docker: DockerEnvironment = field(default_factory=DockerEnvironment)
    llm: LLMEnvironment = field(default_factory=LLMEnvironment)
    target: TargetEnvironment = field(default_factory=TargetEnvironment)
    inference: str = ""
    rakshak_version: str = ""
    git_commit: str = ""
    git_branch: str = ""
    config_snapshot: dict[str, str] = field(default_factory=dict)
    prompt_verbatim: str = ""
    scope: str = ""
    started_at: str = ""
    ended_at: str = ""
    duration_s: float = 0.0

    def compute_integrity_hash(self) -> str:
        serialized = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def persist(self, output_path: Path) -> str:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        integrity_hash = self.compute_integrity_hash()
        data = asdict(self)
        data["integrity_hash"] = integrity_hash
        output_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Environment freeze written to %s (hash=%s)", output_path, integrity_hash)
        return integrity_hash


def verify_environment_freeze(path: Path) -> tuple[bool, str]:
    """Recompute a stored freeze file's integrity hash and compare.

    Returns (ok, detail): ok=True means the file is byte-consistent with
    what :meth:`RakshakEnvironmentFreeze.persist` wrote (no tampering, no
    truncation, no hand-edits). Any structural problem returns ok=False
    with a reason — never raises, so scripts can report instead of crash.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"unreadable freeze file: {exc}"
    if not isinstance(data, dict):
        return False, "freeze file is not a JSON object"
    stored = data.pop("integrity_hash", None)
    if not stored:
        return False, "missing integrity_hash field"
    try:
        recomputed = hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
    except Exception as exc:
        return False, f"hash recomputation failed: {exc}"
    if recomputed == stored:
        return True, f"integrity_hash verified ({stored[:16]}...)"
    return False, f"hash mismatch: stored {str(stored)[:16]}... vs recomputed {recomputed[:16]}..."


def _get_git_info() -> tuple[str, str]:
    commit = _run_cmd(["git", "rev-parse", "--short", "HEAD"])
    branch = _run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return commit if commit != "unavailable" else "", branch if branch != "unavailable" else ""


def _infer_inference(provider: str, api_base: str) -> str:
    p = (provider or "").lower()
    base = (api_base or "").lower()
    if "localhost" in base or "127.0.0.1" in base or p in ("ollama", "opencode", "local"):
        if "opencode" in p or "ollama" in p:
            return "local"
        return "local"
    if "openai" in p or "anthropic" in p or "openrouter" in p or "groq" in p or "gemini" in p:
        return "cloud" if not base else "api"
    if base.startswith("http"):
        return "api"
    return "cloud"


def freeze_environment(
    *,
    model: str = "",
    provider: str = "",
    api_base: str = "",
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
    sandbox_image: str = "",
    rakshak_version: str = "",
    target_name: str = "",
    target_version: str = "",
    target_image: str = "",
    target_digest: str = "",
    target_url: str = "",
    prompt_verbatim: str = "",
    scope: str = "",
    started_at: str = "",
    ended_at: str = "",
    capture_hardware: bool = True,
    capture_tools: bool = True,
) -> RakshakEnvironmentFreeze:
    """Capture a complete environment freeze for benchmark reproducibility."""
    python_env = PythonEnvironment()
    python_env.freeze_installed()

    system_env = SystemEnvironment()

    hardware_env = HardwareEnvironment()
    if capture_hardware:
        hardware_env.freeze()

    tools_env = SecurityToolsEnvironment()
    if capture_tools:
        tools_env.freeze()

    docker_env = DockerEnvironment()
    docker_env.sandbox_image = sandbox_image
    docker_env.freeze()

    llm_env = LLMEnvironment(
        model=model,
        provider=provider,
        api_base=api_base,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    )

    target_env = TargetEnvironment(
        name=target_name,
        version=target_version,
        image=target_image,
        digest=target_digest,
        url_or_ip=target_url,
        snapshot=target_digest or target_image,
    )

    git_commit, git_branch = _get_git_info()

    # config snapshot (masked)
    config_snapshot: dict[str, str] = {}
    try:
        import json as _json
        from pathlib import Path as _P
        for cfg_path in [_P(".rakshakx/config.json"), _P("rakshak.config.json")]:
            if cfg_path.exists():
                cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
                # mask api_key
                if "api_key" in cfg:
                    k = cfg["api_key"]
                    cfg["api_key"] = (k[:4] + "****" + k[-4:]) if len(k) > 8 else "****"
                config_snapshot[str(cfg_path)] = _json.dumps(cfg)[:2000]
                break
    except Exception:
        pass

    inference = _infer_inference(provider, api_base)

    duration = 0.0
    if started_at and ended_at:
        try:
            s = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            e = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            duration = (e - s).total_seconds()
        except Exception:
            pass

    freeze = RakshakEnvironmentFreeze(
        python=python_env,
        system=system_env,
        hardware=hardware_env,
        security_tools=tools_env,
        docker=docker_env,
        llm=llm_env,
        target=target_env,
        inference=inference,
        rakshak_version=rakshak_version,
        git_commit=git_commit,
        git_branch=git_branch,
        config_snapshot=config_snapshot,
        prompt_verbatim=prompt_verbatim[:4000] if prompt_verbatim else "",
        scope=scope,
        started_at=started_at,
        ended_at=ended_at,
        duration_s=duration,
    )

    logger.info(
        "Environment frozen: python=%s os=%s/%s hw=%s docker=%s git=%s target=%s",
        python_env.version.split()[0] if python_env.version else "unknown",
        system_env.os_name,
        system_env.architecture,
        hardware_env.cpu_model[:40] if hardware_env.cpu_model else "unknown",
        docker_env.docker_version,
        git_commit or "unknown",
        target_name or "none",
    )
    return freeze
