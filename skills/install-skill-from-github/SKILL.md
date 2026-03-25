---
name: install-skill-from-github
description: >
  Install an AI skill from a GitHub repository into ~/.shared-ai-skills with mandatory
  security audit and cross-tool compatibility verification (Claude Code, Gemini CLI,
  Codex, OpenCode, Aider). Use when user provides a GitHub URL to install as a skill,
  says "install skill from github", "добавить скилл из github", or "установить навык из репозитория".
  Do NOT use for installing npm packages, Python packages, Docker images, or non-skill repositories.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# install-skill-from-github

## Overview

Full installation cycle for AI skills from GitHub: download → security audit → register
→ symlink → verify. The security audit (Step 2) is **mandatory** and cannot be skipped.

Supports all GitHub URL formats and two installation backends:
- `dispatch.py add` (preferred — handles registration automatically)
- `npx skills` (for repos with multiple skills or non-standard layouts)

---

## Step 1 — Parse GitHub URL and Download SKILL.md

### Supported URL formats

| Format | Example |
|---|---|
| Repo root | `https://github.com/USER/REPO` |
| Specific branch/path | `https://github.com/USER/REPO/tree/main/path/to/skill` |
| Direct raw URL | `https://raw.githubusercontent.com/USER/REPO/main/SKILL.md` |

### Download procedure

1. Extract `USER`, `REPO`, and optional `PATH` from the URL.
2. Convert to raw URL:
   - Root: `https://raw.githubusercontent.com/USER/REPO/main/SKILL.md`
   - Try `main` first, then `master` if 404.
   - If path provided: `https://raw.githubusercontent.com/USER/REPO/main/PATH/SKILL.md`
3. Download to a temporary directory:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TMPDIR="/tmp/skill-install-${TIMESTAMP}"
mkdir -p "$TMPDIR"
curl -fsSL "https://raw.githubusercontent.com/USER/REPO/main/SKILL.md" -o "$TMPDIR/SKILL.md"
```

4. If SKILL.md not found at root, search for it:

```bash
# Try common locations
for path in "skills/SKILL_NAME/SKILL.md" "skill/SKILL.md" "SKILL_NAME/SKILL.md"; do
  curl -fsSL "https://raw.githubusercontent.com/USER/REPO/main/$path" -o "$TMPDIR/SKILL.md" && break
done
```

5. Verify the download: `wc -l "$TMPDIR/SKILL.md"` — must be > 3 lines.
6. Inspect the frontmatter: `head -10 "$TMPDIR/SKILL.md"` — must contain `---` and `name:`.

---

## Step 2 — Mandatory Security Audit

**This step cannot be skipped under any circumstances.**

Invoke the `skill-security-audit` skill with the downloaded file path:

```bash
# Check if skill-scanner is available (preferred)
which skill-scanner && /Users/dim/from_git/skill-scanner/scripts/install-skill.sh "$TMPDIR"
```

If skill-scanner is not available, follow the `skill-security-audit` skill procedure manually:
run all grep checks from Steps 2–5 of that skill against `$TMPDIR/SKILL.md`.

### Decision after audit

| Result | Action |
|---|---|
| `SECURITY_AUDIT: PASSED` | Proceed to Step 3 |
| `PASSED WITH WARNINGS` | Show warnings to user, wait for acknowledgment, then proceed |
| `BLOCKED (HIGH)` | Show report. Ask user for explicit `ДА` to override. If `ДА` — proceed. |
| `BLOCKED (CRITICAL)` | Show report. **Do not proceed.** Offer to open the report file. |

---

## Step 3 — Determine Skill Name and Install Path

### Extract skill name

Read `name:` from the YAML frontmatter:

```bash
grep "^name:" "$TMPDIR/SKILL.md" | head -1 | sed 's/name: *//'
```

### Choose install path

| Skill type | Install location | Condition |
|---|---|---|
| Document/plugin skill | `~/.shared-ai-skills/skills/<name>/SKILL.md` | name matches: pptx, docx, xlsx, pdf, canvas-design, or similar document types |
| Language/framework skill | `~/.shared-ai-skills/<name>/SKILL.md` | all other skills |

Default to `skills/<name>/SKILL.md` unless the skill clearly targets a programming language or framework.

### Check for conflicts

```bash
python3 ~/.shared-ai-skills/dispatch.py list | grep "<skill-name>"
```

If already installed — ask user whether to overwrite or abort.

---

## Step 4 — Install via dispatch.py

### Preferred path (automatic registration)

```bash
python3 ~/.shared-ai-skills/dispatch.py add "https://github.com/USER/REPO"
```

`dispatch.py add` handles:
- Downloading SKILL.md
- Extracting keywords and description
- Checking for duplicate triggers
- Registering in `registry.json`
- Adding a row to `INDEX.md`

If dispatch.py reports duplicate keywords (≥ 2 matches with an existing skill) — show
the conflict to the user and ask whether to proceed.

### Alternative: npx skills (for multi-skill repos)

If the repo contains multiple skills or `dispatch.py add` fails:

```bash
python3 ~/.shared-ai-skills/dispatch.py add --npx \
  "npx skills add https://github.com/USER/REPO --skill SKILL-NAME --yes"
