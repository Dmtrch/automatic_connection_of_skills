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

  # Install skill from aitmpl.com/skills and auto-register:
  python3 dispatch.py add creative-design/frontend-design
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

# Common words to ignore when extracting keywords from skill content
STOPWORDS = {
    "the", "and", "for", "this", "that", "with", "use", "when", "your", "from",
    "have", "will", "been", "are", "was", "were", "not", "can", "all", "they",
    "their", "there", "than", "then", "its", "into", "which", "what", "how",
    "also", "each", "more", "about", "you", "our", "using", "build", "create",
    "make", "write", "add", "get", "set", "any", "new", "should", "must",
    "only", "such", "these", "those", "both", "first", "last", "most", "like",
    "very", "just", "even", "well", "good", "best", "used", "work", "works",
    "provides", "support", "supports", "including", "included", "based", "code",
    "file", "files", "data", "type", "types", "function", "functions", "class",
}

# Russian vowel endings that mark noun/adjective declension
_RU_VOWEL_ENDINGS = "аяыиеую"


def _stem_ru_word(word: str) -> str:
    """Strip single-character Russian inflection ending for better matching.

    Converts declined forms to a common stem:
        архитектуру → архитектур  (accusative → stem)
        архитектуры → архитектур  (genitive   → stem)
        системы     → систем      (genitive   → stem)
    Only strips when word is longer than 4 chars and ends in a Russian vowel.
    """
    if len(word) > 4 and word[-1] in _RU_VOWEL_ENDINGS and re.search("[а-яё]", word):
        return word[:-1]
    return word


def _normalize_ru(text: str) -> str:
    """Normalize Russian text by stemming each word (strip declension endings)."""
    return " ".join(_stem_ru_word(w) for w in text.split())


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
    prompt_normalized = _normalize_ru(prompt_lower)  # Russian stem form
    needed = []

    for skill_name, skill_config in registry.get("skills", {}).items():
        triggers = skill_config.get("triggers", {})
        matched = False

        # Check keywords (try exact match first, then normalized for Russian)
        for kw in triggers.get("keywords", []):
            kw_lower = kw.lower()
            if kw_lower in prompt_lower:
                matched = True
                break
            kw_normalized = _normalize_ru(kw_lower)
            if kw_normalized in prompt_normalized:
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
                if re.search(pattern, prompt_lower) or re.search(pattern, prompt_normalized):
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


# ─── Skill Auto-Installer ─────────────────────────────────────────────────────

def extract_skill_info(skill_name: str, content: str) -> tuple:
    """Extract description and keywords from SKILL.md content."""
    description = ""

    # Parse YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            frontmatter = content[3:end]
            desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip().strip('"\'')
                # Trim long description (may span 1 sentence)
                description = description.split(".")[0].strip()

    # Start with skill name parts
    name_parts = re.split(r'[-_/]', skill_name)
    keywords = [p.lower() for p in name_parts if len(p) > 2]
    keywords.append(skill_name.lower())

    # Add words from description
    if description:
        desc_words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#]{3,}\b', description)
        for w in desc_words:
            wl = w.lower()
            if wl not in STOPWORDS and wl not in keywords:
                keywords.append(wl)

    # Extract frequent words from first 2000 chars of content
    main_content = content[:2000]
    content_words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#]{3,}\b', main_content)
    word_freq: dict = {}
    for w in content_words:
        wl = w.lower()
        if wl not in STOPWORDS:
            word_freq[wl] = word_freq.get(wl, 0) + 1
    top_words = sorted(word_freq, key=lambda x: -word_freq[x])[:8]
    for w in top_words:
        if w not in keywords:
            keywords.append(w)

    # Deduplicate, preserving order
    seen: set = set()
    unique = []
    for k in keywords:
        if k not in seen and len(k) > 2:
            seen.add(k)
            unique.append(k)

    return description or f"{skill_name} skill", unique[:12]


def find_similar_skills(new_keywords: list, registry: dict) -> list:
    """Find existing skills with overlapping keywords (potential duplicates)."""
    new_set = {k.lower() for k in new_keywords}
    similar = []
    for skill_name, config in registry.get("skills", {}).items():
        existing_kw = {k.lower() for k in config.get("triggers", {}).get("keywords", [])}
        overlap = list(new_set & existing_kw)
        if len(overlap) >= 2:
            similar.append((skill_name, overlap))
    return similar


