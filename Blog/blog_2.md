# HephAIStos: Your Friendly AI Coding Buddy 🎉

Ever wondered how an AI can help you write code, organize projects, and keep everything tidy? Meet **HephAIStos** – a lightweight, modular framework that does exactly that! Below is a friendly walkthrough of what HephAIStos is, how it works, and why you might want to give it a spin.

---

## What is HephAIStos?

HephAIStos is an **AI‑driven coding assistant** built to run right from your command line. It’s designed around three core ideas:

1. **Tools** – Concrete actions the AI can perform (reading files, writing files, searching text, etc.).
2. **Planner** – A decision‑making engine (currently rule‑based) that decides which tool to call next based on the goal you give it.
3. **Agent Core** – The orchestrator that loops through the planner’s suggestions, runs tools, and keeps a scratchpad of what’s happened.

All of this lives in a clean, extensible architecture that makes it easy to add new tools or swap in a smarter, LLM‑powered planner later on.

---

## Why a Friendly Tone?

We wanted HephAIStos to feel like a helpful coworker rather than a cold robot. That’s why the codebase is peppered with clear comments, readable variable names, and a **blog** that explains everything in a conversational style. Think of it as the friend who always has the right snippet handy!

---

## Core Components (in a nutshell)

### 1. Tool Registry & Implementations

The **Tool Registry** is a simple dictionary that maps tool names (like `read_file` or `search_text_in_files`) to their actual Python functions. Each tool follows a tiny contract:

```python
ToolFn = Callable[[dict, ToolContext], ToolResult]
```

That means every tool receives a dictionary of arguments and a `ToolContext` (which knows the workspace path), then returns a `ToolResult` indicating success and any output.

### 2. Planner

Right now the planner is **rule‑based**: it looks at your high‑level goal, checks the scratchpad, and decides which tool to call next. The idea is to keep it deterministic while we prototype. Later we can swap in an LLM to make the planning more creative.

### 3. Agent Core

The core loop looks something like this:

1. **Receive a goal** from the CLI.
2. **Ask the planner** what to do.
3. **Run the chosen tool** and capture the result.
4. **Log everything** in the scratchpad.
5. **Repeat** until the planner says we’re done.

This separation keeps the system tidy and testable.

---

## Getting Started (in 3 easy steps)

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/HephAIStos.git
   cd HephAIStos
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the CLI** with a goal of your choice:
   ```bash
   python -m hephaistos_cli "Write a friendly README for my project"
   ```
   Watch as the AI walks you through the steps, creating files, searching code, and even polishing the language.

---

## A Peek Under the Hood

If you open `HephAIStos.py`, you’ll see:

- **Dataclasses** like `Tool`, `ToolContext`, and `ToolResult` that give everything a clean shape.
- A **registry** that registers each tool with a name and description.
- A **simple planner** that can be extended.
- The **CLI entry point** (`hephaistos_cli`) that wires everything together.

All of this is documented in the repo’s `readme.md` and the various `Blog/*.md` files.

---

## Where to Go Next?

- **Add more tools** – Want the AI to run tests, lint code, or even commit to Git? Just drop a new function in the tools folder and register it!
- **Swap in an LLM planner** – Hook up OpenAI’s API (or another model) to make the planning stage smarter.
- **Build a web UI** – The core logic is UI‑agnostic, so you could create a tiny Flask app or a VS Code extension.

---

## Final Thoughts

HephAIStos is a playground for anyone curious about building AI‑assisted developer tools. It’s intentionally simple, well‑documented, and, most importantly, **friendly**. Dive in, tinker, and let the AI help you code faster and with a smile! 😊
