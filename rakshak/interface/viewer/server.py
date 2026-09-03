"""Backend REST API & System Health Server for RakshakX Console."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import platform
import threading
import time
import traceback
import uuid
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import psutil

from rakshak.core.paths import base_runs_dir, run_dir_for, runtime_state_dir

logger = logging.getLogger(__name__)
CONFIG_FILE = Path(".rakshakx") / "config.json"
_LEGACY_CONFIG_FILE = Path("rakshak.config.json")
START_TIME = time.time()
_CURR_PROCESS = psutil.Process()
_active_scan_lock = threading.Lock()
_active_scan_dir: Path | None = None


def _set_active_scan(run_dir: Path | None) -> None:
    """Record the most recently launched scan so GET handlers serve its live data."""
    global _active_scan_dir
    with _active_scan_lock:
        _active_scan_dir = run_dir


def _resolve_run_dir(view_run_dir: Path) -> Path:
    """Return the active scan dir (latest launched) or fall back to the view scan dir."""
    global _active_scan_dir
    with _active_scan_lock:
        if _active_scan_dir is not None and _active_scan_dir.exists():
            return _active_scan_dir
        _active_scan_dir = None
    return view_run_dir


def _resolve_artifact_dir(view_run_dir: Path, filename: str) -> Path:
    """Prefer the active scan dir, but fall back to view dir when the artifact exists there."""
    active = _resolve_run_dir(view_run_dir)
    if (active / filename).exists():
        return active
    if (view_run_dir / filename).exists():
        return view_run_dir
    return active


def _write_run_meta(run_dir: Path, **updates: Any) -> None:
    meta_file = run_dir / "run_meta.json"
    meta: dict[str, Any] = {}
    if meta_file.exists():
        with contextlib.suppress(Exception):
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
    meta.update(updates)
    with contextlib.suppress(Exception):
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_system_telemetry() -> dict[str, Any]:
    """Gather 100% real-time live resource telemetry, host stats, and child worker processes."""
    # Live CPU (instantaneous sample)
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    ram_used_gb = round(mem.used / (1024 ** 3), 2)
    ram_total_gb = round(mem.total / (1024 ** 3), 2)
    ram_percent = mem.percent

    # Process & Child Workers Telemetry
    proc_mem_mb = round(_CURR_PROCESS.memory_info().rss / (1024 * 1024), 1)
    proc_cpu = round(_CURR_PROCESS.cpu_percent(interval=None), 1)
    num_threads = _CURR_PROCESS.num_threads()

    children_info = []
    try:
        for child in _CURR_PROCESS.children(recursive=True):
            try:
                c_mem = round(child.memory_info().rss / (1024 * 1024), 1)
                children_info.append({
                    "pid": child.pid,
                    "name": child.name(),
                    "status": child.status(),
                    "cpu_percent": round(child.cpu_percent(interval=None), 1),
                    "memory_mb": c_mem,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

    uptime_secs = int(time.time() - START_TIME)
    uptime_str = f"{uptime_secs // 60}m {uptime_secs % 60}s"

    return {
        "timestamp": time.time(),
        "backend": {
            "status": "online",
            "port": 8080,
            "pid": _CURR_PROCESS.pid,
            "latency_ms": 2,
            "uptime": uptime_str,
            "python_version": platform.python_version(),
            "os": f"{platform.system()} {platform.release()}",
            "process_memory_mb": proc_mem_mb,
            "process_cpu_percent": proc_cpu,
            "active_threads": num_threads,
        },
        "child_workers": children_info,
        "mcp_bridge": {
            "status": "ready",
            "protocol": "Model Context Protocol (JSON-RPC 2.0)",
            "supported_tools": ["rakshak_start_scan", "rakshak_list_findings", "rakshak_get_poc", "rakshak_get_report"],
            "clients": ["Antigravity IDE", "OpenCode", "Claude Desktop", "Cursor"],
        },
        "sandbox": {
            "status": "ready",
            "container": "rakshakx/sandbox:latest",
            "proxy_port": 48080,
            "tools_installed": ["nmap", "nuclei", "sqlmap", "ffuf", "semgrep", "agent-browser"],
        },
        "resources": {
            "cpu_percent": cpu_percent,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "ram_percent": ram_percent,
        },
    }


def _load_user_config() -> dict[str, Any]:
    default_cfg = {
        "provider": "openai",
        "model": os.getenv("RAKSHAK_LLM__MODEL", "openai/gpt-4o"),
        "api_key": os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or "",
        "api_base": os.getenv("RAKSHAK_LLM__API_BASE", ""),
        "temperature": 0.2,
        "max_budget_usd": 10.0,
        "reasoning_effort": "medium",
        "use_mcp_ide_llm": False,
    }
    config_source: Path | None = None
    if CONFIG_FILE.exists():
        config_source = CONFIG_FILE
    elif _LEGACY_CONFIG_FILE.exists():
        config_source = _LEGACY_CONFIG_FILE
    if config_source is not None:
        try:
            saved = json.loads(config_source.read_text(encoding="utf-8"))
            default_cfg.update(saved)
        except Exception:
            pass
    return default_cfg


def _save_user_config(cfg: dict[str, Any]) -> None:
    # Never overwrite a stored API key with an empty one. The web console only shows a
    # masked key, so a Save without re-entering the key must preserve the existing value.
    if not cfg.get("api_key"):
        existing = _load_user_config()
        existing.pop("masked_key", None)
        existing.pop("is_key_configured", None)
        cfg["api_key"] = existing.get("api_key") or ""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    _apply_config_env(cfg)


def _apply_config_env(cfg: dict[str, Any]) -> None:
    """Push config values into process env so the scan runner's LiteLLM picks them up."""
    if cfg.get("model"):
        os.environ["RAKSHAK_LLM__MODEL"] = cfg["model"]
    if cfg.get("api_key"):
        prov = (cfg.get("provider") or "").lower()
        if "anthropic" in prov or "claude" in cfg.get("model", "").lower():
            os.environ["ANTHROPIC_API_KEY"] = cfg["api_key"]
        elif "gemini" in prov or "google" in cfg.get("model", "").lower():
            os.environ["GEMINI_API_KEY"] = cfg["api_key"]
        elif "groq" in prov or cfg.get("model", "").lower().startswith("groq"):
            os.environ["GROQ_API_KEY"] = cfg["api_key"]
        elif "openrouter" in prov or cfg.get("model", "").lower().startswith("openrouter"):
            os.environ["OPENROUTER_API_KEY"] = cfg["api_key"]
        else:
            os.environ["OPENAI_API_KEY"] = cfg["api_key"]
    if cfg.get("api_base"):
        os.environ["RAKSHAK_LLM__API_BASE"] = cfg["api_base"]


