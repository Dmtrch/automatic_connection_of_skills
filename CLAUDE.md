# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

`~/.shared-ai-skills/` is a unified AI skills auto-dispatcher — a system that auto-detects task context and injects relevant skill content into prompts for any AI CLI tool (Claude Code, Gemini CLI, Codex, OpenCode, Aider).

## Key Commands

```bash
# Detect which skills a prompt needs
python3 dispatch.py detect "create a PowerPoint about AI"

# Inject skill content into a prompt (outputs enriched prompt to stdout)
python3 dispatch.py inject "create a PowerPoint about AI"

# List all registered skills and their status (✓ = file exists)
python3 dispatch.py list

# Show a skill's content
python3 dispatch.py show pptx

# Universal wrapper (routes to claude/gemini/codex with auto skill injection)
ai "create a PowerPoint about AI trends"
ai -t gemini "write a Python script..."
ai --dry-run "create a presentation"    # show detected skills without running
ai --list-skills

# Re-run installation (sets up symlinks, hooks, PATH)
bash install.sh
```

## Architecture

### Core Files
- **`dispatch.py`** — Central dispatcher. Loads `registry.json`, detects needed skills by matching keywords/file extensions/regex patterns in the prompt, and injects `SKILL.md` content into prompts (capped at ~4000 tokens/skill, ~12000 tokens total).
- **`registry.json`** — Machine-readable skill registry. Each entry maps a skill name to its path and triggers (keywords, file_extensions, task_patterns).
- **`INDEX.md`** — Human-readable trigger index used in `~/.claude/CLAUDE.md` to instruct AI tools on when to read skill files directly.

### Hook System
- **`hooks/pre_tool.sh`** — Claude Code `PreToolUse` hook (registered in `~/.claude/settings.json`). Intercepts `Bash|Write|Edit` tool calls, extracts text from the JSON tool input, runs `dispatch.py detect`, and writes detected skill names to `.last_detected_skills`.
- **`hooks/pre_tool_inject.py`** — Python helper for the hook.

### Wrappers
- **`wrappers/ai`** — Installed as `~/.local/bin/ai`. Detects skills → injects content → routes to the chosen AI CLI tool.

### Skill Storage Layout
Skills live in two places depending on type:

| Type | Location | Example |
|---|---|---|
| Language/framework skills | `~/.shared-ai-skills/<skill-name>/SKILL.md` | `python-pro/SKILL.md` |
| Document/plugin skills | `~/.shared-ai-skills/skills/<skill-name>/SKILL.md` | `skills/pptx/SKILL.md` |

The `skills/` subdirectory is symlinked from `~/.claude/skills/`, `~/.gemini/skills/`, etc. — enabling skill sharing across AI tools without duplication.

### Adding a New Skill
1. Create `<skill-name>/SKILL.md` (or `skills/<skill-name>/SKILL.md` for document skills)
2. Add an entry to `registry.json` under `"skills"` with `path`, `description`, and `triggers`
3. Add a row to `INDEX.md` for human-readable lookup
4. Test: `python3 dispatch.py detect "keyword from your skill"`

### Modifying Triggers
All trigger logic is in `registry.json`. Each skill supports:
- `keywords` — substring match (case-insensitive)
- `file_extensions` — match `.ext` anywhere in the prompt
- `task_patterns` — regex match against the prompt
