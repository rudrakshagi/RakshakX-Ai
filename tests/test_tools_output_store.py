"""Unit tests for tool output bounding and spillage store."""

from __future__ import annotations

from rakshak.tools.output_store import bound_text, configure_spill_writer


def test_bound_text_short_unchanged():
    text = "hello world"
    assert bound_text(text) == text


def test_bound_text_empty():
    assert bound_text("") == ""


def test_bound_text_line_cap():
    text = "\n".join(f"line {i}" for i in range(1000))
    out = bound_text(text, max_lines=10, max_bytes=100_000)
    assert "Output truncated" in out
    assert out.count("line ") < 100


def test_bound_text_byte_cap():
    text = "x" * 200_000
    out = bound_text(text, max_lines=500, max_bytes=1000)
    assert "Output truncated" in out
    assert len(out) < 2000


def test_bound_text_token_cap():
    text = "word " * 50_000
    out = bound_text(text, max_lines=500, max_bytes=100_000, max_tokens=100)
    assert "Output truncated" in out


async def test_bound_and_store_spills_to_writer():
    from rakshak.tools.output_store import bound_and_store

    spills: list[tuple[str, str]] = []

    async def writer(output_id: str, text: str):
        spills.append((output_id, text))
        return f"/workspace/.rakshak/spill/{output_id}.txt"

    configure_spill_writer(writer)
    try:
        big = "a" * 200_000
        out = await bound_and_store(big)
        assert "[NOTE: Full output" in out
        assert len(spills) == 1
    finally:
        configure_spill_writer(None)
