# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

`~/.shared-ai-skills/` is a unified AI skills auto-dispatcher — a system that auto-detects task context and injects relevant skill content into prompts for any AI CLI tool (Claude Code, Gemini CLI, Codex, OpenCode, Aider).

## Key Commands

```bash
# Detect which skills a prompt needs (outputs SKILLS:name1,name2 or NONE)
python3 dispatch.py detect "create a PowerPoint about AI"

# Inject skill content into a prompt (outputs enriched prompt to stdout)
python3 dispatch.py inject "create a PowerPoint about AI"

# List all registered skills and their status (✓ = file exists, ✗ = missing)
python3 dispatch.py list

# Show a skill's content
python3 dispatch.py show pptx

# Install a skill from aitmpl.com/skills and auto-register in registry.json
python3 dispatch.py add creative-design/frontend-design

# Universal wrapper (routes to claude/gemini/codex with auto skill injection)
ai "create a PowerPoint about AI trends"
ai -t gemini "write a Python script..."
ai --dry-run "create a presentation"    # show detected skills without running
ai --list-skills
ai --add-skill creative-design/frontend-design

# Re-run installation (sets up symlinks, hooks, PATH)
bash install.sh
```

## Architecture

### Core Files
- **`dispatch.py`** — Central dispatcher. Loads `registry.json`, detects needed skills by matching keywords/file extensions/regex patterns in the prompt, and injects `SKILL.md` content into prompts (capped at ~4000 tokens/skill, ~12000 tokens total). Supports Russian via light suffix-stripping stemmer (`_stem_ru_word`).
- **`registry.json`** — Machine-readable skill registry. Has three top-level sections:
  - `"skills"` — skills detected and injected by `dispatch.py`
  - `"agents"` — agent/plugin hints (detected but not content-injected)
  - `"cowork_plugins"` — document-type plugins (pptx, docx, xlsx, pdf, canvas) loaded by the Cowork plugin system, not by this dispatcher
- **`INDEX.md`** — Human-readable trigger index embedded in `~/.claude/CLAUDE.md` for direct in-context lookup without running the dispatcher.

### Hook System
- **`hooks/pre_tool.sh`** — Claude Code `PreToolUse` hook (registered in `~/.claude/settings.json`). Intercepts `Bash|Write|Edit` tool calls, extracts text from the JSON tool input, runs `dispatch.py detect`, and writes detected skill names to `.last_detected_skills`.
- **`hooks/pre_tool_inject.py`** — Python helper for the hook.

### Wrappers
- **`wrappers/ai`** — Installed as `~/.local/bin/ai`. Detects skills → injects content → routes to the chosen AI CLI tool (claude, gemini, codex, opencode, aider).

### Skill Storage Layout
Skills live in two places depending on type:

| Type | Location | Example |
|---|---|---|
| Language/framework skills | `~/.shared-ai-skills/<skill-name>/SKILL.md` | `python-pro/SKILL.md` |
| Document/plugin skills | `~/.shared-ai-skills/skills/<skill-name>/SKILL.md` | `skills/pptx/SKILL.md` |

The `skills/` subdirectory is symlinked from `~/.claude/skills/`, `~/.agents/skills/`, etc. — enabling skill sharing across AI tools without duplication.

### How Each Tool Discovers Skills

| Tool | Discovery mechanism | Notes |
|---|---|---|
| **Claude Code** | `~/.claude/CLAUDE.md` embeds `INDEX.md` content; hook injects SKILL.md at tool-call time | Skills in context from session start |
| **Gemini CLI** | Scans `~/.agents/skills/*/SKILL.md` (lazy-loaded per `@skill-name`) | Do NOT symlink `~/.gemini/skills/` — Gemini also scans `~/.agents/`, causes conflicts |
| **OpenCode** | Reads `INDEX.md` as a plain file in context, then reads `SKILL.md` on demand | No YAML frontmatter required; ask "какие skills у тебя есть?" to list all |
| **Codex** | `~/.codex/instructions` → symlink to `~/.shared-ai-skills/`; built-in TUI (`/skills`) to enable/disable | Token usage shown automatically on session exit |
| **`ai` wrapper** | `dispatch.py inject` — injects SKILL.md content into prompt before routing | Works for all tools via CLI |

### Checking Token Usage Per Tool

| Tool | Command | When available |
|---|---|---|
| **Claude Code** | `/context` | Any time during session |
| **Codex** | Automatic summary on exit: `Token usage: total=X input=Y (+ Z cached) output=W` | End of session only |
| **Gemini CLI** | No built-in command | Estimate via file sizes |
| **OpenCode** | No built-in command | Estimate via file sizes |

Codex example output (session with all skills loaded):
```
Token usage: total=63 324  input=58 900 (+ 160 000 cached)  output=4 424 (reasoning 3 528)
```

### Adding a New Skill
1. Create `<skill-name>/SKILL.md` (or `skills/<skill-name>/SKILL.md` for document skills)
2. Add an entry to `registry.json` under `"skills"` with `path`, `description`, and `triggers`
3. Add a row to `INDEX.md` for human-readable lookup
4. Test: `python3 dispatch.py detect "keyword from your skill"`

Or use the auto-installer: `python3 dispatch.py add <category/skill-name>` — downloads from aitmpl.com, auto-extracts keywords from SKILL.md content, warns about duplicate triggers with existing skills, and registers in both `registry.json` and `INDEX.md`.

### Modifying Triggers
All trigger logic is in `registry.json`. Each skill supports:
- `keywords` — substring match (case-insensitive); Russian words supported with single-character suffix stripping (e.g. `архитектуру` matches `архитектур`)
- `file_extensions` — match `.ext` anywhere in the prompt
- `task_patterns` — regex match against the prompt (applied to both original and stemmed Russian text)
