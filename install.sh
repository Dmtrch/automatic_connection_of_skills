#!/bin/bash
# ~/.shared-ai-skills/install.sh
# Complete installation script for the AI Skills Auto-Loader system.
#
# Run: bash ~/.shared-ai-skills/install.sh
#
# What this does:
# 1. Fixes Claude Code settings (disables duplicate plugins)
# 2. Sets up ~/.shared-ai-skills/ as the unified skills directory
# 3. Creates symlinks for all AI tools
# 4. Installs the universal `ai` wrapper
# 5. Configures Claude Code hooks
# 6. Updates CLAUDE.md with the skill dispatcher

set -e  # exit on error

SKILLS_ROOT="$HOME/.shared-ai-skills"
CLAUDE_DIR="$HOME/.claude"
GEMINI_DIR="$HOME/.gemini"
CODEX_DIR="$HOME/.codex"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[install]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
log_error()   { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║   AI Skills Auto-Loader — Installation        ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# ─── Step 1: Fix Claude Code settings.json ────────────────────────────────────

SETTINGS="$CLAUDE_DIR/settings.json"

if [ -f "$SETTINGS" ]; then
    log_info "Step 1: Fixing Claude Code settings.json..."

    # Backup first
    cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d_%H%M%S)"
    log_success "Backed up settings.json"

    # Disable duplicate plugins
    if grep -q '"document-skills@anthropic-agent-skills": true' "$SETTINGS"; then
        sed -i '' 's/"document-skills@anthropic-agent-skills": true/"document-skills@anthropic-agent-skills": false/' "$SETTINGS"
        log_success "Disabled document-skills@anthropic-agent-skills"
    else
        log_warn "document-skills plugin not found (or already disabled)"
    fi

    if grep -q '"example-skills@anthropic-agent-skills": true' "$SETTINGS"; then
        sed -i '' 's/"example-skills@anthropic-agent-skills": true/"example-skills@anthropic-agent-skills": false/' "$SETTINGS"
        log_success "Disabled example-skills@anthropic-agent-skills"
    else
        log_warn "example-skills plugin not found (or already disabled)"
    fi
else
    log_warn "~/.claude/settings.json not found, skipping"
fi

# ─── Step 2: Set up ~/.shared-ai-skills/ ──────────────────────────────────────

log_info "Step 2: Setting up ~/.shared-ai-skills/..."

mkdir -p "$SKILLS_ROOT/skills"
mkdir -p "$SKILLS_ROOT/hooks"
mkdir -p "$SKILLS_ROOT/wrappers"

# Copy existing skills from Claude to shared
if [ -d "$CLAUDE_DIR/skills" ] && [ ! -L "$CLAUDE_DIR/skills" ]; then
    log_info "Copying existing Claude skills to shared directory..."
    cp -rn "$CLAUDE_DIR/skills/." "$SKILLS_ROOT/skills/" 2>/dev/null || true
    log_success "Copied skills"
fi

# Copy from Gemini if exists
if [ -d "$GEMINI_DIR/skills" ] && [ ! -L "$GEMINI_DIR/skills" ]; then
    log_info "Merging Gemini skills..."
    cp -rn "$GEMINI_DIR/skills/." "$SKILLS_ROOT/skills/" 2>/dev/null || true
fi

log_success "~/.shared-ai-skills/ ready"

# ─── Step 3: Create symlinks for AI tools ─────────────────────────────────────

log_info "Step 3: Creating symlinks..."

# Claude Code
if [ -d "$CLAUDE_DIR" ] && [ ! -L "$CLAUDE_DIR/skills" ]; then
    rm -rf "$CLAUDE_DIR/skills"
    ln -s "$SKILLS_ROOT/skills" "$CLAUDE_DIR/skills"
    log_success "~/.claude/skills → ~/.shared-ai-skills/skills"
fi