```

### Manual fallback

If both automated paths fail, install manually:

```bash
INSTALL_DIR="$HOME/.shared-ai-skills/skills/<skill-name>"
mkdir -p "$INSTALL_DIR"
cp "$TMPDIR/SKILL.md" "$INSTALL_DIR/SKILL.md"
```

Then manually add the entry to `registry.json` and `INDEX.md` (see Step 5).

---

## Step 5 — Register in registry.json and INDEX.md

**Skip if dispatch.py handled registration automatically.**

### registry.json entry

Add to the `"skills"` section:

```json
"<skill-name>": {
  "path": "skills/<skill-name>/SKILL.md",
  "description": "<description from frontmatter>",
  "triggers": {
    "keywords": ["<extracted keywords>"],
    "file_extensions": [],
    "task_patterns": []
  }
}
```

Keywords to extract: nouns and verbs from the `description:` field in frontmatter.
Add Russian equivalents for key terms if the skill targets Russian-speaking users.

### INDEX.md entry

Find the appropriate section in `~/.shared-ai-skills/INDEX.md` (or add `## 🔧 External Skills`
at the bottom before the Document Skills line). Add a row:

```markdown
| <trigger keywords, comma-separated> | `<skill-name>` |
```

---

## Step 6 — Verify Cross-Tool Compatibility

Check that the skill is reachable by all AI tools via symlinks:

```bash
# Claude Code
ls -la ~/.claude/skills/ | grep "<skill-name>"

# Gemini CLI and OpenCode (via ~/.agents/skills → ~/.shared-ai-skills/skills)
ls -la ~/.agents/skills/ | grep "<skill-name>"

# Codex (accesses ~/.shared-ai-skills/ directly via ~/.codex/instructions symlink)
ls -la ~/.codex/instructions/ | grep "<skill-name>"
```

**Note:** Gemini CLI does NOT need `~/.gemini/skills/<name>` — it discovers skills via
`~/.agents/skills/` automatically. Do NOT create `~/.gemini/skills/` symlink.

If any symlink is missing, run:

```bash
bash ~/.shared-ai-skills/install.sh
```

`install.sh` rebuilds all symlinks without affecting installed skills.

---

## Step 7 — Verify Installation

```bash
# Verify the skill is registered and the file exists
python3 ~/.shared-ai-skills/dispatch.py list | grep "<skill-name>"
# Expected: ✓ <skill-name>

# Test trigger detection
python3 ~/.shared-ai-skills/dispatch.py detect "<keyword from the skill>"
# Expected: SKILLS:<skill-name>

# Show full content
python3 ~/.shared-ai-skills/dispatch.py show "<skill-name>"
```

All three checks must pass before confirming successful installation.

---

## Common Mistakes

**Repo has no SKILL.md at root**
Check `skills/` subdirectory, then browse the repo structure with:
```bash
curl -s "https://api.github.com/repos/USER/REPO/contents" | python3 -c "import sys,json; [print(f['path']) for f in json.load(sys.stdin)]"
```

**dispatch.py add fails with 404**
The repo may use `master` instead of `main`. Try:
```bash
python3 ~/.shared-ai-skills/dispatch.py add --npx "npx skills add https://github.com/USER/REPO --skill SKILL-NAME"
```

**Skill triggers conflict with existing skills**
`dispatch.py add` warns about ≥ 2 keyword overlaps. If the new skill is more specific,
remove the conflicting keywords from the new skill's `registry.json` entry rather than
modifying the existing skill.

**Symlinks missing after install**
Running `bash install.sh` is always safe — it checks before creating, never overwrites
existing skills, and rebuilds only missing symlinks.
