```
  ██████╗ ██╗       █████╗  ██╗   ██╗ ██████╗  ███████╗
 ██╔════╝ ██║      ██╔══██╗ ██║   ██║ ██╔══██╗ ██╔════╝
 ██║      ██║      ███████║ ██║   ██║ ██║  ██║ █████╗
 ██║      ██║      ██╔══██║ ██║   ██║ ██║  ██║ ██╔══╝
 ╚██████╗ ███████╗ ██║  ██║ ╚██████╔╝ ██████╔╝ ███████╗
  ╚═════╝ ╚══════╝ ╚═╝  ╚═╝  ╚═════╝  ╚═════╝  ╚══════╝

  ██████╗  ██████╗  ███╗   ██╗ ████████╗ ███████╗ ██╗  ██╗ ████████╗
 ██╔════╝ ██╔═══██╗ ████╗  ██║ ╚══██╔══╝ ██╔════╝ ╚██╗██╔╝ ╚══██╔══╝
 ██║      ██║   ██║ ██╔██╗ ██║    ██║    █████╗    ╚███╔╝     ██║
 ██║      ██║   ██║ ██║╚██╗██║    ██║    ██╔══╝    ██╔██╗     ██║
 ╚██████╗ ╚██████╔╝ ██║ ╚████║    ██║    ███████╗ ██╔╝ ██╗    ██║
  ╚═════╝  ╚═════╝  ╚═╝  ╚═══╝    ╚═╝    ╚══════╝ ╚═╝  ╚═╝    ╚═╝

 ██╗       ██████╗   ██████╗  █████╗  ██╗
 ██║      ██╔═══██╗ ██╔════╝ ██╔══██╗ ██║
 ██║      ██║   ██║ ██║      ███████║ ██║
 ██║      ██║   ██║ ██║      ██╔══██║ ██║
 ███████╗ ╚██████╔╝ ╚██████╗ ██║  ██║ ███████╗
 ╚══════╝  ╚═════╝   ╚═════╝ ╚═╝  ╚═╝ ╚══════╝

```

