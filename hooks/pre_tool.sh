#!/bin/bash
# ~/.shared-ai-skills/hooks/pre_tool.sh
# Claude Code PreToolUse hook — detects task context and signals needed skills.
#
# Install in ~/.claude/settings.json:
# {
#   "hooks": {
#     "PreToolUse": [{
#       "matcher": "Bash|Write|Edit",
#       "hooks": [{"type": "command", "command": "~/.shared-ai-skills/hooks/pre_tool.sh"}]
#     }]
#   }
# }
#
# How it works:
# Claude Code passes tool input as JSON to stdin.
# This hook reads the tool name + input, detects skills, writes a hint to a temp file.
# Claude Code can then read this hint in subsequent turns via the dispatcher skill.

DISPATCH="$HOME/.shared-ai-skills/dispatch.py"
HINT_FILE="$HOME/.shared-ai-skills/.last_detected_skills"

# Read tool input from stdin
INPUT=$(cat)
TOOL_NAME="${CLAUDE_TOOL_NAME:-unknown}"

# Extract text content from JSON input for analysis
PROMPT_TEXT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Extract any string values from the tool input
    texts = []
    def extract_strings(obj):
        if isinstance(obj, str):
            texts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                extract_strings(v)
        elif isinstance(obj, list):
            for item in obj:
                extract_strings(item)
    extract_strings(data)
    print(' '.join(texts[:5]))  # First 5 string values
except:
    pass
" 2>/dev/null)

# Detect needed skills
if [ -n "$PROMPT_TEXT" ] && [ -f "$DISPATCH" ]; then
    DETECTED=$(python3 "$DISPATCH" detect "$PROMPT_TEXT" 2>/dev/null)
    if [ -n "$DETECTED" ] && [ "$DETECTED" != "NONE" ]; then
        echo "$DETECTED" > "$HINT_FILE"
        # Log for debugging (silent in production)
        # echo "[hook] Detected: $DETECTED for tool: $TOOL_NAME" >> /tmp/ai-hooks.log
    fi
fi

# Always pass through — hooks must exit 0 to allow tool execution
exit 0