# Gemini CLI
# NOTE: Gemini CLI also scans ~/.agents/skills/ automatically.
# We do NOT create a ~/.gemini/skills symlink to avoid "Skill conflict detected"
# warnings caused by Gemini finding the same skills via both paths.
# Skills reach Gemini via ~/.agents/skills → ~/.shared-ai-skills/skills.
if [ -L "$GEMINI_DIR/skills" ]; then
    rm "$GEMINI_DIR/skills"
    log_success "Removed duplicate ~/.gemini/skills symlink (Gemini uses ~/.agents/skills)"
fi

# Codex CLI
mkdir -p "$CODEX_DIR"
if [ ! -L "$CODEX_DIR/instructions" ]; then
    ln -s "$SKILLS_ROOT" "$CODEX_DIR/instructions"
    log_success "~/.codex/instructions → ~/.shared-ai-skills/"
fi

# OpenCode (~/.agents/ or ~/.opencode/)
for AGENT_DIR in "$HOME/.agents" "$HOME/.opencode"; do
    if [ -d "$AGENT_DIR" ] && [ ! -L "$AGENT_DIR/skills" ]; then
        [ -d "$AGENT_DIR/skills" ] && cp -rn "$AGENT_DIR/skills/." "$SKILLS_ROOT/skills/" 2>/dev/null || true
        rm -rf "$AGENT_DIR/skills"
        ln -s "$SKILLS_ROOT/skills" "$AGENT_DIR/skills"
        log_success "$AGENT_DIR/skills → ~/.shared-ai-skills/skills"
    fi
done

# Cursor (~/.cursor/rules or similar)
if [ -d "$HOME/.cursor" ] && [ ! -L "$HOME/.cursor/skills" ]; then
    ln -s "$SKILLS_ROOT" "$HOME/.cursor/skills"
    log_success "~/.cursor/skills → ~/.shared-ai-skills/"
fi

