# HephAIstos 🔥

**HephAIstos** is an autonomous coding assistant powered by ReAct (Reasoning and Acting) methodology. Named after the Greek god of fire and forge, HephAIstos helps you build, modify, and manage code projects through natural language conversations.

## Demo

[![Watch the video](https://img.youtube.com/vi/YIwN4l4LuxI/3.jpg)](https://youtu.be/YIwN4l4LuxI?si=eUqtSghwDqh1QEZ7)

## About

```

 ▄    ▄               █        █▀     ▄▄   ▄▄▄▄▄   ▀█             ▄
 █    █  ▄▄▄   ▄▄▄▄   █ ▄▄     █      ██     █      █     ▄▄▄   ▄▄█▄▄  ▄   ▄   ▄▄▄
 █▄▄▄▄█ █▀  █  █▀ ▀█  █▀  █    █     █  █    █      █    █   ▀    █    █   █  █   ▀
 █    █ █▀▀▀▀  █   █  █   █    █     █▄▄█    █      █     ▀▀▀▄    █    █   █   ▀▀▀▄
 █    █ ▀█▄▄▀  ██▄█▀  █   █    █    █    █ ▄▄█▄▄    █    ▀▄▄▄▀    ▀▄▄  ▀▄▄▀█  ▀▄▄▄▀
               █               ▀▀                  ▀▀
               ▀
```

## ✨ Features

- **Autonomous Code Generation**: Write, modify, and organize code files through natural language
- **Intelligent File Operations**: Read, write, append, patch, and search files with context awareness
- **Git Integration**: Automated version control with add, commit, and push capabilities
- **Web Search**: Real-time web search integration for up-to-date information
- **Interactive CLI**: Beautiful command-line interface with syntax highlighting and progress indicators
- **Context-Aware**: Maintains session context and understands file relationships
- **Safety Features**: Built-in guardrails against unsafe operations

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **API Keys** (set in `.env` file):
   ```env
   GROQ_API_KEY=your_groq_api_key
   EXA_API_KEY=your_exa_api_key
   ```

### Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd hephaistus
   ```

2. Install dependencies:

   ```bash
   pip install groq openai python-dotenv
   ```

3. Set up your `.env` file with required API keys

4. Run HephAIstos:
   ```bash
   python hephaistus.py
   ```

## 🛠️ Available Tools

| Tool                   | Description                       |
| ---------------------- | --------------------------------- |
| `chat`                 | General conversation and advice   |
| `read_file`            | Read file contents                |
| `write_file`           | Create or overwrite files         |
| `append_file`          | Append content to existing files  |
| `list_dir`             | List directory contents           |
| `search_text_in_files` | Search for text across files      |
| `patch_file`           | Apply line-based changes to files |
| `run_python_script`    | Execute Python scripts safely     |
| `search_web`           | Search the web for information    |
| `git_add`              | Stage files for commit            |
| `git_commit`           | Commit changes with message       |
| `git_push`             | Push commits to remote repository |

## 💡 Usage Examples

### Basic File Operations

```
🔎 Enter your goal: Create a Python script that calculates fibonacci numbers and save it as fib.py
```

### Code Modification

```
🔎 Enter your goal: Add error handling to the last file I created
```

### Project Setup

```
🔎 Enter your goal: Set up a new Flask web application with routes for home and about pages
```

### Git Workflow

```
🔎 Enter your goal: Review my changes and commit them with an appropriate message
```

## 🎯 CLI Commands

- `:help` - Show available commands
- `:tools` - List all available tools
- `:state` - Display current agent context
- `:clear` - Clear the screen
- `:ls [path]` - List files in directory
- `:quit` / `:exit` - Exit the application

## 🧠 How It Works

HephAIstos uses the **ReAct (Reasoning and Acting)** framework:

1. **Reasoning**: The agent thinks through the problem step by step
2. **Acting**: Takes concrete actions using available tools
3. **Observing**: Processes results and adjusts the approach
4. **Iterating**: Continues until the goal is achieved

### Context Awareness

The agent maintains context about:

- Recently modified files
- Active workspace structure
- Previous operations and their results
- Session history and patterns

## 🔒 Safety Features

- **Path Validation**: Prevents access to parent directories (`../`)
- **Safe Execution**: Python scripts are scanned for unsafe operations
- **File Deletion Disabled**: Delete operations are blocked by policy
- **Error Handling**: Robust exception handling throughout the system

## ⚙️ Configuration

### Workspace Context

The agent automatically analyzes your workspace on startup, providing context about:

- File structure and contents
- Recently modified files
- Active development patterns

### Agent State

The system tracks:

- Last modified files
- Recently created files
- Current working files
- Session context and history

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Groq](https://groq.com/) for fast LLM inference
- Web search powered by [Exa](https://exa.ai/)
- Inspired by the ReAct methodology from research papers

**HephAIstos** - Forging code with the power of AI 🔥⚒️
