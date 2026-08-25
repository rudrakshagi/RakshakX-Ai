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
    """Build capped model settings to stay within low-budget provider rate limits."""
    kwargs: dict[str, Any] = {}
    temperature = getattr(settings.llm, "temperature", None)
    if temperature is not None:
        kwargs["temperature"] = temperature
    reasoning_effort = getattr(settings.llm, "reasoning_effort", None)
    if reasoning_effort:
        kwargs["extra_body"] = {"reasoning_effort": reasoning_effort}
    try:
        import importlib.util

        if (
            importlib.util.find_spec("agents.extensions.models.litellm_model") is not None
            and getattr(settings.llm, "model", "").startswith("groq/")
        ):
            kwargs["max_tokens"] = 4096
    except (ImportError, ModuleNotFoundError):
        pass
    return ModelSettings(**kwargs)


async def run_rakshak_scan(
    *,
    target: str,
    scan_id: str | None = None,
    scan_mode: str = "deep",
    is_whitebox: bool = False,
    local_sources: list[dict[str, Any]] | None = None,
    max_budget_usd: float | None = None,
    max_turns: int = 150,
) -> Any:
    """Execute an autonomous end-to-end penetration testing assessment."""
    if scan_id is None:
        scan_id = f"scan-{uuid.uuid4().hex[:8]}"

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
        )

        hooks = ReportUsageHooks(
            model=resolved_model,
            max_budget_usd=max_budget_usd,
            max_turns=max_turns,
        )

        # Build Root Orchestrator
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
                **kwargs,
            )

        context: dict[str, Any] = {
            "coordinator": coordinator,
            "sandbox_session": bundle.session,
            "caido_client": bundle.caido_client,
            "agent_id": root_id,
            "parent_id": None,
            "spawn_child_agent": spawn_child,
        }

        root_session = open_agent_session(root_id, agents_db)
        sessions_to_close.append(root_session)
        await coordinator.attach_runtime(root_id, session=root_session)

        initial_input = [{
            "role": "user",
            "content": f"Begin penetration test against target: {target}. Explore scope, discover attack surface, and validate vulnerabilities.",
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
        for s in sessions_to_close:
            with contextlib.suppress(Exception):
                s.close()
        await session_manager.cleanup(scan_id)
        logger.info("RakshakX Scan %s completed.", scan_id)
