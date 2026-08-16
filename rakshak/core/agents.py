"""Master Agent Coordinator for the multi-agent graph."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from rakshak.core.sessions import session_write_lock

if TYPE_CHECKING:
    from agents.items import TResponseInputItem
    from agents.memory import Session

logger = logging.getLogger(__name__)

Status = Literal[
    "running",
    "waiting",
    "completed",
    "stopped",
    "crashed",
    "failed",
    "budget_paused",
]

WaitKind = Literal["user", "agents", "stalled"]


@dataclass(slots=True)
class AgentRuntime:
    """Live async execution state, mailbox, and signaling handles for an agent."""
    session: Session | None = None
    task: asyncio.Task[Any] | None = None
    stream: Any | None = None
    interrupt_on_message: bool = False
    wake: asyncio.Event = field(default_factory=asyncio.Event)
    mailbox: list[dict[str, Any]] = field(default_factory=list)
    user_wake_required: bool = False


class AgentCoordinator:
    """Central orchestrator managing the multi-agent hierarchy, mailboxes, and resume snapshots."""

    def __init__(self) -> None:
        self.statuses: dict[str, Status] = {}
        self.parent_of: dict[str, str | None] = {}
        self.names: dict[str, str] = {}
        self.metadata: dict[str, dict[str, Any]] = {}
        self.pending_counts: dict[str, int] = {}
        self.errors: dict[str, str] = {}
        self.recovery_counts: dict[str, int] = {}
        self.idle_resume_counts: dict[str, int] = {}
        self.wait_kinds: dict[str, WaitKind] = {}
        self.runtimes: dict[str, AgentRuntime] = {}
        self._parent_notified: set[str] = set()
        self._lock = asyncio.Lock()
        self._snapshot_path: Path | None = None
        self.is_shutting_down = False
        self._budget_stopped = False
        self._reserve_stopped = False
        self._budget_paused = False
        self._extend_budget: Callable[[], None] | None = None

    def set_snapshot_path(self, path: Path) -> None:
        self._snapshot_path = path

    def mark_shutting_down(self) -> None:
        self.is_shutting_down = True

    @property
    def budget_stopped(self) -> bool:
        return self._budget_stopped

    @property
    def reserve_stopped(self) -> bool:
        return self._reserve_stopped

    @property
    def budget_paused(self) -> bool:
        return self._budget_paused

    def set_budget_extender(self, extend: Callable[[], None]) -> None:
        self._extend_budget = extend

    async def trigger_budget_stop(self) -> None:
        """Wake all agents and signal a scan-wide stop when budget limit is breached."""
        async with self._lock:
            self._budget_stopped = True
            for runtime in self.runtimes.values():
                runtime.wake.set()

    async def register(
        self,
        agent_id: str,
        name: str,
        parent_id: str | None,
        *,
        task: str | None = None,
        skills: list[str] | None = None,
    ) -> None:
        """Register a new root or child agent into the graph."""
        async with self._lock:
            self.statuses[agent_id] = "running"
            self.parent_of[agent_id] = parent_id
            self.names[agent_id] = name
            self.pending_counts.setdefault(agent_id, 0)
            self.metadata[agent_id] = {
                "task": task or "",
                "skills": list(skills or []),
            }
            self.runtimes.setdefault(agent_id, AgentRuntime())
        logger.info("Registered agent %s (%s), parent=%s", agent_id, name, parent_id or "ROOT")
        await self._maybe_snapshot()

    async def attach_runtime(
        self,
        agent_id: str,
        *,
        session: Session | None = None,
        task: asyncio.Task[Any] | None = None,
        interrupt_on_message: bool | None = None,
    ) -> None:
        """Bind live SDK session and asyncio task to the registered agent."""
        async with self._lock:
            runtime = self.runtimes.setdefault(agent_id, AgentRuntime())
            if session is not None:
                runtime.session = session
            if task is not None:
                runtime.task = task
            if interrupt_on_message is not None:
                runtime.interrupt_on_message = interrupt_on_message

    async def mark_running(self, agent_id: str) -> None:
        async with self._lock:
            if agent_id in self.statuses:
                self.statuses[agent_id] = "running"
                self.errors.pop(agent_id, None)
                self.wait_kinds.pop(agent_id, None)
                self.runtimes.setdefault(agent_id, AgentRuntime()).user_wake_required = False
                self._parent_notified.discard(agent_id)
        await self._maybe_snapshot()

    async def park_waiting(self, agent_id: str, *, wait_kind: WaitKind) -> None:
        """Park an agent turn while waiting for child completion or user response."""
        async with self._lock:
            if agent_id in self.statuses:
                self.wait_kinds[agent_id] = wait_kind
        await self.set_status(agent_id, "waiting")

    async def set_status(
        self,
        agent_id: str,
        status: Status,
        *,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            if agent_id not in self.statuses:
                return
            self.statuses[agent_id] = status
            if error is not None:
                self.errors[agent_id] = error
            elif status == "running":
                self.errors.pop(agent_id, None)
            runtime = self.runtimes.setdefault(agent_id, AgentRuntime())
            runtime.user_wake_required = status in {"failed", "crashed"}
            runtime.wake.set()
        logger.info("Agent %s status updated -> %s", agent_id, status)
        await self._maybe_snapshot()

    async def claim_parent_notice(self, agent_id: str) -> bool:
        """Ensure only one completion report or terminal notice is sent to parent."""
        async with self._lock:
            if agent_id in self._parent_notified:
                return False
            self._parent_notified.add(agent_id)
            return True

    async def send(
        self,
        target_agent_id: str,
        message: dict[str, Any],
        *,
        interrupt: bool = True,
    ) -> bool:
        """Deliver a message to target agent's mailbox and trigger immediate wake/interrupt."""
        async with self._lock:
            if target_agent_id not in self.statuses:
                logger.warning("Attempted to send message to unknown agent: %s", target_agent_id)
                return False
            runtime = self.runtimes.setdefault(target_agent_id, AgentRuntime())
            runtime.mailbox.append(dict(message))
            self.pending_counts[target_agent_id] = self.pending_counts.get(target_agent_id, 0) + 1
            if message.get("from") == "user":
                runtime.user_wake_required = False
            runtime.wake.set()
            stream = runtime.stream
            interrupt_on_message = runtime.interrupt_on_message

        # If target agent is in the middle of streaming a turn, interrupt it immediately
        # so it consumes this high-priority message on the next turn cycle
        if stream is not None and interrupt and interrupt_on_message:
            try:
                stream.cancel(mode="immediate")
            except Exception:
                pass

        await self._maybe_snapshot()
        return True

    async def wait_for_message(self, agent_id: str, *, timeout: float | None = None) -> bool:
        """Block until a message is received in the agent's mailbox."""
        while True:
            async with self._lock:
                runtime = self.runtimes.setdefault(agent_id, AgentRuntime())
                if self._budget_stopped or (self.pending_counts.get(agent_id, 0) > 0 and not runtime.user_wake_required):
                    return True
                wake = runtime.wake
                wake.clear()

            if timeout is None:
                await wake.wait()
            else:
                try:
                    await asyncio.wait_for(wake.wait(), timeout)
                except TimeoutError:
                    return False

    async def consume_pending(
        self,
        agent_id: str,
        *,
        include_items: bool = False,
    ) -> tuple[int, list[Any]]:
        """Drain the agent's mailbox into its active SQLite session items."""
        async with self._lock:
            runtime = self.runtimes.setdefault(agent_id, AgentRuntime())
            queued = list(runtime.mailbox)
            runtime.mailbox.clear()
            count = max(self.pending_counts.get(agent_id, 0), len(queued))
            self.pending_counts[agent_id] = 0
            session = runtime.session

        if count <= 0:
            return 0, []

        items = [self._message_to_session_item(m) for m in queued]
        if items and session is not None:
            try:
                async with session_write_lock(session):
                    await session.add_items(items)
            except Exception:
                logger.exception("Failed to append queued mailbox messages to session for %s", agent_id)

        await self._maybe_snapshot()
        return count, items if include_items else []

    def _message_to_session_item(self, message: dict[str, Any]) -> TResponseInputItem:
        sender = str(message.get("from", "unknown"))
        content = str(message.get("content", ""))
        if sender == "user":
            return cast("TResponseInputItem", {"role": "user", "content": content})
        sender_name = self.names.get(sender, sender)
        msg_type = message.get("type", "information")
        priority = message.get("priority", "normal")
        formatted = f"[Message from {sender_name} ({sender}) | type={msg_type} | priority={priority}]\n{content}"
        return cast("TResponseInputItem", {"role": "user", "content": formatted})

    async def cancel_descendants(self, agent_id: str) -> None:
        """Cancel all subagent tasks under the given agent."""
        tasks: list[asyncio.Task[Any]] = []
        async with self._lock:
            for aid in reversed(self._subtree_order_locked(agent_id)):
                t = self.runtimes.get(aid, AgentRuntime()).task
                if t is not None and not t.done():
                    tasks.append(t)
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _subtree_order_locked(self, agent_id: str) -> list[str]:
        queue = [agent_id]
        order: list[str] = []
        while queue:
            aid = queue.pop()
            order.append(aid)
            queue.extend(child for child, parent in self.parent_of.items() if parent == aid)
        return order

    async def graph_snapshot(
        self,
    ) -> tuple[dict[str, str | None], dict[str, Status], dict[str, str], dict[str, str]]:
        async with self._lock:
            return (
                dict(self.parent_of),
                dict(self.statuses),
                dict(self.names),
                dict(self.errors),
            )

    async def snapshot(self) -> dict[str, Any]:
        """Serialize current state for disk snapshotting."""
        async with self._lock:
            return {
                "statuses": dict(self.statuses),
                "parent_of": dict(self.parent_of),
                "names": dict(self.names),
                "metadata": {aid: dict(md) for aid, md in self.metadata.items()},
                "pending_counts": dict(self.pending_counts),
                "recovery_counts": dict(self.recovery_counts),
                "idle_resume_counts": dict(self.idle_resume_counts),
                "wait_kinds": dict(self.wait_kinds),
                "errors": dict(self.errors),
                "budget_stopped": self._budget_stopped,
                "reserve_stopped": self._reserve_stopped,
                "budget_paused": self._budget_paused,
            }

    async def restore(self, snap: dict[str, Any]) -> None:
        """Restore graph state from a persisted snapshot dictionary."""
        async with self._lock:
            self.statuses = dict(snap.get("statuses", {}))
            self.parent_of = dict(snap.get("parent_of", {}))
            self.names = dict(snap.get("names", {}))
            self.metadata = {aid: dict(md) for aid, md in snap.get("metadata", {}).items()}
            self.pending_counts = dict(snap.get("pending_counts", {}))
            self.errors = dict(snap.get("errors", {}))
            self.recovery_counts = dict(snap.get("recovery_counts", {}))
            self.idle_resume_counts = dict(snap.get("idle_resume_counts", {}))
            self.wait_kinds = dict(snap.get("wait_kinds", {}))
            self._budget_stopped = bool(snap.get("budget_stopped", False))
            self._reserve_stopped = bool(snap.get("reserve_stopped", False))
            self._budget_paused = bool(snap.get("budget_paused", False))
            for aid in self.statuses:
                self.runtimes.setdefault(aid, AgentRuntime())

    async def _maybe_snapshot(self) -> None:
        """Atomically persist state to disk via temporary file swap."""
        path = self._snapshot_path
        if path is None:
            return
        try:
            data = await self.snapshot()
            payload = json.dumps(data, ensure_ascii=False, default=str, indent=2)
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(path.parent),
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(payload)
                tmp_path = Path(tmp.name)
            tmp_path.replace(path)
        except Exception:
            logger.exception("Failed to write coordinator snapshot to %s", path)


def coordinator_from_context(ctx: dict[str, Any]) -> AgentCoordinator | None:
    """Extract the AgentCoordinator instance from the runner context dictionary."""
    coord = ctx.get("coordinator")
    return coord if isinstance(coord, AgentCoordinator) else None