[![Seeking Remote Work](https://img.shields.io/badge/🌍-Actively%20Seeking%20Remote%20Work-success?style=for-the-badge)](mailto:farhanalirazaazeemi@gmail.com)

Claude Context without the cloud. Semantic code search that runs 100% locally using EmbeddingGemma. No API keys, no costs, your code never leaves your machine.

- 🔍 **Find code by meaning, not strings** - grep-like CLI for semantic search
- 🔒 **100% local - completely private** - your code never leaves your machine
- 💰 **Zero API costs - forever free** - no API keys needed
- ⚡ **Fewer tokens in Claude Code** - fast local searches via CLI or MCP
- 🖥️ **Hybrid CLI + MCP** - use from terminal or integrate with Claude Code

An intelligent code search system that uses Google's EmbeddingGemma model and advanced multi-language chunking to provide semantic search capabilities across 15 file extensions and 9+ programming languages. Use it as a **grep-like CLI tool** or integrate with Claude Code via MCP (Model Context Protocol).

## 🚧 Beta Release

- Core functionality working
- Installation tested on Mac/Linux
- Benchmarks coming soon
- Please report issues!

## Demo

<img src="https://github.com/FarhanAliRaza/claude-context-local/releases/download/v0.1/example.gif" alt="Demo of local semantic code search" width="900" />

## Features

- **Multi-language support**: 9+ programming languages with 15 file extensions
- **Intelligent chunking**: AST-based (Python) + tree-sitter (JS/TS/Go/Java/Rust/C/C++/C#)
- **Semantic search**: Natural language queries to find code across all languages
- **Rich metadata**: File paths, folder structure, semantic tags, language-specific info
- **MCP integration**: Direct integration with Claude Code
- **Local processing**: All embeddings stored locally, no API calls
- **Fast search**: FAISS for efficient similarity search

## Why this

Claude’s code context is powerful, but sending your code to the cloud costs tokens and raises privacy concerns. This project keeps semantic code search entirely on your machine. It integrates with Claude Code via MCP, so you keep the same workflow—just faster, cheaper, and private.

## Requirements

- Python 3.12+
- Disk: 1–2 GB free (model + caches + index)
- Optional: NVIDIA GPU (CUDA 11/12) for FAISS acceleration; Apple Silicon (MPS) for embedding acceleration. These also speed up running the embedding model with SentenceTransformer, but everything still works on CPU.

## Install & Update

### Install (one‑liner)

```bash
curl -fsSL https://raw.githubusercontent.com/FarhanAliRaza/claude-context-local/main/scripts/install.sh | bash
```

If your system doesn't have `curl`, you can use `wget`:

```bash
wget -qO- https://raw.githubusercontent.com/FarhanAliRaza/claude-context-local/main/scripts/install.sh | bash
```

### Update existing installation

Run the same install command to update:

```bash
curl -fsSL https://raw.githubusercontent.com/FarhanAliRaza/claude-context-local/main/scripts/install.sh | bash
```

The installer will:

- Detect your existing installation
- Preserve your embeddings and indexed projects in `~/.claude_code_search`
- Stash any local changes automatically (if running via curl)
- Update the code and dependencies

### What the installer does

- Installs `uv` if missing and creates a project venv
- Clones/updates `claude-context-local` in `~/.local/share/claude-context-local`
- Installs Python dependencies with `uv sync`
- Creates the `csearch` CLI command
- Downloads the EmbeddingGemma model (~1.2–1.3 GB) if not already cached
- Tries to install `faiss-gpu` if an NVIDIA GPU is detected (interactive mode only)
- **Preserves all your indexed projects and embeddings** across updates

### Alternative: pip/pipx install

```bash
# With pip
pip install .

# With pipx (recommended for CLI tools)
pipx install .

# With uv
uv tool install .
```

After installation, the `csearch` command is available globally.

## Quick Start

### For Existing Claude Code Users

If you already have Claude Code and want to add local semantic search:

```bash
# 1. Install csearch (one command)
curl -fsSL https://raw.githubusercontent.com/FarhanAliRaza/claude-context-local/main/scripts/install.sh | bash

# 2. Add the MCP server to Claude Code
claude mcp add code-search --scope user -- uv run --directory ~/.local/share/claude-context-local python mcp_server/server.py

# 3. Restart Claude Code and ask it to "index this codebase"
```

That's it! Claude Code will now use local semantic search instead of sending your code to the cloud.

### CLI Usage (Recommended)

The `csearch` command provides grep-like semantic code search:

```bash
# Index your project (first time)
csearch index

# Search for code semantically
csearch "authentication handling"
csearch "where is rate limiting implemented"
csearch "database connection pooling"

# Search with filters
csearch -m 10 "error handling"           # Max 10 results
csearch -f "*.py" "async function"       # Python files only
csearch -l python "class definition"     # Filter by language
csearch -t function "validate"           # Filter by chunk type

# Output formats
csearch --json "auth"                    # JSON output
csearch -1 "config"                      # Compact (path:line only)
csearch -v "middleware"                  # Verbose with scores

# Exact and hybrid search
csearch --exact "handleUserLogin"        # Exact text match (uses ripgrep)
csearch --hybrid "authentication" "JWT"  # Semantic + exact filter

# Other commands
csearch status                           # Show index info
csearch watch                            # Auto-reindex on file changes
csearch watch --daemon                   # Background file watcher
csearch config                           # View configuration
csearch doctor                           # Check dependencies
```

### MCP Integration (Claude Code)

If you already have Claude Code installed and want to add semantic code search, follow these steps:

#### 1) Register the MCP server

**If you installed via the one-liner script (recommended):**

```bash
# Global (available in all projects)
claude mcp add code-search --scope user -- uv run --directory ~/.local/share/claude-context-local python mcp_server/server.py

# Or project-specific (only in current directory)
claude mcp add code-search -- uv run --directory ~/.local/share/claude-context-local python mcp_server/server.py
```

**If you installed via pip/pipx/uv or cloned manually:**

```bash
# Replace /path/to/claude-context-local with your actual installation path
claude mcp add code-search --scope user -- uv run --directory /path/to/claude-context-local python mcp_server/server.py
```

#### 2) Verify the MCP server is registered

```bash
claude mcp list
```

You should see `code-search` in the list of registered servers.

#### 3) Index your codebase

Open Claude Code in your project and say:

> "Index this codebase"

Or use the CLI first:

```bash
csearch index /path/to/your/project
```

#### 4) Search in Claude Code

Once indexed, simply ask Claude Code questions like:

> "Find the authentication handling code"
> "Where is rate limiting implemented?"
> "Show me the database connection logic"

Claude will use the local semantic search automatically.

#### Updating or Removing the MCP Server

```bash
# Remove existing server
claude mcp remove code-search

# Re-add with updated path (after update)
claude mcp add code-search --scope user -- uv run --directory ~/.local/share/claude-context-local python mcp_server/server.py
```

#### MCP Troubleshooting

If the MCP server isn't working:

1. **Check registration**: `claude mcp list` should show `code-search`
2. **Check logs**: Look for errors in Claude Code's MCP output
3. **Verify path**: Ensure the directory path in `claude mcp add` is correct
4. **Test manually**: Try `uv run --directory ~/.local/share/claude-context-local python mcp_server/server.py` to see startup errors
5. **Re-register**: Remove and re-add the server after updates

## Architecture

```
csearch/
├── cli/                              # CLI interface (grep-like)
│   ├── main.py                       # Entry point and command registration
│   ├── commands/                     # CLI commands (search, index, status, watch, etc.)
│   └── output/                       # Output formatters (grep, JSON, compact, verbose)
├── core/                             # Shared business logic
│   ├── config.py                     # TOML configuration management
│   ├── project.py                    # Project and index management
│   └── search_engine.py              # Unified search interface
├── chunking/                         # Multi-language chunking (15 extensions)
│   ├── multi_language_chunker.py     # Unified orchestrator (Python AST + tree-sitter)
│   ├── python_ast_chunker.py         # Python-specific chunking (rich metadata)
│   └── tree_sitter.py                # Tree-sitter: JS/TS/JSX/TSX/Svelte/Go/Java/Rust/C/C++/C#
├── embeddings/
│   └── embedder.py                   # EmbeddingGemma; device=auto (CUDA→MPS→CPU); offline cache
├── search/
│   ├── indexer.py                    # FAISS index (CPU by default; GPU when available)
│   ├── searcher.py                   # Intelligent ranking & filters
│   └── incremental_indexer.py        # Merkle-driven incremental indexing
├── merkle/
│   ├── merkle_dag.py                 # Content-hash DAG of the workspace
│   ├── change_detector.py            # Diffs snapshots to find changed files
│   └── snapshot_manager.py           # Snapshot persistence & stats
├── mcp_server/
│   └── server.py                     # MCP tools for Claude Code (stdio/HTTP)
└── scripts/
    ├── install.sh                    # One-liner remote installer (uv + model + faiss)
    ├── download_model_standalone.py  # Pre-fetch embedding model
    └── index_codebase.py             # Standalone indexing utility
```

### Data flow

```mermaid
graph TD
    A["Claude Code (MCP client)"] -->|index_directory| B["MCP Server"]
    B --> C{IncrementalIndexer}
    C --> D["ChangeDetector<br/>(Merkle DAG)"]
    C --> E["MultiLanguageChunker"]
    E --> F["Code Chunks"]
    C --> G["CodeEmbedder<br/>(EmbeddingGemma)"]
    G --> H["Embeddings"]
    C --> I["CodeIndexManager<br/>(FAISS CPU/GPU)"]
    H --> I
    D --> J["SnapshotManager"]
    C --> J
    B -->|search_code| K["Searcher"]
    K --> I
```

## Intelligent Chunking

The system uses advanced parsing to create semantically meaningful chunks across all supported languages:

### Chunking Strategies

- **Python**: AST-based parsing for rich metadata extraction
- **All other languages**: Tree-sitter parsing with language-specific node type recognition

### Chunk Types Extracted

- **Functions/Methods**: Complete with signatures, docstrings, decorators
- **Classes/Structs**: Full definitions with member functions as separate chunks
- **Interfaces/Traits**: Type definitions and contracts
- **Enums/Constants**: Value definitions and module-level declarations
- **Namespaces/Modules**: Organizational structures
- **Templates/Generics**: Parameterized type definitions

### Rich Metadata for All Languages

- File path and folder structure
- Function/class/type names and relationships
- Language-specific features (async, generics, modifiers, etc.)
- Parent-child relationships (methods within classes)
- Line numbers for precise code location
- Semantic tags (component, export, async, etc.)

## Configuration

### CLI Configuration

The CLI uses a TOML configuration file at `~/.config/csearch/config.toml`:

```toml
[general]
storage_dir = "~/.claude_code_search"
default_threshold = 0.4
max_results = 20

[model]
name = "google/embeddinggemma-300m"
device = "auto"  # auto, cuda, mps, cpu
batch_size = 32

[index]
excluded_dirs = ["node_modules", ".venv", "__pycache__", ".git", "dist"]
max_file_size_kb = 1024

[watch]
debounce_ms = 2000
auto_start = false

[output]
context_lines = 0
show_score = false
color = "auto"  # auto, always, never
```

Manage configuration with:
```bash
csearch config                    # View current config
csearch config --edit             # Open in $EDITOR
csearch config set threshold 0.5  # Set a value
```

### Environment Variables

- `CODE_SEARCH_STORAGE`: Custom storage directory (default: `~/.claude_code_search`)

### Model Configuration

The system uses `google/embeddinggemma-300m` by default.

Notes:

- Download size: ~1.2–2 GB on disk depending on variant and caches
- Device selection: auto (CUDA on NVIDIA, MPS on Apple Silicon, else CPU)
- You can pre-download via installer or at first use
- FAISS backend: CPU by default. If an NVIDIA GPU is detected, the installer
  attempts to install `faiss-gpu-cu12` (or `faiss-gpu-cu11`) and the index will
  run on GPU automatically at runtime while saving as CPU for portability.

#### Hugging Face authentication (if prompted)

The `google/embeddinggemma-300m` model is hosted on Hugging Face and may require
accepting terms and/or authentication to download.

1. Visit the model page and accept any terms:

   - https://huggingface.co/google/embeddinggemma-300m

2. Authenticate one of the following ways:

   - CLI (recommended):

     ```bash
     uv run huggingface-cli login
     # Paste your token from https://huggingface.co/settings/tokens
     ```

   - Environment variable:
     ```bash
     export HUGGING_FACE_HUB_TOKEN=hf_XXXXXXXXXXXXXXXXXXXXXXXX
     ```

After the first successful download, we cache the model under `~/.claude_code_search/models`
and prefer offline loads for speed and reliability.

### Supported Languages & Extensions

**Fully Supported (15 extensions across 9+ languages):**

| Language       | Extensions                    |
| -------------- | ----------------------------- |
| **Python**     | `.py`                         |
| **JavaScript** | `.js`, `.jsx`                 |
| **TypeScript** | `.ts`, `.tsx`                 |
| **Java**       | `.java`                       |
| **Go**         | `.go`                         |
| **Rust**       | `.rs`                         |
| **C**          | `.c`                          |
| **C++**        | `.cpp`, `.cc`, `.cxx`, `.c++` |
| **C#**         | `.cs`                         |
| **Svelte**     | `.svelte`                     |

**Total**: **15 file extensions** across **9+ programming languages**

## Storage

Data is stored in the configured storage directory:

```
~/.claude_code_search/
├── models/          # Downloaded models
├── index/           # FAISS indices and metadata
│   ├── code.index   # Vector index
│   ├── metadata.db  # Chunk metadata (SQLite)
│   └── stats.json   # Index statistics
```

## Performance

- **Model size**: ~1.2GB (EmbeddingGemma-300m and caches)
- **Embedding dimension**: 768 (can be reduced for speed)
- **Index types**: Flat (exact) or IVF (approximate) based on dataset size
- **Batch processing**: Configurable batch sizes for embedding generation

Tips:

- First index on a large repo will take time (model load + chunk + embed). Subsequent runs are incremental.
- With GPU FAISS, searches on large indexes are significantly faster.
- Embeddings automatically use CUDA (NVIDIA) or MPS (Apple) if available.

## Troubleshooting

### Quick Diagnostics

Run the built-in doctor command to check your setup:

```bash
csearch doctor
```

This verifies Python version, dependencies, model availability, and GPU support.

### Common Issues

1. **Import errors**: Ensure all dependencies are installed with `uv sync`
2. **Model download fails**: Check internet connection and disk space (~1.2GB needed)
3. **Memory issues**: Reduce batch size in config: `csearch config set batch_size 16`
4. **No search results**: Verify the codebase was indexed: `csearch status`
5. **FAISS GPU not used**: Ensure `nvidia-smi` is available and CUDA drivers are installed; re-run installer to pick `faiss-gpu-cu12`/`cu11`.
6. **Force offline**: We auto-detect a local cache and prefer offline loads; you can also set `HF_HUB_OFFLINE=1`.

### MCP Server Issues

1. **MCP server not found**: Re-register with `claude mcp add code-search --scope user -- uv run --directory ~/.local/share/claude-context-local python mcp_server/server.py`
2. **Tools not appearing**: Restart Claude Code after adding the MCP server
3. **Connection errors**: Test the server manually: `uv run --directory ~/.local/share/claude-context-local python mcp_server/server.py`
4. **Wrong index used**: Each project has its own index; run `csearch index` in the correct directory

### Ignored directories (for speed and noise reduction)

`node_modules`, `.venv`, `venv`, `env`, `.env`, `.direnv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.pytype`, `.ipynb_checkpoints`, `build`, `dist`, `out`, `public`, `.next`, `.nuxt`, `.svelte-kit`, `.angular`, `.astro`, `.vite`, `.cache`, `.parcel-cache`, `.turbo`, `coverage`, `.coverage`, `.nyc_output`, `.gradle`, `.idea`, `.vscode`, `.docusaurus`, `.vercel`, `.serverless`, `.terraform`, `.mvn`, `.tox`, `target`, `bin`, `obj`

## Contributing

This is a research project focused on intelligent code chunking and search. Feel free to experiment with:

- Different chunking strategies
- Alternative embedding models
- Enhanced metadata extraction
- Performance optimizations

## License

Licensed under the GNU General Public License v3.0 (GPL-3.0). See the `LICENSE` file for details.

## Inspiration

This project draws inspiration from [zilliztech/claude-context](https://github.com/zilliztech/claude-context). I adapted the concepts to a Python implementation with fully local embeddings.
