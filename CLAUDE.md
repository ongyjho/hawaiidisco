# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Dev setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,all]"

# Run
hawaiidisco                    # entry point
python -m hawaiidisco          # via __main__.py

# Test
pytest -v                      # all tests
pytest tests/test_db.py -v     # single file
pytest -k "test_name" -v       # single test

# Lint
ruff check hawaiidisco/ tests/  # py311, line-length=120

# Build
python -m build                # hatchling backend → dist/
```

## Architecture

Textual TUI app with AI-powered RSS reading. Entry point: `hawaiidisco/app.py:main()`.

### Core Flow
1. **Config** (`config.py`) — YAML loader with `${ENV_VAR}` resolution, dataclass-based
2. **Fetch** (`fetcher.py`) — feedparser + SHA256 article ID hashing → SQLite upsert
3. **Display** (`app.py:HawaiiDiscoApp`) — Textual App with modal screens, `widgets/` for timeline/detail/status
4. **AI** (`ai/`) — Protocol-based providers, background threads via `@work(thread=True)`
5. **Persist** — SQLite (articles/insights/translations), Markdown (bookmark export)

### Threading Model
- Main thread: Textual event loop
- Worker threads: feed fetch, AI calls (subprocess/API)
- Thread-safe DB: `threading.local()` per-thread connections, WAL mode
- Worker → UI: `call_from_thread()` only

### AI Provider Pattern
`ai/base.py` defines `AIProvider` Protocol (`generate`, `is_available`, `name`). Implementations: `claude_cli.py` (subprocess), `anthropic_api.py`, `openai_api.py`. Factory: `ai/__init__.py:get_provider()`. `anthropic`/`openai` are optional extras.

### Prompt Pattern
Single English template in `ai/prompts.py` with `{output_language}` injection for bilingual output.

### i18n
`i18n.py`: `_STRINGS` dict keyed by `Lang.EN`/`Lang.KO`. Call `t(key, **kwargs)` for translated strings.

### DB Migrations
New columns added in `Database._migrate()` (not schema init). Migrations run automatically on startup.

## Key Conventions

- **Security**: `_safe_path()` for path traversal defense in bookmark export, `_slugify()` for filenames, parameterized SQL (`?`), `shell=False` subprocess, Rich markup `_escape()` for external data
- **Config paths**: `~/.config/hawaiidisco/config.yml`, `~/.local/share/hawaiidisco/hawaiidisco.db`, dirs created with `0o700`
- **Bilingual UI**: all user-facing strings via `t()`, Korean preserved in slugify
- **Type hints**: `from __future__ import annotations` throughout
- **Commit style**: `type: description` in English (feat, fix, chore, refactor, docs)

## Remotes

- `origin`: `whale-millie/hd.git` (private)
- `public`: `ongyjho/hawaiidisco.git` (public, PyPI source)
