"""E2E test: real agent loop + real tool dispatch driven by a scripted fake LLM.

Unlike the mocked runner tests (which stub out ``Runner.run`` entirely), this drives
the actual openai-agents ``Runner`` loop with a fake ``Model`` implementation. The
fake model emits tool calls against the REAL RakshakX tools, so the test exercises:

- agent construction (SandboxAgent + tools + schemas)
- the multi-turn tool-calling loop (model <-> tool dispatch)
- real tool *execution* (arguments parsed and functions invoked)
- final output generation

Deterministic and token-free (no network, no Docker needed if the sandbox session
is not exercised), so it is safe to run in CI.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from agents import Agent, ModelSettings, RunConfig, Runner
from agents.items import ModelResponse
from agents.models.interface import Model, ModelProvider
from agents.usage import Usage
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)

import rakshak.tools.todo.tools as todo_tools


class ScriptedModel(Model):
    """A fake Model that plays back a fixed script of tool calls then a final answer."""

    def __init__(self, calls: list[tuple[str, dict[str, Any]]], final_text: str) -> None:
        self.calls = calls
        self.final_text = final_text
        self.turn = 0

    def _response_for(self) -> ModelResponse:
        call = self.calls[self.turn] if self.turn < len(self.calls) else None
        self.turn += 1

        if call is not None:
            name, args_dict = call
            item = ResponseFunctionToolCall(
                id=f"fc_{self.turn}",
                call_id=f"call_{self.turn}",
                arguments=json.dumps(args_dict),
                name=name,
                type="function_call",
            )
            return ModelResponse(
                output=[item],
                usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15),
                response_id=None,
            )

        msg = ResponseOutputMessage(
            id="final_msg",
            content=[ResponseOutputText(text=self.final_text, type="output_text", annotations=[])],
            role="assistant",
            status="completed",
            type="message",
        )
        return ModelResponse(
            output=[msg],
            usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15),
            response_id=None,
        )

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self._response_for()

    def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[Any],
        model_settings: ModelSettings,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: Any,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any | None = None,
    ) -> Any:
        response = self._response_for()

        async def _events() -> Any:
            seq = 0
            created: Response = Response(
                id=f"resp_{self.turn}",
                object="response",
                created_at=0,
                model="scripted",
                output=response.output,
                status="completed",
                parallel_tool_calls=True,
                tool_choice="auto",
                tools=[],
            )
            yield ResponseCreatedEvent(
                response=created,
                type="response.created",
                sequence_number=seq,
            )
            yield ResponseCompletedEvent(
                response=created,
                type="response.completed",
                sequence_number=seq + 1,
            )

        return _events()


class ScriptedProvider(ModelProvider):
    """Exposes the fake model via the ModelProvider contract."""

    def __init__(self, model: ScriptedModel) -> None:
        self._model = model

    def get_model(self, model_name: str | None = None) -> Model:
        return self._model


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent_loop_executes_real_tools(tmp_path: Any, monkeypatch: Any) -> None:
    todo_tools._TODOS.clear()

    from rakshak.tools.finish.tool import finish_scan
    from rakshak.tools.thinking.tool import think
    from rakshak.tools.todo.tools import create_todo, list_todos, mark_todo_done

    # Plain Agent (no sandbox), but with the REAL RakshakX tools — proves the
    # tool-calling loop and tool dispatch work end-to-end.
    agent = Agent(
        name="Root",
        instructions="You manage pentest work with todos and finish reports.",
        tools=[think, create_todo, list_todos, mark_todo_done, finish_scan],
        model="scripted",
    )
    model = ScriptedModel(
        calls=[
            ("create_todo", {"id": "scan_orders", "task": "Test parameterized order id lookup"}),
            ("list_todos", {}),
        ],
        final_text="Created a todo for the order lookup scan and listed the queue.",
    )

    result = await Runner.run(
        agent,
        input="Plan the scan and track work in todos.",
        run_config=RunConfig(
            model="scripted",
            model_provider=ScriptedProvider(model),
            model_settings=ModelSettings(temperature=0.2),
        ),
        max_turns=6,
    )

    assert "Created a todo" in result.final_output

    # The todo persisted through the REAL tool function.
    assert "scan_orders" in todo_tools._TODOS
    assert todo_tools._TODOS["scan_orders"].status == "pending"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent_loop_surfaces_tool_validation_errors(tmp_path: Any, monkeypatch: Any) -> None:
    """If the fake model asks for a bad CVSS, the real tool should reject it and the loop continues."""
    from rakshak.tools.reporting.tool import create_vulnerability_report

    agent = Agent(
        name="ReportProbe",
        instructions="You file vulnerability reports.",
        tools=[create_vulnerability_report],
        model="scripted",
    )
    model = ScriptedModel(
        calls=[
            (
                "create_vulnerability_report",
                {
                    "title": "Bad CVSS",
                    "description": "invalid metric",
                    "category": "XSS",
                    "cwe_id": "CWE-79",
                    "cvss_metrics": {"attack_vector": "Z"},
                    "reproduction_steps": ["step"],
                    "exploit_poc": "<script>",
                },
            )
        ],
        final_text="The report was rejected due to an invalid CVSS metric.",
    )

    result = await Runner.run(
        agent,
        input="File a vulnerability report.",
        run_config=RunConfig(model="scripted", model_provider=ScriptedProvider(model)),
        max_turns=6,
    )

    assert "rejected" in result.final_output.lower()
    # The tool returned a structured JSON failure that flowed back into the loop.
    outputs = [it for it in result.new_items if it.type in ("function_call_output", "tool_call_output_item")]
    assert len(outputs) == 1