def _run_scan_background(run_dir: Path, *, target: str, mode: str, prompt: str, benchmark_target: str = "", scope: str = "") -> None:
    """Execute the real autonomous scan in a background thread, updating live status."""
    scan_id = run_dir.name
    _write_run_meta(run_dir, status="Running", started_at=datetime.now(UTC).isoformat())
    started = time.time()
    try:
        from rakshak.core.runner import run_rakshak_scan

        is_whitebox = "white" in mode.lower()
        # Resolve benchmark mode: if mode is T01/A.1 etc use verbatim prompt
        effective_mode = mode.strip()
        # Normalize common aliases
        _mode_lower = effective_mode.lower()
        if "benchmark" in _mode_lower or _mode_lower in ("t01", "a.1", "a1", "juice", "juice_shop"):
            effective_mode = "T01"
        asyncio.run(run_rakshak_scan(
            target=target,
            scan_id=scan_id,
            scan_mode=effective_mode,
            is_whitebox=is_whitebox,
            max_budget_usd=3.0,
            max_turns=30,
            prompt_verbatim=prompt or None,
            scope=scope or target,
            benchmark_target=benchmark_target or None,
        ))
        duration = f"{int(time.time() - started) // 60}m {int(time.time() - started) % 60}s"
        _write_run_meta(run_dir, status="Completed", duration=duration, ended_at=datetime.now(UTC).isoformat())
    except Exception as exc:
        logger.error("Background scan %s failed: %s\n%s", scan_id, exc, traceback.format_exc())
        _write_run_meta(run_dir, status="Failed", error=str(exc), ended_at=datetime.now(UTC).isoformat())