# Sync top-level skill dirs into skills/ so Gemini/OpenCode can discover them.
# Top-level layout: ~/.shared-ai-skills/<skill-name>/SKILL.md
# skills/ layout:   ~/.shared-ai-skills/skills/<skill-name> → ../<skill-name>
log_info "Syncing top-level skills into skills/ directory..."
SYNCED=0
for dir in "$SKILLS_ROOT"/*/; do
    name=$(basename "$dir")
    case "$name" in
        skills|hooks|wrappers|__pycache__) continue ;;
    esac
    if [ -f "$dir/SKILL.md" ] && [ ! -L "$SKILLS_ROOT/skills/$name" ]; then
        ln -s "../$name" "$SKILLS_ROOT/skills/$name"
        SYNCED=$((SYNCED + 1))
    fi
done
log_success "Synced $SYNCED new skill(s) into skills/ ($(ls "$SKILLS_ROOT/skills/" | wc -l | tr -d ' ') total)"

# ─── Step 4: Install `ai` universal wrapper ───────────────────────────────────

log_info "Step 4: Installing universal 'ai' wrapper..."

chmod +x "$SKILLS_ROOT/wrappers/ai"
chmod +x "$SKILLS_ROOT/hooks/pre_tool.sh"
chmod +x "$SKILLS_ROOT/dispatch.py"

mkdir -p "$HOME/.local/bin"

# Create symlink for `ai` command
if [ ! -L "$HOME/.local/bin/ai" ]; then
    ln -s "$SKILLS_ROOT/wrappers/ai" "$HOME/.local/bin/ai"
    log_success "Installed: ~/.local/bin/ai"
else
    log_warn "~/.local/bin/ai already exists"
fi

# Ensure ~/.local/bin is in PATH
SHELL_RC=""
if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/bin/zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ] || [ "$SHELL" = "/bin/bash" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
    if ! grep -q 'shared-ai-skills' "$SHELL_RC"; then
        echo '' >> "$SHELL_RC"
        echo '# AI Skills Auto-Loader' >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        log_success "Added ~/.local/bin to PATH in $SHELL_RC"
    fi
fi

# ─── Step 5: Configure Claude Code hooks ──────────────────────────────────────

log_info "Step 5: Configuring Claude Code hooks..."

if [ -f "$SETTINGS" ]; then
    # Check if hooks already configured
    if ! grep -q 'pre_tool' "$SETTINGS"; then
        # Add hooks to settings.json using Python (safer than sed for JSON)
        python3 - "$SETTINGS" "$SKILLS_ROOT" << 'PYEOF'
import sys, json

settings_path = sys.argv[1]
skills_root = sys.argv[2]

with open(settings_path) as f:
    settings = json.load(f)

hook_command = f"{skills_root}/hooks/pre_tool.sh"

if "hooks" not in settings:
    settings["hooks"] = {}

if "PreToolUse" not in settings["hooks"]:
    settings["hooks"]["PreToolUse"] = []

# Add hook if not already present
hook_entry = {
    "matcher": "Bash|Write|Edit",
    "hooks": [{"type": "command", "command": hook_command}]
}

existing_commands = [
    h.get("command", "")
    for entry in settings["hooks"]["PreToolUse"]
    for h in entry.get("hooks", [])
]

if hook_command not in existing_commands:
    settings["hooks"]["PreToolUse"].append(hook_entry)
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
    print("Hook added to settings.json")
else:
    print("Hook already configured")
PYEOF
        log_success "Claude Code hooks configured"
    else
        log_warn "Hooks already configured in settings.json"
    fi
fi

# ─── Step 6: Update CLAUDE.md with skill dispatcher ──────────────────────────

log_info "Step 6: Updating CLAUDE.md..."

CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
INDEX_BLOCK="
# ── AI Skills Auto-Dispatcher ────────────────────────────────────────────────
# Source: ~/.shared-ai-skills/INDEX.md
# Auto-load rule: Before file creation or complex tasks, check skill index below.

## Skill Quick Index
| Trigger | Skill File |
|---|---|
| presentation, slides, pptx, deck | \`~/.shared-ai-skills/skills/pptx/SKILL.md\` |
| document, word, docx, report | \`~/.shared-ai-skills/skills/docx/SKILL.md\` |
| excel, spreadsheet, xlsx, table | \`~/.shared-ai-skills/skills/xlsx/SKILL.md\` |
| pdf, form, extract | \`~/.shared-ai-skills/skills/pdf/SKILL.md\` |
| poster, design, visual | \`~/.shared-ai-skills/skills/canvas-design/SKILL.md\` |
| schedule, cron, interval | \`~/.shared-ai-skills/skills/schedule/SKILL.md\` |
| mcp server, fastmcp | \`~/.shared-ai-skills/skills/mcp-builder/SKILL.md\` |
| react, shadcn, dashboard | \`~/.shared-ai-skills/skills/web-artifacts-builder/SKILL.md\` |
| create skill, skill creator | \`~/.shared-ai-skills/skills/skill-creator/SKILL.md\` |

**RULE**: Match task → Read skill file FIRST → Then execute task.
# ─────────────────────────────────────────────────────────────────────────────
"

if [ -f "$CLAUDE_MD" ]; then
    if ! grep -q 'AI Skills Auto-Dispatcher' "$CLAUDE_MD"; then
        echo "$INDEX_BLOCK" >> "$CLAUDE_MD"
        log_success "Skill dispatcher added to CLAUDE.md"
    else
        log_warn "Skill dispatcher already in CLAUDE.md"
    fi
else
    echo "Всегда отвечай на русском." > "$CLAUDE_MD"
    echo "$INDEX_BLOCK" >> "$CLAUDE_MD"
    log_success "Created CLAUDE.md with skill dispatcher"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║   Installation complete!                      ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "Test the system:"
echo "  python3 ~/.shared-ai-skills/dispatch.py list"
echo "  python3 ~/.shared-ai-skills/dispatch.py detect 'create a presentation'"
echo "  python3 ~/.shared-ai-skills/dispatch.py detect 'write a report'"
echo ""
echo "Use the universal wrapper:"
echo "  source ~/.zshrc  # reload PATH"
echo "  ai 'create a PowerPoint about AI trends'"
echo "  ai --dry-run 'write an Excel budget'"
echo ""
