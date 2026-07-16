# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Essential Commands (use these exact commands):**
- `uv run poe format` - Format code (RUFF) - ONLY allowed formatting command
- `uv run poe type-check` - Run `ty` type checking (`ty check`; replaced mypy) - ONLY allowed type checking command
- `uv run poe test` - Run tests with default markers (excludes java/rust by default)
- `uv run poe test -m "python or go"` - Run specific language tests
- `uv run poe test -m vue` - Run Vue tests
- `uv run poe lint` - Check code style without fixing (ruff format --check + ruff check)

**Test Markers:**
59 pytest markers are registered as of v1.5.4.dev0. The authoritative list is
`[tool.pytest.ini_options].markers` in `pyproject.toml` — consult it rather than trusting this snapshot.
- Core languages: `python`, `go`, `java`, `kotlin`, `groovy`, `rust`, `typescript`, `vue`, `php`, `perl`, `powershell`, `csharp`, `elixir`, `elm`, `terraform`, `clojure`, `swift`, `bash`, `ruby`, `r`, `zig`, `lua`, `luau`, `nix`, `dart`, `erlang`, `ocaml`, `scala`, `al`, `fsharp`, `rego`, `markdown`, `julia`, `fortran`, `haskell`, `yaml`, `pascal`, `cpp`, `toml`, `matlab`, `systemverilog`, `hlsl`, `lean4`, `solidity`, `ansible`
- Newer language markers: `ada`, `angular`, `bsl`, `crystal`, `cue`, `haxe`, `html`, `json`, `latex`, `msl`, `scss`, `svelte`
- `snapshot` - for symbolic editing operation tests
- `slow` - tests requiring extra Expert instances (~60-90s startup)

(Note: alternative language-server variants such as `python_jedi`, `csharp_omnisharp`, `ruby_solargraph`, `typescript_vts`, `php_phpactor` are `.serena/project.yml` language options, NOT pytest markers — do not pass them to `-m`.)

**Project Management (CLI subcommands, not standalone scripts):**
- `uv run serena` - Main CLI entry point (top-level command; installed scripts: `serena`, `serena-agent`, `serena-hooks`)
- `uv run serena start-mcp-server` - Start the MCP server (there is no `serena-mcp-server` script; it is a subcommand)
- `uv run serena index` - Index a project for faster tool performance (the old `index-project` script is removed; the positional project arg is deprecated — use `--project`)

**Always run format, type-check, and test before completing any task.**

## Architecture Overview

Serena is a dual-layer coding agent toolkit:

### Core Components

**1. SerenaAgent (`src/serena/agent.py`)**
- Central orchestrator managing projects, tools, and user interactions
- Coordinates language servers, memory persistence, and MCP server interface
- Manages tool registry and context/mode configurations

**2. SolidLanguageServer (`src/solidlsp/ls.py`)**
- Unified wrapper around Language Server Protocol (LSP) implementations
- Provides language-agnostic interface for symbol operations
- Handles caching, error recovery, and multiple language server lifecycle

**3. Tool System (`src/serena/tools/`)**
- **file_tools.py** - File system operations, search, regex replacements
- **symbol_tools.py** - Language-aware symbol finding, navigation, editing
- **memory_tools.py** - Project knowledge persistence and retrieval
- **config_tools.py** - Project activation, mode switching
- **workflow_tools.py** - Onboarding and meta-operations

**4. Configuration System (`src/serena/config/`)**
- **Contexts** - Define tool sets for different environments. Available: `agent`, `claude-code`, `codex`, `chatgpt`, `desktop-app`, `ide`, `oaicompat-agent` (`ide-assistant` is a legacy alias resolving to `claude-code`, see `src/serena/config/context_mode.py`)
- **Modes** - Operational patterns (planning, editing, interactive, one-shot)
- **Projects** - Per-project settings and language server configs

### Language Support Architecture

Each supported language has:
1. **Language Server Implementation** in `src/solidlsp/language_servers/`
2. **Runtime Dependencies** - Automatic language server downloads when needed
3. **Test Repository** in `test/resources/repos/<language>/`
4. **Test Suite** in `test/solidlsp/<language>/`

### Memory & Knowledge System

