# AI Skills Auto-Dispatcher (`~/.shared-ai-skills`)

> **English** | [Русский](#русский)

---

## English

### What Is This?

A unified skill library with an automatic dispatcher for AI CLI tools. Instead of maintaining separate prompt libraries for each AI tool (Claude Code, Gemini CLI, Codex, OpenCode, Aider), this system detects what expert knowledge your task requires and injects only the relevant skill content — without loading everything into the context window.

**Key metric:** `~600 tokens` (index) vs `~40,000+ tokens` (all skills) — **98% context savings**.

### How It Works

```
You type:  ai "create a PowerPoint about AI trends"
                      ↓
dispatch.py detects:  "PowerPoint" → skill: pptx
                      ↓
Reads only:           skills/pptx/SKILL.md (~3,000 tokens)
                      ↓
AI receives:          [pptx skill content] + your prompt
```

The AI never sees skills it doesn't need. The index (`INDEX.md`, ~600 tokens) lives in `~/.claude/CLAUDE.md` as a routing table — the AI reads it, matches your task, then reads only the required `SKILL.md` file on demand.

### Installation

```bash
bash ~/.shared-ai-skills/install.sh
```

The installer:
1. Fixes `~/.claude/settings.json` (disables duplicate plugins)
2. Creates symlinks so all AI tools share the same skills directory
3. Installs the universal `ai` command to `~/.local/bin/ai`
4. Adds `~/.local/bin` to your `PATH` (`.zshrc` / `.bashrc`)
5. Registers the Claude Code `PreToolUse` hook for automatic skill detection
6. Appends the skill index to `~/.claude/CLAUDE.md`

After installation:

```bash
source ~/.zshrc   # reload PATH
ai --list-skills  # verify everything works
```

### Usage

#### Universal `ai` wrapper

```bash
# Auto-detects skills, routes to Claude by default
ai "create a PowerPoint about AI trends"

# Route to a specific AI tool
ai -t gemini "write a Python script to parse JSON"
ai -t codex "refactor this TypeScript class"

# Inspect what would be injected without running
ai --dry-run "create a presentation about microservices"

# List all registered skills
ai --list-skills
```

#### Installing skills from the marketplace

```bash
# Install a skill from aitmpl.com/skills — auto-registers in registry.json and INDEX.md
ai --add-skill creative-design/frontend-design
ai --add-skill data-science/pandas-expert

# Equivalent using dispatch.py directly
python3 ~/.shared-ai-skills/dispatch.py add creative-design/frontend-design
```

The installer:
1. Downloads via `npx claude-code-templates@latest --skill=<id> --yes`
2. Extracts keywords from the skill's `SKILL.md` frontmatter and content
3. Warns about potential duplicates (≥2 overlapping keywords with existing skills)
4. Registers in `registry.json` and adds a row to `INDEX.md`

#### `dispatch.py` directly

```bash
# Detect which skills a prompt needs
python3 ~/.shared-ai-skills/dispatch.py detect "async python crawler"

# Inject skill content into a prompt (outputs enriched prompt to stdout)
python3 ~/.shared-ai-skills/dispatch.py inject "build a REST API"

# List all skills and their status (✓ = file exists, ✗ = missing)
python3 ~/.shared-ai-skills/dispatch.py list

# Print a skill's content
python3 ~/.shared-ai-skills/dispatch.py show python-pro
```

### Directory Structure

```
~/.shared-ai-skills/
├── dispatch.py          # Core dispatcher: detect / inject / list / show
├── registry.json        # Skill registry: paths + trigger rules
├── INDEX.md             # Human-readable trigger table (~600 tokens)
├── install.sh           # One-command installer
│
├── hooks/
│   ├── pre_tool.sh      # Claude Code PreToolUse hook
│   └── pre_tool_inject.py
│
├── wrappers/
│   └── ai               # Universal CLI wrapper (installed to ~/.local/bin/ai)
│
├── skills/              # Document / plugin skills (symlinked to ~/.claude/skills)
│   ├── pptx/SKILL.md
│   ├── docx/SKILL.md
│   ├── xlsx/SKILL.md
│   ├── pdf/SKILL.md
│   ├── osgrep/SKILL.md
│   ├── find-skills/SKILL.md
│   └── planning-with-files/SKILL.md
│
├── python-pro/SKILL.md         # Language / framework skills
├── typescript-pro/SKILL.md
├── react-patterns/SKILL.md
├── async-python-patterns/SKILL.md
├── swift-expert/SKILL.md
├── kotlin-specialist/SKILL.md
├── cpp-pro/SKILL.md
├── android-dev/SKILL.md
├── aws-serverless/SKILL.md
└── ...                          # 30+ more skills
```

**Two storage locations:**

| Type | Path | Example |
|---|---|---|
| Language / framework | `~/.shared-ai-skills/<skill>/SKILL.md` | `python-pro/SKILL.md` |
| Document / plugin | `~/.shared-ai-skills/skills/<skill>/SKILL.md` | `skills/pptx/SKILL.md` |

> **Note for Claude Code Skill tool discovery:** `~/.claude/skills` is symlinked to `~/.shared-ai-skills/` (the root), not to the `skills/` subdirectory. Claude Code scans `~/.claude/skills/*/SKILL.md` (one level deep), so skills in `skills/<name>/` are **not** automatically visible via the Skill tool. To expose them, create a top-level symlink:
> ```bash
> ln -s ~/.shared-ai-skills/skills/planning-with-files ~/.shared-ai-skills/planning-with-files
> ```
> Skills installed via `dispatch.py add` at the top level are discovered automatically.

### Supported AI Tools

| Tool | Integration |
|---|---|
| Claude Code | Hook (`PreToolUse`) + symlinked `~/.claude/skills/` |
| Gemini CLI | Symlinked `~/.gemini/skills/` |
| Codex CLI | Symlinked `~/.codex/instructions/` |
| OpenCode | Symlinked `~/.opencode/skills/` |
| Aider | Via `ai -t aider "..."` wrapper |
| Cursor | Symlinked `~/.cursor/skills/` |

### Adding a New Skill

1. Create the skill file:
   ```bash
   mkdir ~/.shared-ai-skills/my-skill
   nano ~/.shared-ai-skills/my-skill/SKILL.md
   ```

2. Register it in `registry.json`:
   ```json
   "my-skill": {
     "path": "my-skill/SKILL.md",
     "description": "What this skill does",
     "triggers": {
       "keywords": ["my-keyword", "another trigger"],
       "file_extensions": [".ext"],
       "task_patterns": ["create.*something", "build.*widget"]
     }
   }
   ```

3. Add a row to `INDEX.md` for the human-readable table.

4. Test:
   ```bash
   python3 dispatch.py detect "my-keyword in a sentence"
   ```

### How Triggers Work

Each skill in `registry.json` has three trigger types (all case-insensitive):

| Type | Match method | Example |
|---|---|---|
| `keywords` | Substring in prompt | `"python"`, `"asyncio"` |
| `file_extensions` | Extension string in prompt | `".py"`, `".tsx"` |
| `task_patterns` | Regex match | `"write.*python"`, `"create.*\\.py"` |

A skill is activated if **any one** trigger matches.

### Bilingual Support (EN + RU)

All 38 built-in skills have Russian trigger keywords. Prompts in Russian are detected automatically:

```bash
python3 dispatch.py detect "написать скрипт на питоне"
# → SKILLS:python-pro

python3 dispatch.py detect "спроектировать архитектуру системы"
# → SKILLS:software-architecture
```

**Russian morphology normalization**: The dispatcher automatically strips common Russian case endings (`а`, `я`, `ы`, `и`, `е`, `у`, `ю`) before matching, so declined word forms work without listing every inflection in the registry:

| Prompt word | Normalized | Matches keyword |
|---|---|---|
| `архитектуру` | `архитектур` | `архитектура` ✓ |
| `микросервисов` | `микросервисо` | `микросервисы` → `микросервис` ✓ |
| `агента` | `агент` | `агент` ✓ |

### Token Budget

`dispatch.py` enforces limits when injecting skill content:

- Max per skill: **~4,000 tokens** (16,000 characters)
- Max total: **~12,000 tokens** (48,000 characters)

Content is truncated if it exceeds the limit.

---

## Русский

### Что это такое?

Единая библиотека AI-скиллов с автоматическим диспетчером. Вместо того чтобы поддерживать отдельные наборы промптов для каждого AI-инструмента (Claude Code, Gemini CLI, Codex, OpenCode, Aider), эта система определяет, какие экспертные знания нужны для конкретной задачи, и инжектирует только нужный контент — не загружая всё в контекстное окно.

**Ключевой показатель:** `~600 токенов` (индекс) против `~40 000+ токенов` (все скиллы) — **экономия контекста 98%**.

### Как работает

```
Вы пишете: ai "создай PowerPoint о трендах AI"
                      ↓
dispatch.py определяет: "PowerPoint" → скилл: pptx
                      ↓
Читает только:        skills/pptx/SKILL.md (~3 000 токенов)
                      ↓
AI получает:          [содержимое pptx-скилла] + ваш запрос
```

AI никогда не видит скиллы, которые не нужны. Индекс (`INDEX.md`, ~600 токенов) живёт в `~/.claude/CLAUDE.md` как таблица маршрутизации — AI читает её, сопоставляет задачу и читает только нужный `SKILL.md` по требованию.

### Установка

```bash
bash ~/.shared-ai-skills/install.sh
```

Скрипт установки:
1. Правит `~/.claude/settings.json` (отключает дублирующие плагины)
2. Создаёт симлинки, чтобы все AI-инструменты использовали общую директорию скиллов
3. Устанавливает универсальную команду `ai` в `~/.local/bin/ai`
4. Добавляет `~/.local/bin` в `PATH` (`.zshrc` / `.bashrc`)
5. Регистрирует хук Claude Code `PreToolUse` для автоопределения скиллов
6. Добавляет индекс скиллов в `~/.claude/CLAUDE.md`

После установки:

```bash
source ~/.zshrc   # перезагрузить PATH
ai --list-skills  # проверить, что всё работает
```

### Использование

#### Универсальная обёртка `ai`

```bash
# Автоопределение скиллов, по умолчанию маршрут — Claude
ai "создай PowerPoint о трендах AI"

# Маршрут к конкретному AI-инструменту
ai -t gemini "напиши Python-скрипт для парсинга JSON"
ai -t codex "отрефактори этот TypeScript-класс"

# Показать, что будет инжектировано, не запуская AI
ai --dry-run "сделай презентацию о микросервисах"

# Список всех зарегистрированных скиллов
ai --list-skills
```

#### Установка скиллов из маркетплейса

```bash
# Установить скилл с aitmpl.com/skills — автоматически регистрируется в registry.json и INDEX.md
ai --add-skill creative-design/frontend-design
ai --add-skill data-science/pandas-expert

# То же самое через dispatch.py напрямую
python3 ~/.shared-ai-skills/dispatch.py add creative-design/frontend-design
```

Установщик:
1. Скачивает через `npx claude-code-templates@latest --skill=<id> --yes`
2. Извлекает ключевые слова из фронтматтера и содержимого `SKILL.md`
3. Предупреждает о возможных дубликатах (≥2 совпадающих ключевых слова с уже установленными)
4. Регистрирует в `registry.json` и добавляет строку в `INDEX.md`

#### `dispatch.py` напрямую

```bash
# Определить нужные скиллы для промпта
python3 ~/.shared-ai-skills/dispatch.py detect "async python crawler"

# Инжектировать контент скилла в промпт (выводит обогащённый промпт в stdout)
python3 ~/.shared-ai-skills/dispatch.py inject "build a REST API"

# Список всех скиллов и их статус (✓ = файл есть, ✗ = отсутствует)
python3 ~/.shared-ai-skills/dispatch.py list

# Вывести содержимое скилла
python3 ~/.shared-ai-skills/dispatch.py show python-pro
```

### Структура директорий

```
~/.shared-ai-skills/
├── dispatch.py          # Ядро: detect / inject / list / show
├── registry.json        # Реестр скиллов: пути + правила триггеров
├── INDEX.md             # Читабельная таблица триггеров (~600 токенов)
├── install.sh           # Установка одной командой
│
├── hooks/
│   ├── pre_tool.sh      # Хук Claude Code PreToolUse
│   └── pre_tool_inject.py
│
├── wrappers/
│   └── ai               # Универсальная обёртка (устанавливается в ~/.local/bin/ai)
│
├── skills/              # Скиллы для документов/плагинов (симлинк в ~/.claude/skills)
│   ├── pptx/SKILL.md
│   ├── docx/SKILL.md
│   ├── xlsx/SKILL.md
│   └── ...
│
├── python-pro/SKILL.md        # Языковые / фреймворковые скиллы
├── typescript-pro/SKILL.md
├── react-patterns/SKILL.md
└── ...                         # 30+ скиллов
```

**Два места хранения:**

| Тип | Путь | Пример |
|---|---|---|
| Языки / фреймворки | `~/.shared-ai-skills/<skill>/SKILL.md` | `python-pro/SKILL.md` |
| Документы / плагины | `~/.shared-ai-skills/skills/<skill>/SKILL.md` | `skills/pptx/SKILL.md` |

> **Важно для обнаружения через Skill tool в Claude Code:** `~/.claude/skills` симлинкован на `~/.shared-ai-skills/` (корень), а не на поддиректорию `skills/`. Claude Code сканирует `~/.claude/skills/*/SKILL.md` (один уровень), поэтому скиллы из `skills/<name>/` **не видны** через Skill tool автоматически. Для их подключения создайте симлинк на верхнем уровне:
> ```bash
> ln -s ~/.shared-ai-skills/skills/planning-with-files ~/.shared-ai-skills/planning-with-files
> ```
> Скиллы, установленные через `dispatch.py add` напрямую в корень, обнаруживаются автоматически.

### Поддерживаемые AI-инструменты

| Инструмент | Интеграция |
|---|---|
| Claude Code | Хук (`PreToolUse`) + симлинк `~/.claude/skills/` |
| Gemini CLI | Симлинк `~/.gemini/skills/` |
| Codex CLI | Симлинк `~/.codex/instructions/` |
| OpenCode | Симлинк `~/.opencode/skills/` |
| Aider | Через `ai -t aider "..."` |
| Cursor | Симлинк `~/.cursor/skills/` |

### Добавление нового скилла

1. Создайте файл скилла:
   ```bash
   mkdir ~/.shared-ai-skills/my-skill
   nano ~/.shared-ai-skills/my-skill/SKILL.md
   ```

2. Зарегистрируйте в `registry.json`:
   ```json
   "my-skill": {
     "path": "my-skill/SKILL.md",
     "description": "Что делает этот скилл",
     "triggers": {
       "keywords": ["ключевое-слово", "другой триггер"],
       "file_extensions": [".ext"],
       "task_patterns": ["создай.*что-то", "напиши.*виджет"]
     }
   }
   ```

3. Добавьте строку в `INDEX.md` для человекочитаемой таблицы.

4. Проверьте:
   ```bash
   python3 dispatch.py detect "ключевое-слово в предложении"
   ```

### Как работают триггеры

Каждый скилл в `registry.json` имеет три типа триггеров (без учёта регистра):

| Тип | Метод сопоставления | Пример |
|---|---|---|
| `keywords` | Подстрока в промпте | `"python"`, `"asyncio"` |
| `file_extensions` | Расширение файла в промпте | `".py"`, `".tsx"` |
| `task_patterns` | Regex-совпадение | `"write.*python"`, `"create.*\\.py"` |

Скилл активируется, если совпадает **хотя бы один** триггер.

### Двуязычная поддержка (EN + RU)

Все 38 встроенных скиллов имеют тригерные слова на русском языке. Промпты на русском определяются автоматически:

```bash
python3 dispatch.py detect "написать скрипт на питоне"
# → SKILLS:python-pro

python3 dispatch.py detect "спроектировать архитектуру системы"
# → SKILLS:software-architecture
```

**Нормализация падежей**: диспетчер автоматически убирает типичные падежные окончания (`а`, `я`, `ы`, `и`, `е`, `у`, `ю`) перед сравнением, поэтому все формы слов работают без перечисления каждого склонения в реестре:

| Слово в промпте | Нормализованное | Ключевое слово в реестре |
|---|---|---|
| `архитектуру` | `архитектур` | `архитектура` ✓ |
| `агента` | `агент` | `агент` ✓ |
| `микросервисов` | `микросервисо` | `микросервисы` → `микросервис` ✓ |

### Бюджет токенов

`dispatch.py` контролирует лимиты при инжекции контента:

- Максимум на один скилл: **~4 000 токенов** (16 000 символов)
- Максимум суммарно: **~12 000 токенов** (48 000 символов)

Контент обрезается при превышении лимита.
