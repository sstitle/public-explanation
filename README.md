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

- Python 3.13+
- OpenAI API key
- `mods` and `glow` CLI tools installed

### Installation

1. Clone and set up the project:
```bash
git clone <your-repo-url>
cd public-explanation
uv sync
```

2. **TODO: Create your .env file with your OpenAI API key:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. Install external CLI tools:
```bash
# Install mods (AI CLI tool)
# See: https://github.com/charmbracelet/mods

# Install glow (markdown renderer)  
# See: https://github.com/charmbracelet/glow
```

### Usage

```bash
# Ask about a specific repository
python -m public_explanation "facebook/react" "how does the virtual DOM work?"

# Search for a repository and ask a question
python -m public_explanation "react router" "how do I set up nested routes?"

# Use full GitHub URLs
python -m public_explanation "https://github.com/microsoft/vscode" "how does the extension system work?"

# Dry run to see what would be processed
python -m public_explanation "small-repo" "test question" --dry-run --verbose
```

## Development Status

🚧 **Currently in Phase 1**: Foundation & Basic CLI
- ✅ Project setup and dependencies
- 🔄 Repository discovery implementation
- ⏳ Content processing integration

See `scratchpad.md` for detailed development plan and progress.

## Architecture

- **gitingest**: Repository content extraction and prompt-friendly digestion
- **mods**: OpenAI API integration with conversation support
- **glow**: Beautiful terminal markdown rendering  
- **Python**: CLI orchestration and repository discovery
