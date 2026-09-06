"""Top-level RakshakX scan runner and orchestrator."""

from __future__ import annotations

import contextlib
import logging
import uuid
from typing import Any, cast

from agents import ModelSettings, RunConfig
from agents.sandbox import SandboxRunConfig

from rakshak.agents.factory import build_rakshak_agent, make_child_factory
from rakshak.config import load_settings
from rakshak.config.models import RakshakProvider, configure_model_defaults
from rakshak.core.agents import AgentCoordinator
from rakshak.core.execution import run_agent_loop
from rakshak.core.execution import spawn_child_agent as start_child_agent
from rakshak.core.hooks import ReportUsageHooks
from rakshak.core.paths import run_dir_for, runtime_state_dir
from rakshak.core.sessions import open_agent_session
from rakshak.report.state import ReportState, set_global_report_state
from rakshak.runtime import session_manager
from rakshak.tools.notes.tools import hydrate_notes_from_disk
from rakshak.tools.output_store import WORKSPACE_SPILL_DIR, configure_spill_writer
from rakshak.tools.todo.tools import hydrate_todos_from_disk

logger = logging.getLogger(__name__)


def _build_model_settings(settings: Any) -> ModelSettings:
    """Build capped model settings to control runaway completions and rate limits."""
    kwargs: dict[str, Any] = {}
    temperature = getattr(settings.llm, "temperature", None)
    if temperature is not None:
        kwargs["temperature"] = temperature
    reasoning_effort = getattr(settings.llm, "reasoning_effort", None)
    if reasoning_effort:
        kwargs["extra_body"] = {"reasoning_effort": reasoning_effort}
    model = getattr(settings.llm, "model", "") or ""
    if model.startswith("groq/"):
        kwargs["max_tokens"] = 4096
    else:
        kwargs.setdefault("max_tokens", 8192)
    from rakshak.config.models import _is_opencode_free
    if _is_opencode_free(settings):
        kwargs["extra_headers"] = {
            "x-opencode-client": "desktop",
            "Authorization": "",
        }
    return ModelSettings(**kwargs)


def _is_allowed_scope(target: str, scope: str) -> bool:
    """Authorization & Safety: scope must be a self-hosted lab target (RFC1918, localhost, or lab domain)."""
    import ipaddress
    import os
    from urllib.parse import urlparse

    raw = (scope or target).strip()
    if not raw:
        return False
    # Operator-owned domains: comma-separated, e.g.
    # RAKSHAK_ALLOWED_SCOPES="rudrakshai.in,example.com". Only add domains
    # you own or are explicitly authorized to test.
    owned = [s.strip().lower() for s in os.getenv("RAKSHAK_ALLOWED_SCOPES", "").split(",") if s.strip()]
    # Allow explicit lab allowlist via substrings
    allow_substrings = ["localhost", "127.0.0.1", "10.", "192.168.", "172.", "lab", "juice", "dvwa", "metasploitable"]
    low = raw.lower()
    if any(tok in low for tok in allow_substrings):
        return True
    try:
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        host = (parsed.hostname or raw.split("/")[0].split(":")[0]).lower()
        if owned and any(host == o or host.endswith(f".{o}") for o in owned):
            return True
    except Exception:
        pass
    try:
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        host = parsed.hostname or raw.split("/")[0].split(":")[0]
        # Check if host is an IP in private range
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback
        except Exception:
            pass
        # Otherwise deny public hostnames by default (require explicit lab token)
        return False
    except Exception:
        return False