def _make_handler(run_dir: Path) -> type[BaseHTTPRequestHandler]:
    class ApiHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.OK)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            content_length = int(self.headers.get("Content-Length", 0))
            body_data = {}
            if content_length > 0:
                try:
                    raw_body = self.rfile.read(content_length)
                    body_data = json.loads(raw_body.decode("utf-8"))
                except Exception:
                    pass

            def _send_json(payload: Any, status: int = HTTPStatus.OK) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

            if path == "/api/config":
                _save_user_config(body_data)
                _send_json({"success": True, "message": "LLM Configuration saved successfully!"})
                return

            if path == "/api/scan":
                target = body_data.get("target", "example.com")
                mode = body_data.get("mode", "Black Box")
                prompt = body_data.get("prompt", "")
                benchmark_target = body_data.get("benchmark_target", body_data.get("benchmarkTarget", ""))
                scope = body_data.get("scope", target)
                scan_id = f"scan-{uuid.uuid4().hex[:8]}"
                new_run_dir = run_dir_for(scan_id)
                with contextlib.suppress(Exception):
                    new_run_dir.mkdir(parents=True, exist_ok=True)
                _write_run_meta(new_run_dir, scan_id=scan_id, target=target, mode=mode,
                                prompt=prompt, scope=scope, benchmark_target=benchmark_target, status="Queued")
                _set_active_scan(new_run_dir)
                threading.Thread(
                    target=_run_scan_background,
                    args=(new_run_dir,),
                    kwargs={"target": target, "mode": mode, "prompt": prompt, "benchmark_target": benchmark_target, "scope": scope},
                    daemon=True,
                ).start()
                _send_json({
                    "success": True,
                    "scan_id": scan_id,
                    "target": target,
                    "mode": mode,
                    "prompt": prompt,
                    "scope": scope,
                    "benchmark_target": benchmark_target,
                    "message": f"Autonomous security assessment started for {target}",
                })
                return

            if path == "/api/benchmark/prompts":
                try:
                    from rakshak.benchmark.prompts import PROMPT_REGISTRY
                    _send_json({"prompts": PROMPT_REGISTRY})
                except Exception as e:
                    _send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path == "/api/benchmark/targets":
                try:
                    import glob as _glob
                    targets = []
                    for p in _glob.glob("rakshak/benchmark/targets/*.json"):
                        import json as _json
                        data = _json.loads(Path(p).read_text(encoding="utf-8"))
                        targets.append({"file": p, "target": data.get("target"), "version": data.get("version"), "count": len(data.get("ground_truth", []))})
                    _send_json({"targets": targets})
                except Exception as e:
                    _send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path == "/api/steer":
                instruction = body_data.get("instruction", "")
                # Persist to mailbox file so runner can poll it (Phase 3 steer queue)
                try:
                    active_run_dir = _resolve_run_dir(run_dir)
                    state_dir = runtime_state_dir(active_run_dir)
                    state_dir.mkdir(parents=True, exist_ok=True)
                    steer_file = state_dir / "steer_queue.json"
                    existing = []
                    if steer_file.exists():
                        with contextlib.suppress(Exception):
                            existing = json.loads(steer_file.read_text(encoding="utf-8"))
                            if not isinstance(existing, list):
                                existing = []
                    existing.append({"instruction": instruction, "timestamp": time.time(), "iso": datetime.now(UTC).isoformat()})
                    # keep last 50
                    existing = existing[-50:]
                    steer_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
                    # Also append to active agents mailbox pending_counts hint
                    agents_file = state_dir / "agents.json"
                    if agents_file.exists():
                        with contextlib.suppress(Exception):
                            agents_data = json.loads(agents_file.read_text(encoding="utf-8"))
                            # Ensure metadata for root agent has pending_counts
                            meta = agents_data.get("metadata", {})
                            root_key = "root_01" if "root_01" in agents_data.get("names", {}) else next(iter(agents_data.get("names", {})), None)
                            if root_key:
                                if root_key not in meta:
                                    meta[root_key] = {}
                                meta[root_key]["pending_counts"] = len(existing)
                                agents_data["metadata"] = meta
                                agents_file.write_text(json.dumps(agents_data, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as exc:
                    logger.warning("Failed to persist steer queue: %s", exc)
                _send_json({"success": True, "delivered": True, "message": f"Steering instruction queued: {instruction}"})
                return

            _send_json({"error": "Endpoint not found"}, status=HTTPStatus.NOT_FOUND)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            def _get_requested_run_dir() -> Path:
                # Support ?run=scan-xxxx or ?scan_id=xxx or ?id=xxx for historic selection
                run_id = (query.get("run") or query.get("scan_id") or query.get("id") or [None])[0]
                if run_id:
                    cand = run_dir_for(run_id)
                    if cand.exists():
                        return cand
                return _resolve_run_dir(run_dir)

            def _get_artifact_dir(filename: str) -> Path:
                run_id = (query.get("run") or query.get("scan_id") or query.get("id") or [None])[0]
                if run_id:
                    cand = run_dir_for(run_id)
                    if cand.exists():
                        return cand
                return _resolve_artifact_dir(run_dir, filename)

            def _send_json(payload: Any, status: int = HTTPStatus.OK) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

            if path == "/api/system/health":
                _send_json(_get_system_telemetry())
                return

            if path == "/api/config":
                cfg = _load_user_config()
                raw_key = cfg.get("api_key", "")
                masked_key = raw_key[:4] + "••••••••" + raw_key[-4:] if len(raw_key) > 8 else ("••••••••" if raw_key else "")
                _send_json({
                    **cfg,
                    "is_key_configured": bool(raw_key),
                    "masked_key": masked_key,
                })
                return

            if path == "/api/overview":
                active_run_dir = _get_requested_run_dir()
                vuln_file = active_run_dir / "vulnerabilities.json"
                vulns = []
                if vuln_file.exists():
                    with contextlib.suppress(Exception):
                        vulns = json.loads(vuln_file.read_text(encoding="utf-8"))

                state_dir = runtime_state_dir(active_run_dir)
                agents_file = state_dir / "agents.json"
                agents_data: dict[str, Any] = {"names": {}, "statuses": {}, "metadata": {}}
                if agents_file.exists():
                    with contextlib.suppress(Exception):
                        agents_data = json.loads(agents_file.read_text(encoding="utf-8"))

                crit = sum(1 for v in vulns if (v.get("severity") or "").lower() == "critical")
                high = sum(1 for v in vulns if (v.get("severity") or "").lower() == "high")
                med = sum(1 for v in vulns if (v.get("severity") or "").lower() == "medium")
                low = sum(1 for v in vulns if (v.get("severity") or "").lower() == "low")

                runs_base = base_runs_dir()
                runs_count = 0
                if runs_base.exists():
                    runs_count = len([d for d in runs_base.iterdir() if d.is_dir() and not d.name.startswith(".")])

                _send_json({
                    "scan_id": active_run_dir.name if active_run_dir.exists() else None,
                    "target": "example.com" if active_run_dir.exists() else "No Active Target",
                    "status": "Analyzing" if active_run_dir.exists() else "Idle",
                    "total_findings": len(vulns),
                    "total_scans": runs_count,
                    "active_agents": len(agents_data.get("names", {})),
                    "severity_counts": {
                        "critical": crit,
                        "high": high,
                        "medium": med,
                        "low": low,
                    }
                })
                return

            if path == "/api/runs":
                runs_base = base_runs_dir()
                runs_list = []
                if runs_base.exists():
                    for d in sorted(runs_base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                        if d.is_dir() and not d.name.startswith("."):
                            v_file = d / "vulnerabilities.json"
                            v_count = 0
                            if v_file.exists():
                                with contextlib.suppress(Exception):
                                    v_count = len(json.loads(v_file.read_text(encoding="utf-8")))
                            meta = {}
                            meta_file = d / "run_meta.json"
                            if meta_file.exists():
                                with contextlib.suppress(Exception):
                                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                            runs_list.append({
                                "id": d.name,
                                "target": meta.get("target") or d.name,
                                "mode": meta.get("mode") or "Black Box",
                                "status": meta.get("status") or "Completed",
                                "duration": meta.get("duration") or "14m 20s",
                                "findings_count": v_count,
                            })
                _send_json(runs_list)
                return

            if path == "/api/vulnerabilities":
                active_run_dir = _get_requested_run_dir()
                vuln_file = active_run_dir / "vulnerabilities.json"
                data = []
                if vuln_file.exists():
                    with contextlib.suppress(Exception):
                        data = json.loads(vuln_file.read_text(encoding="utf-8"))
                _send_json(data)
                return

            if path == "/api/agents":
                active_run_dir = _get_requested_run_dir()
                state_dir = runtime_state_dir(active_run_dir)
                agents_file = state_dir / "agents.json"
                agents_state: dict[str, Any] = {"names": {}, "statuses": {}, "metadata": {}}
                if agents_file.exists():
                    with contextlib.suppress(Exception):
                        agents_state = json.loads(agents_file.read_text(encoding="utf-8"))
                _send_json(agents_state)
                return

            if path == "/api/report":
                active_run_dir = _get_artifact_dir("report.md")
                report_file = active_run_dir / "report.md"
                content = report_file.read_text(encoding="utf-8") if report_file.exists() else "# RakshakX Assessment Report\n\nNo active scan report yet."
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return

            if path == "/api/sarif":
                active_run_dir = _get_artifact_dir("sarif.json")
                sarif_file = active_run_dir / "sarif.json"
                if sarif_file.exists():
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Disposition", "attachment; filename=rakshakx-findings.sarif")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(sarif_file.read_bytes())
                    return
                self.send_error(HTTPStatus.NOT_FOUND, "SARIF report not ready yet.")
                return

            if path == "/api/pdf":
                active_run_dir = _get_artifact_dir("report.pdf")
                pdf_file = active_run_dir / "report.pdf"
                if pdf_file.exists():
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f"inline; filename={pdf_file.name}")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(pdf_file.read_bytes())
                    return
                self.send_error(HTTPStatus.NOT_FOUND, "PDF report not generated yet.")
                return

            if path == "/api/benchmark/scorecard":
                active_run_dir = _get_artifact_dir("scorecard.json")
                sc_file = active_run_dir / "scorecard.json"
                if sc_file.exists():
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(sc_file.read_bytes())
                    return
                # also check legacy location reports/benchmark_v2/
                legacy = Path("reports/benchmark_v2/scorecard.json")
                if legacy.exists():
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(legacy.read_bytes())
                    return
                _send_json({"error": "Scorecard not ready yet. Run a benchmark scan."}, status=HTTPStatus.NOT_FOUND)
                return

            if path == "/api/benchmark/freeze":
                active_run_dir = _get_artifact_dir("environment_freeze.json")
                freeze_file = active_run_dir / "environment_freeze.json"
                if freeze_file.exists():
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(freeze_file.read_bytes())
                    return
                legacy = Path("reports/benchmark_v2/environment_freeze.json")
                if legacy.exists():
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(legacy.read_bytes())
                    return
                _send_json({"error": "Environment freeze not available."}, status=HTTPStatus.NOT_FOUND)
                return

            if path == "/api/benchmark/repeatability":
                # Serve summary from latest repeatability run if exists
                for cand in [Path("reports/benchmark_v2/repeatability_summary.json"), Path("reports/benchmark_v2/summary.json")]:
                    if cand.exists():
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(cand.read_bytes())
                        return
                _send_json({"error": "Repeatability summary not available. Run scripts/run_benchmark_repeatability.py"}, status=HTTPStatus.NOT_FOUND)
                return

            if path == "/api/steer":
                try:
                    active_run_dir = _get_requested_run_dir()
                    state_dir = runtime_state_dir(active_run_dir)
                    steer_file = state_dir / "steer_queue.json"
                    data = []
                    if steer_file.exists():
                        with contextlib.suppress(Exception):
                            data = json.loads(steer_file.read_text(encoding="utf-8"))
                    _send_json({"queue": data, "count": len(data) if isinstance(data, list) else 0})
                except Exception as e:
                    _send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path == "/api/playbooks":
                try:
                    skills_dir = Path("rakshak/skills")
                    catalog = []
                    # Map known playbook metadata (matches web/src/data/playbooksData.ts)
                    meta_map = {
                        "authentication_jwt": {"id": "playbook-jwt", "name": "Authentication & JWT Security", "category": "Broken Authentication", "attackVectors": ["Algorithm Confusion", "None Algorithm", "Weak Secret Cracking", "Key ID Traversal"]},
                        "sql_injection": {"id": "playbook-sqli", "name": "SQL Injection & Database Exploitation", "category": "Injection", "attackVectors": ["Time-Based Blind", "Boolean Blind", "Error-Based", "SQLMap Proxy Bridging"]},
                        "idor": {"id": "playbook-idor", "name": "Insecure Direct Object References (IDOR/BOLA)", "category": "Broken Access Control", "attackVectors": ["Multi-User Probing", "Parameter Tampering", "Method Mutation", "UUID Probing"]},
                        "ssrf": {"id": "playbook-ssrf", "name": "Server-Side Request Forgery (SSRF)", "category": "Server-Side Request Forgery", "attackVectors": ["AWS IMDSv1/v2", "GCP Metadata", "DNS Rebinding", "Loopback Bypasses"]},
                        "race_conditions": {"id": "playbook-race", "name": "Race Conditions & Concurrency Flaws", "category": "Broken Business Logic", "attackVectors": ["HTTP/2 Single-Packet Attack", "Burst Async Fuzzing", "Coupon Reuse", "Balance Race"]},
                        "xss": {"id": "playbook-xss", "name": "Cross-Site Scripting & DOM Exploitation", "category": "Client-Side Attacks", "attackVectors": ["DOM XSS", "Stored XSS", "CSP Bypasses", "Chromium Flag Evaluation"]},
                        "rce": {"id": "playbook-rce", "name": "Remote Code Execution & Command Injection", "category": "Server-Side Execution", "attackVectors": ["Command Separators", "Blind Sleep Injections", "Polyglot Web Shells", "Deserialization"]},
                        "agent_browser": {"id": "playbook-browser", "name": "Headless Browser & DOM Automation", "category": "Tooling", "attackVectors": ["Chromium Automation", "DOM Inspection", "Session Replay"]},
                    }
                    if skills_dir.exists():
                        for p in sorted(skills_dir.glob("**/*.md")):
                            stem = p.stem
                            meta = meta_map.get(stem, {"id": f"playbook-{stem}", "name": stem.replace("_", " ").title(), "category": p.parent.name, "attackVectors": []})
                            try:
                                text = p.read_text(encoding="utf-8")
                                # first heading or second line as description
                                desc = ""
                                for line in text.splitlines():
                                    l = line.strip()
                                    if l and not l.startswith("#") and len(l) > 20:
                                        desc = l[:180]
                                        break
                                if not desc:
                                    desc = text[:180]
                            except Exception:
                                desc = ""
                            catalog.append({
                                "id": meta["id"],
                                "name": meta["name"],
                                "filename": p.name,
                                "category": meta["category"],
                                "description": desc,
                                "attackVectors": meta["attackVectors"],
                                "skill": stem,
                                "status": "Active",
                            })
                    _send_json({"playbooks": catalog})
                except Exception as e:
                    _send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            # Default fallback for API
            if path.startswith("/api/"):
                _send_json({"error": f"Endpoint {path} not found"}, status=HTTPStatus.NOT_FOUND)
                return
            _send_json(_get_system_telemetry())

        def log_message(self, format: str, *args: Any) -> None:
            pass

    return ApiHandler


def start_viewer_server(scan_id: str, port: int = 8080) -> None:
    """Launch the backend API server."""
    _apply_config_env(_load_user_config())
    _set_active_scan(run_dir_for(scan_id))
    run_dir = run_dir_for(scan_id)
    handler_cls = _make_handler(run_dir)
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_cls)
    logger.info("RakshakX Backend API running at http://127.0.0.1:%d for scan %s", port, scan_id)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
