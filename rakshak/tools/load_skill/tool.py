"""Dynamic skill playbook loader tool for agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from agents import RunContextWrapper, function_tool

from rakshak.tools.errors import model_failure_message, model_timeout_message

_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


def _find_skill_file(skill_name: str) -> Path | None:
    """Search for skill markdown file across skill categories."""
    clean_name = skill_name.strip().removesuffix(".md")
    for category in ("vulnerabilities", "reconnaissance", "tooling", "protocols"):
        candidate = _SKILLS_DIR / category / f"{clean_name}.md"
        if candidate.exists():
            return candidate
    return None


def _list_all_skills() -> list[str]:
    """Discover all available skill names."""
    if not _SKILLS_DIR.exists():
        return []
    skills = []
    for p in _SKILLS_DIR.glob("**/*.md"):
        skills.append(p.stem)
    return sorted(skills)


@function_tool(
    timeout=10,
    failure_error_function=model_failure_message,
    timeout_error_function=model_timeout_message,
)
async def load_skill(
    ctx: RunContextWrapper,
    skill_name: Annotated[str, "Skill playbook to load, e.g. 'sql_injection', 'idor', 'ssrf'."],
) -> str:
    """Load specialized offensive methodology and exploit playbook for a vulnerability or tool.

    Examples: 'authentication_jwt', 'idor', 'sql_injection', 'ssrf', 'race_conditions'.
    """
    skill_file = _find_skill_file(skill_name)
    if skill_file is None:
        available = _list_all_skills()
        return json.dumps({
            "success": False,
            "error": f"Skill '{skill_name}' not found.",
            "available_skills": available,
        })

    try:
        content = skill_file.read_text(encoding="utf-8")
        truncated = content
        if len(content) // 3 > 400:
            truncated = (
                content[: 400 * 3]
                + "\n\n[... playbook truncated by RakshakX to save context tokens ...]\n"
            )
        return json.dumps({
            "success": True,
            "skill": skill_name,
            "playbook": truncated,
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Could not read skill file: {exc}"})
