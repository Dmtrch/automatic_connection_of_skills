#!/usr/bin/env python3
"""
~/.shared-ai-skills/hooks/pre_tool_inject.py
Advanced Claude Code hook that reads stdin (tool JSON), detects skills,
and outputs a modified tool input with skill context appended.

This is used when you want Claude to *see* skill content inline in tool output,
rather than relying on the model to read files proactively.

Note: This is more aggressive — use only if the INDEX.md approach isn't working.
"""

import sys
import json
import subprocess
from pathlib import Path

DISPATCH = Path.home() / ".shared-ai-skills" / "dispatch.py"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception:
        # If we can't parse, pass through unchanged
        print(raw)
        return

    # Extract text to analyze
    def extract_text(obj, depth=0):
        if depth > 3:
            return ""
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            return " ".join(extract_text(v, depth+1) for v in list(obj.values())[:5])
        if isinstance(obj, list):
            return " ".join(extract_text(i, depth+1) for i in obj[:3])
        return ""

    prompt_text = extract_text(data)

    if not prompt_text or not DISPATCH.exists():
        print(raw)
        return

    # Detect skills
    result = subprocess.run(
        ["python3", str(DISPATCH), "detect", prompt_text],
        capture_output=True, text=True, timeout=5
    )

    if result.returncode != 0 or result.stdout.strip() == "NONE":
        print(raw)
        return

    detected = result.stdout.strip()
    # Parse "SKILLS:pptx,docx"
    skills = []
    for line in detected.split("\n"):
        if line.startswith("SKILLS:"):
            skills = line.replace("SKILLS:", "").split(",")

    if not skills:
        print(raw)
        return

    # Inject skill hint into tool context
    # For Bash tool: append a comment with skill recommendations
    if "command" in data:
        hint = f"\n# [auto-dispatch] Recommended skills for this task: {', '.join(skills)}\n# Read: ~/.shared-ai-skills/skills/<name>/SKILL.md"
        data["command"] = hint + "\n" + data.get("command", "")

    print(json.dumps(data))


if __name__ == "__main__":
    main()
