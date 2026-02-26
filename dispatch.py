#!/usr/bin/env python3
"""
~/.shared-ai-skills/dispatch.py
Universal skill auto-dispatcher for AI CLI tools.

Usage:
  # Detect needed skills for a prompt:
  python3 dispatch.py detect "create a PowerPoint presentation about AI"

  # Inject skill content into prompt (for wrapping CLI tools):
  python3 dispatch.py inject "create a PowerPoint presentation about AI"

  # List all available skills:
  python3 dispatch.py list

  # Show skill content:
  python3 dispatch.py show pptx
"""

import sys
import json
import os
import re
from pathlib import Path
from typing import Optional

# ─── Configuration ────────────────────────────────────────────────────────────

SKILLS_ROOT = Path.home() / ".shared-ai-skills"
REGISTRY_PATH = SKILLS_ROOT / "registry.json"

# Max tokens to inject per skill (approximate: 1 token ≈ 4 chars)
MAX_SKILL_TOKENS = 4000
MAX_TOTAL_INJECT_TOKENS = 12000


# ─── Registry Loader ──────────────────────────────────────────────────────────

def load_registry() -> dict:
    """Load the skill registry JSON."""
    if not REGISTRY_PATH.exists():
        print(f"[dispatch] ERROR: registry.json not found at {REGISTRY_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(REGISTRY_PATH) as f:
        return json.load(f)


# ─── Skill Detection ──────────────────────────────────────────────────────────

def detect_skills(prompt: str, registry: dict) -> list[str]:
    """Detect which skills are needed based on prompt content."""
    prompt_lower = prompt.lower()
    needed = []

    for skill_name, skill_config in registry.get("skills", {}).items():
        triggers = skill_config.get("triggers", {})
        matched = False

        # Check keywords
        for kw in triggers.get("keywords", []):
            if kw.lower() in prompt_lower:
                matched = True
                break

        # Check file extensions
        if not matched:
            for ext in triggers.get("file_extensions", []):
                if ext.lower() in prompt_lower:
                    matched = True
                    break

        # Check regex patterns
        if not matched:
            for pattern in triggers.get("task_patterns", []):
                if re.search(pattern, prompt_lower):
                    matched = True
                    break

        if matched:
            needed.append(skill_name)

    return needed


def detect_agents(prompt: str, registry: dict) -> list[str]:
    """Detect which agents/plugins are needed."""
    prompt_lower = prompt.lower()
    needed = []

    for agent_name, agent_config in registry.get("agents", {}).items():
        triggers = agent_config.get("triggers", {})
        matched = False

        for kw in triggers.get("keywords", []):
            if kw.lower() in prompt_lower:
                matched = True
                break

        if not matched:
            for pattern in triggers.get("task_patterns", []):
                if re.search(pattern, prompt_lower):
                    matched = True
                    break

        if matched:
            needed.append(agent_name)

    return needed


# ─── Skill Content Loader ─────────────────────────────────────────────────────

def load_skill_content(skill_name: str, registry: dict) -> Optional[str]:
    """Load a skill's SKILL.md content."""
    skill_config = registry.get("skills", {}).get(skill_name)
    if not skill_config:
        return None

    skill_path = SKILLS_ROOT / skill_config["path"]
    if not skill_path.exists():
        # Try alternate locations
        alt_path = Path.home() / ".claude" / "skills" / skill_name / "SKILL.md"
        if alt_path.exists():
            skill_path = alt_path
        else:
            return None

    content = skill_path.read_text()

    # Truncate if too long
    max_chars = MAX_SKILL_TOKENS * 4
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[...truncated for context efficiency...]"

    return content


# ─── Injection Builder ────────────────────────────────────────────────────────

def build_injected_prompt(prompt: str, skills: list[str], registry: dict) -> str:
    """Build prompt with skill context injected at the top."""
    if not skills:
        return prompt

    injected_parts = []
    total_chars = 0
    max_chars = MAX_TOTAL_INJECT_TOKENS * 4

    for skill_name in skills:
        content = load_skill_content(skill_name, registry)
        if content:
            skill_block = f"<skill:{skill_name}>\n{content}\n</skill:{skill_name}>"
            total_chars += len(skill_block)
            if total_chars > max_chars:
                injected_parts.append(
                    f"<skill:{skill_name}>[Skill loaded but truncated - context limit reached]</skill:{skill_name}>"
                )
                break
            injected_parts.append(skill_block)

    if not injected_parts:
        return prompt

    header = "<!-- Auto-loaded skills based on task analysis -->\n"
    return header + "\n\n".join(injected_parts) + "\n\n---\n\n" + prompt


# ─── CLI Interface ────────────────────────────────────────────────────────────

def cmd_detect(prompt: str):
    """Print detected skill names (one per line)."""
    registry = load_registry()
    skills = detect_skills(prompt, registry)
    agents = detect_agents(prompt, registry)

    if skills:
        print("SKILLS:" + ",".join(skills))
    if agents:
        print("AGENTS:" + ",".join(agents))
    if not skills and not agents:
        print("NONE")


def cmd_inject(prompt: str):
    """Print the full injected prompt to stdout."""
    registry = load_registry()
    skills = detect_skills(prompt, registry)
    result = build_injected_prompt(prompt, skills, registry)
    print(result)


def cmd_list():
    """List all registered skills and agents."""
    registry = load_registry()

    print("\n=== SKILLS ===")
    for name, config in registry.get("skills", {}).items():
        path = SKILLS_ROOT / config["path"]
        status = "✓" if path.exists() else "✗ (missing)"
        keywords = config["triggers"]["keywords"][:3]
        print(f"  {status} {name:20} [{', '.join(keywords)}...]")

    print("\n=== AGENTS ===")
    for name, config in registry.get("agents", {}).items():
        keywords = config["triggers"]["keywords"][:3]
        print(f"  → {name:20} [{', '.join(keywords)}...]")
    print()


def cmd_show(skill_name: str):
    """Show a skill's content."""
    registry = load_registry()
    content = load_skill_content(skill_name, registry)
    if content:
        print(content)
    else:
        print(f"[dispatch] Skill '{skill_name}' not found or file missing.", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "detect":
        cmd_detect(args)
    elif cmd == "inject":
        cmd_inject(args)
    elif cmd == "list":
        cmd_list()
    elif cmd == "show":
        cmd_show(args)
    else:
        print(f"[dispatch] Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