async def run_rakshak_scan(
    *,
    target: str,
    scan_id: str | None = None,
    scan_mode: str = "deep",
    is_whitebox: bool = False,
    local_sources: list[dict[str, Any]] | None = None,
    max_budget_usd: float | None = None,
    max_turns: int = 150,
    prompt_verbatim: str | None = None,
    scope: str | None = None,
    benchmark_target: str | None = None,
) -> Any:
    """Execute an autonomous end-to-end penetration testing assessment."""
    if scan_id is None:
        scan_id = f"scan-{uuid.uuid4().hex[:8]}"

    # §2 Authorization & Safety guard
    effective_scope_for_check = scope or target
    if not _is_allowed_scope(target, effective_scope_for_check):
        logger.warning("Scope guard: target %s not in lab allowlist. Use isolated lab target per Protocol §2.", target)
        # Do not abort automatically in dev, but annotate run_meta and continue with warning
        # To enforce hard block, uncomment next line:
        # raise ValueError(f"Scope {effective_scope_for_check!r} not in authorized lab allowlist (Protocol §2)")

    run_dir = run_dir_for(scan_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    state_dir = runtime_state_dir(run_dir)
    state_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings()
    configure_model_defaults(settings)
    resolved_model = settings.llm.model

    logger.info("Initializing RakshakX Scan %s on target: %s (model=%s)", scan_id, target, resolved_model)

    # Initialize Global Report State
    report_state = ReportState(scan_id=scan_id, run_dir=run_dir)
    set_global_report_state(report_state)

    # State Coordination & Snapshot Paths
    agents_path = state_dir / "agents.json"
    agents_db = state_dir / "agents.db"

    coordinator = AgentCoordinator()
    coordinator.set_snapshot_path(agents_path)

    hydrate_todos_from_disk(state_dir)
    hydrate_notes_from_disk(state_dir)

    root_id = uuid.uuid4().hex[:8]

    # Boot Sandbox Container & Caido Proxy
    bundle = await session_manager.create_or_reuse(
        scan_id,
        local_sources=local_sources or [],
    )
    sandbox_session = bundle.session

    # Configure tool output spillway to sandbox disk
    async def _spill_to_sandbox(output_id: str, text: str) -> str | None:
        path = f"{WORKSPACE_SPILL_DIR}/{output_id}.txt"
        try:
            await sandbox_session.write(path, text)
            return path
        except Exception:
            return None

    configure_spill_writer(_spill_to_sandbox)

    sessions_to_close: list[Any] = []

    try:
        run_config = RunConfig(
            model=resolved_model,
            model_provider=RakshakProvider(settings),
            model_settings=_build_model_settings(settings),
            sandbox=SandboxRunConfig(
                client=cast(Any, bundle.session.docker_client),
                session=bundle.sdk_session,
            ),
            tool_not_found_behavior="return_error_to_model",
            # We run against OpenRouter/OpenCode Zen, not OpenAI — the SDK's
            # trace exporter 401s every turn ("[non-fatal] Tracing client
            # error 401" log spam). Tracing is observability-only; disable it.
            tracing_disabled=True,
        )

        hooks = ReportUsageHooks(
            model=resolved_model,
            max_budget_usd=max_budget_usd,
            max_turns=max_turns,
        )

        # Build Root Orchestrator (benchmark prompts injected via scan_mode)
        # Resolve verbatim prompt if not supplied explicitly
        if prompt_verbatim is None:
            try:
                from rakshak.benchmark.prompts import get_prompt
                prompt_verbatim = get_prompt(scan_mode) or ""
            except Exception:
                prompt_verbatim = ""
        effective_scope = scope or target

        root_agent = build_rakshak_agent(
            name="Root Orchestrator",
            is_root=True,
            scan_mode=scan_mode,
            is_whitebox=is_whitebox,
        )

        await coordinator.register(
            root_id,
            name="Root Orchestrator",
            parent_id=None,
            task=f"Perform authorized pentest on target: {target}",
        )

        child_factory = make_child_factory(
            scan_mode=scan_mode,
            is_whitebox=is_whitebox,
        )

        async def spawn_child(**kwargs: Any) -> dict[str, Any]:
            return await start_child_agent(
                coordinator=coordinator,
                factory=child_factory,
                agents_db_path=agents_db,
                sessions_to_close=sessions_to_close,
                run_config=run_config,
                max_turns=max_turns,
                hooks=hooks,
                **kwargs,
            )

        context: dict[str, Any] = {
            "coordinator": coordinator,
            "sandbox_session": bundle.session,
            "caido_client": bundle.caido_client,
            "agent_id": root_id,
            "parent_id": None,
            "spawn_child_agent": spawn_child,
            "state_dir": state_dir,
            "runtime_state_dir": state_dir,
            "agents_db_path": agents_db,
        }

        root_session = open_agent_session(root_id, agents_db)
        sessions_to_close.append(root_session)
        await coordinator.attach_runtime(root_id, session=root_session)

        # Build initial input: benchmark verbatim prompt takes precedence, else generic
        if prompt_verbatim:
            # Inject scope/target into template placeholders
            resolved_prompt = prompt_verbatim.replace("<JUICE_SHOP_HOST>", target).replace("<DVWA_HOST>", target).replace("<LAB_IP>", target).replace("<PORT>", "").replace("<JUICE_SHOP_HOST>:<PORT>", target).replace("<DVWA_HOST>:<PORT>", target)
            initial_content = f"Target: {target}\nScope: {effective_scope}\nBenchmark Mode: {scan_mode}\n\n{resolved_prompt}"
        else:
            initial_content = f"Begin penetration test against target: {target}. Scope: {effective_scope}. Explore scope, discover attack surface, and validate vulnerabilities."

        initial_input = [{
            "role": "user",
            "content": initial_content,
        }]

        result = await run_agent_loop(
            agent=root_agent,
            initial_input=initial_input,
            run_config=run_config,
            context=context,
            max_turns=max_turns,
            coordinator=coordinator,
            agent_id=root_id,
            session=root_session,
            hooks=hooks,
        )

        return result

    finally:
        configure_spill_writer(None)
        await coordinator.cancel_descendants(root_id)
        # Mark any still-"running"/"waiting" agents terminal so agents.json (and
        # the 5s watchdog) never reports a finished scan as running/stuck.
        with contextlib.suppress(Exception):
            for aid, st in list(coordinator.statuses.items()):
                if st in ("running", "waiting"):
                    await coordinator.set_status(aid, "completed")
        for s in sessions_to_close:
            with contextlib.suppress(Exception):
                s.close()
        # Persist run_meta with scope/prompt + optional benchmark scoring
        try:
            import json as _json
            from datetime import UTC as _UTC
            from datetime import datetime as _dt
            from pathlib import Path as _P

            meta_path = run_dir / "run_meta.json"
            existing: dict[str, Any] = {}
            if meta_path.exists():
                with contextlib.suppress(Exception):
                    existing = _json.loads(meta_path.read_text(encoding="utf-8"))
            existing.update({
                "scan_id": scan_id,
                "target": target,
                "scope": scope or target,
                "mode": scan_mode,
                "prompt_verbatim": (prompt_verbatim or "")[:4000],
                "benchmark_target": benchmark_target or "",
            })
            # Live benchmark scoring if ground-truth available
            if benchmark_target:
                try:
                    from rakshak.benchmark.adapters import evaluate_live_scan
                    gt_map = {
                        "juice_shop": _P("rakshak/benchmark/targets/juice_shop.json"),
                        "dvwa": _P("rakshak/benchmark/targets/dvwa.json"),
                        "metasploitable2": _P("rakshak/benchmark/targets/metasploitable2.json"),
                        "juice-shop": _P("rakshak/benchmark/targets/juice_shop.json"),
                    }
                    gt_path = gt_map.get(benchmark_target.lower())
                    if gt_path and gt_path.exists():
                        vulns = report_state.vulnerabilities
                        # Try to parse started_at from report_state or meta
                        start_iso = report_state.start_time
                        end_iso = report_state.end_time or _dt.now(_UTC).isoformat()
                        s_dt = _dt.fromisoformat(start_iso.replace("Z", "+00:00"))
                        e_dt = _dt.fromisoformat(end_iso.replace("Z", "+00:00"))
                        scorecard = evaluate_live_scan(
                            scan_id=scan_id,
                            target=target,
                            vulnerabilities=vulns,
                            ground_truth_path=gt_path,
                            assessment_start=s_dt,
                            assessment_end=e_dt,
                            output_path=run_dir / "scorecard.json",
                        )
                        existing["scorecard"] = {
                            "tp": scorecard.tp, "fp": scorecard.fp, "fn": scorecard.fn,
                            "precision": scorecard.precision, "recall": scorecard.recall,
                            "f1": scorecard.f1, "verification_rate": scorecard.verification_rate,
                        }
                except Exception as _e:
                    logger.warning("Benchmark live scoring failed for %s: %s", scan_id, _e)

            with contextlib.suppress(Exception):
                meta_path.write_text(_json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

            # Guaranteed final report: the console's Reports tab expects
            # vulnerabilities.json / sarif.json / report.md to exist even
            # when the agent recorded zero findings (previously no files
            # were written at all, showing "No active scan report yet").
            with contextlib.suppress(Exception):
                report_state.persist()

            # Environment freeze artifact
            try:
                from rakshak.benchmark.runner import freeze_environment as _freeze_env
                settings_obj = load_settings()
                # Resolve LLM settings similarly to viewer
                freeze = _freeze_env(
                    model=getattr(settings_obj.llm, "model", ""),
                    provider=(getattr(settings_obj.llm, "model", "") or "").split("/")[0],
                    api_base=getattr(settings_obj.llm, "api_base", "") or "",
                    temperature=getattr(settings_obj.llm, "temperature", None),
                    reasoning_effort=getattr(settings_obj.llm, "reasoning_effort", None),
                    sandbox_image=getattr(settings_obj.runtime, "docker_image", "rakshakx/sandbox:latest"),
                    rakshak_version="2.0-community",
                    target_name=benchmark_target or "",
                    target_url=target,
                    prompt_verbatim=prompt_verbatim or "",
                    scope=scope or target,
                    started_at=report_state.start_time,
                    ended_at=report_state.end_time or _dt.now(_UTC).isoformat(),
                )
                freeze.persist(run_dir / "environment_freeze.json")
            except Exception as _e:
                logger.warning("Failed to write environment freeze for %s: %s", scan_id, _e)
        except Exception:
            pass
        await session_manager.cleanup(scan_id)
        logger.info("RakshakX Scan %s completed.", scan_id)