- **Markdown-based storage** in `.serena/memories/` directories
- **Project-specific knowledge** persistence across sessions
- **Contextual retrieval** based on relevance
- **Onboarding support** for new projects

## Development Patterns

### Adding New Languages
1. Create language server class in `src/solidlsp/language_servers/`
2. Add to Language enum in `src/solidlsp/ls_config.py`
3. Update factory method in `src/solidlsp/ls.py`
4. Create test repository in `test/resources/repos/<language>/`
5. Write test suite in `test/solidlsp/<language>/`
6. Add pytest marker to `pyproject.toml`

### Adding New Tools
1. Inherit from `Tool` base class in `src/serena/tools/tools_base.py`
2. Implement required methods and parameter validation
3. Register in appropriate tool registry
4. Add to context/mode configurations

### Testing Strategy
- Language-specific tests use pytest markers
- Symbolic editing operations have snapshot tests
- Integration tests in `test_serena_agent.py`
- Test repositories provide realistic symbol structures

## Configuration Hierarchy

Configuration is loaded from (in order of precedence):
1. Command-line arguments to `serena start-mcp-server`
2. Project-specific `.serena/project.yml`
3. User config `~/.serena/serena_config.yml`
4. Active modes and contexts

## Key Implementation Notes

- **Symbol-based editing** - Uses LSP for precise code manipulation
- **Caching strategy** - Reduces language server overhead
- **Error recovery** - Automatic language server restart on crashes
- **Multi-language support** - 50+ languages with LSP integration (including Vue, Solidity, Ansible, Lean 4, Angular, Svelte)
- **MCP protocol** - Exposes tools to AI agents via Model Context Protocol
- **Async operation** - Non-blocking language server interactions

## Working with the Codebase

- Project targets Python `>=3.11, <3.15` with `uv` for dependency management
- Strict typing with `ty`, formatted with ruff
- Language servers run as separate processes with LSP communication
- Memory system enables persistent project knowledge
- Context/mode system allows workflow customization

## Guardrails

- This is a **fork** of [oraios/serena](https://github.com/oraios/serena). Upstream URL: `https://github.com/oraios/serena`. **Canonical fork: `artificemachine/serena`** (`git@github.com:artificemachine/serena.git`) — all installs are pinned to it. `celstnblacc/serena` is a legacy/secondary remote (was 2 commits behind `artificemachine/main` at the 2026-07-16 sync).
- Security fixes must not be reverted. Verify with `uv run pytest test/serena/test_security.py` after any change to the guarded files:
  - **S-1** shell metacharacter guard: `src/serena/util/shell.py` (`_validate_no_shell_metacharacters`, enforced in `execute_shell_command`; labelled `SEC-002` in source).
  - **S-2** memory path-traversal guard: `src/serena/memories/memory_manager.py` (`MemoryManager.get_memory_file_path`). Note: this is NOT `project.py` — `project.py` carries a separate project-relative path check.
- Never push directly to `main`. Feature branches only.
- Never edit `.env`, credentials, or secret files.
- Run `uv run poe format && uv run poe type-check && uv run poe test` before any commit.
- Prefer the `serena` CLI subcommands (`serena index`, `serena start-mcp-server`, `serena project`); the standalone `index-project`/`serena-mcp-server` scripts no longer exist.
- Do not add dependencies without pinning exact (`==`) versions. This is a security constraint: `uvx`/`uv tool install` builds from git and ignores the lock file, so exact pins in `pyproject.toml` are the only enforced version boundary (see the "pinned for security" block in `[project.optional-dependencies].dev`).

## Strict Installation Decoupling

Once installed (e.g., to `~/.local/bin`), the project binary must NEVER depend on the local repository path for execution, configuration, or data. All paths must be relative to the installation root or use standard system config paths (`~/.config`).

The installed binary is pinned to the fork via git, never a local worktree:
`uv tool install --force --from "git+https://github.com/artificemachine/serena.git@<rev>" serena-agent`.
Confirm with the `requirements` line in `~/.local/share/uv/tools/serena-agent/uv-receipt.toml` — it must show a `git = "...artificemachine/serena.git?rev=..."` source, not a local `directory`.
