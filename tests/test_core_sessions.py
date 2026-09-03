"""Unit tests for SQLite session storage and image budget helpers."""

from __future__ import annotations

import pytest

from rakshak.core.sessions import (
    enforce_image_budget,
    open_agent_session,
    seed_initial_input,
    strip_all_images_from_session,
)


def _img_output() -> dict:
    return {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": [{"type": "input_image", "image_url": "data:image/png;base64,AAA"}],
    }


def _text_output() -> dict:
    return {
        "type": "function_call_output",
        "call_id": "call_2",
        "output": [{"type": "input_text", "text": "plain text"}],
    }


@pytest.mark.asyncio
async def test_seed_initial_input_once(tmp_path):
    session = open_agent_session("a1", tmp_path / "db.sqlite")
    first = await seed_initial_input(session, [{"role": "user", "content": "hello"}])
    second = await seed_initial_input(session, [{"role": "user", "content": "again"}])
    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_seed_empty_input(tmp_path):
    session = open_agent_session("a1", tmp_path / "db.sqlite")
    assert await seed_initial_input(session, []) is False


@pytest.mark.asyncio
async def test_enforce_image_budget_elides_old(tmp_path):
    session = open_agent_session("a1", tmp_path / "db.sqlite")
    items = [{"role": "user", "content": "task"}, _img_output(), _img_output(), _img_output()]
    await session.add_items(items)

    changed = await enforce_image_budget(session, max_images=2)
    assert changed is True

    current = await session.get_items()
    elided = [i for i in current if isinstance(i, dict) and _contains_elided(i)]
    assert len(elided) == 1


def _contains_elided(item: dict) -> bool:
    out = item.get("output")
    if not isinstance(out, list):
        return False
    return any(isinstance(b, dict) and b.get("text") and "elided" in b.get("text", "") for b in out)


@pytest.mark.asyncio
async def test_enforce_image_budget_no_change_under_limit(tmp_path):
    session = open_agent_session("a1", tmp_path / "db.sqlite")
    await session.add_items([_img_output()])
    assert await enforce_image_budget(session, max_images=5) is False


@pytest.mark.asyncio
async def test_strip_all_images(tmp_path):
    session = open_agent_session("a1", tmp_path / "db.sqlite")
    await session.add_items([{"role": "user", "content": "task"}, _img_output(), _text_output()])
    changed = await strip_all_images_from_session(session)
    assert changed is True
    current = await session.get_items()
    text_blocks = [
        item
        for item in current
        if isinstance(item, dict)
        for b in (item.get("output", []) if isinstance(item.get("output"), list) else [])
        if isinstance(b, dict) and b.get("type") == "input_image"
    ]
    assert text_blocks == []
