# Public Explanation

AI-powered GitHub repository explanation tool that combines gitingest, mods, and glow to provide intelligent explanations of any public GitHub repository using natural language questions.

## Features

- 🔍 **Smart Repository Discovery**: Find repos by name, URL, or fuzzy search
- 🧠 **AI-Powered Analysis**: Uses OpenAI GPT-4o for intelligent code explanation
- 📝 **Beautiful Output**: Rendered markdown explanations via glow
- 💰 **Token Efficient**: Smart content filtering and caching to minimize API costs
- 🚀 **Fast & Interactive**: Progressive loading with conversation support

## Quick Start

### Prerequisites

- [Nix](https://nixos.org/download.html) with flakes enabled
- OpenAI API key

### Installation

```bash
git clone <your-repo-url>
cd public-explanation

# Enter development shell with all dependencies
nix develop

# Install Python dependencies
uv sync

# Run the tool
uv run python -m public_explanation "octocat/Hello-World" "what does this repository do?"
```

The Nix flake automatically provides:
- Python 3.13+ with uv package manager
- `mods` CLI tool for AI integration
- `glow` CLI tool for markdown rendering
- `mask` for task automation
- All required system dependencies

### Configuration

Create a `.env` file with your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

#### Cost Management

The tool includes built-in cost safety features:
- Estimates token costs before making AI calls
- Requires confirmation for requests over 5¢
- Shows repository size and processing details
- Use `--dry-run` to preview without API calls
- Use `--force` to bypass confirmations

#### Repository Discovery

The tool intelligently handles various input formats:
- **Direct URLs**: `https://github.com/owner/repo`
- **Owner/Repo**: `facebook/react`
- **Search Terms**: `"react router"` (shows interactive selection)
- **Fuzzy Matching**: Finds repositories even with partial names

#### Advanced Options

```bash
# Customize AI model
python -m public_explanation "repo" "question" --model gpt-4o-mini

# Adjust content processing limits
python -m public_explanation "repo" "question" --max-file-size 2 --max-total-size 100

# Development mode without GitHub API
python -m public_explanation "repo" "question" --no-api

# Verbose output for debugging
python -m public_explanation "repo" "question" --verbose
```

## Development

### Nix Development Environment

The project uses Nix flakes for reproducible development environments:

```bash
# Enter the development shell (includes all dependencies)
nix develop

direnv allow
```

The development shell provides:
- Python 3.13+ with uv package manager
- All required CLI tools (`mods`, `glow`, `mask`)
- Consistent development environment across systems
- Isolated dependencies without system pollution

## Architecture

- **gitingest**: Repository content extraction and prompt-friendly digestion
- **mods**: OpenAI API integration with conversation support
- **glow**: Beautiful terminal markdown rendering  
- **Python**: CLI orchestration and repository discovery