def update_index(skill_name: str, keywords: list, category: Optional[str]):
    """Add a row to INDEX.md for the newly installed skill."""
    index_path = SKILLS_ROOT / "INDEX.md"
    if not index_path.exists():
        return

    content = index_path.read_text()
    kw_str = ", ".join(keywords[:3]) if keywords else skill_name
    new_row = f"| {kw_str} | `{skill_name}` |"

    ext_section = "## 🌐 External Skills"
    ext_table_header = "| Trigger keywords | Skill folder |\n|---|---|"

    if ext_section in content:
        # Append row to existing section's table
        idx = content.index(ext_section)
        next_sep = content.find("\n---", idx + 1)
        if next_sep == -1:
            content += f"\n{new_row}"
        else:
            content = content[:next_sep] + f"\n{new_row}" + content[next_sep:]
    else:
        # Create new section before the last "---" separator
        last_sep = content.rfind("\n---")
        new_section = f"\n\n{ext_section}\n\n{ext_table_header}\n{new_row}\n"
        if last_sep != -1:
            content = content[:last_sep] + new_section + content[last_sep:]
        else:
            content += new_section

    index_path.write_text(content)


def cmd_add(skill_identifier: str):
    """Install a skill from aitmpl.com/skills and register it in the dispatcher."""
    import subprocess

    if not skill_identifier:
        print("[add] ERROR: No skill identifier provided.", file=sys.stderr)
        print("[add] Usage: python3 dispatch.py add <category/skill-name>", file=sys.stderr)
        print("[add] Example: python3 dispatch.py add creative-design/frontend-design", file=sys.stderr)
        sys.exit(1)

    skill_name = skill_identifier.split("/")[-1]
    skill_category = skill_identifier.split("/")[0] if "/" in skill_identifier else None

    # Check if already registered
    registry = load_registry()
    if skill_name in registry.get("skills", {}):
        print(f"[add] ⚠️  Skill '{skill_name}' is already registered.")
        print("[add] Remove it from registry.json first to re-register.")
        sys.exit(0)

    print(f"[add] 📦 Installing: {skill_identifier}")
    print(f"[add] Running: npx claude-code-templates@latest --skill={skill_identifier} --yes\n")

    result = subprocess.run(
        ["npx", "claude-code-templates@latest", f"--skill={skill_identifier}", "--yes"],
        text=True,
    )

    if result.returncode != 0:
        print(f"\n[add] ERROR: Installation failed (exit code {result.returncode})", file=sys.stderr)
        sys.exit(1)

    # Search for installed SKILL.md
    search_paths = [
        Path.home() / ".claude" / "skills" / skill_name / "SKILL.md",
        Path.home() / ".claude" / "skills" / skill_identifier / "SKILL.md",
        SKILLS_ROOT / "skills" / skill_name / "SKILL.md",
    ]

    skill_file = None
    for p in search_paths:
        if p.exists():
            skill_file = p
            break

    if skill_file is None:
        print(f"\n[add] ⚠️  SKILL.md not found after installation.", file=sys.stderr)
        for p in search_paths:
            print(f"      Searched: {p}", file=sys.stderr)
        print("[add] Registering with minimal info...")
        description = f"{skill_name} skill"
        keywords = [k.lower() for k in re.split(r'[-_]', skill_name) if len(k) > 2]
    else:
        print(f"\n[add] ✓ Found: {skill_file}")
        content = skill_file.read_text()
        description, keywords = extract_skill_info(skill_name, content)

    # Warn about potential duplicates
    similar = find_similar_skills(keywords, registry)
    if similar:
        print(f"\n[add] ⚠️  Possible duplicates detected:")
        for sim_name, overlap in similar:
            print(f"      - {sim_name}: shared keywords: {', '.join(sorted(overlap))}")
        print()

    # Determine path relative to SKILLS_ROOT
    relative_path = f"skills/{skill_name}/SKILL.md"

    # Add to registry.json
    registry["skills"][skill_name] = {
        "path": relative_path,
        "description": description,
        "triggers": {
            "keywords": keywords[:8],
            "file_extensions": [],
            "task_patterns": [],
        },
    }
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print(f"[add] ✓ Registered in registry.json")

    # Add row to INDEX.md
    update_index(skill_name, keywords[:3], skill_category)
    print(f"[add] ✓ Added to INDEX.md")

    print(f"\n[add] ✅ Skill '{skill_name}' ready to use!")
    print(f"      Description: {description}")
    print(f"      Keywords:    {', '.join(keywords[:6])}")
    print(f"\n      Test:  python3 dispatch.py detect \"{keywords[0] if keywords else skill_name}\"")
    print(f"      View:  python3 dispatch.py show {skill_name}")


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
    elif cmd == "add":
        cmd_add(args)
    else:
        print(f"[dispatch] Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
