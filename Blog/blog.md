# HephAIStos Detailed Overview

Welcome to the comprehensive guide for **HephAIStos**, an AI‑driven coding assistant framework designed to operate from the command line. This document expands on the high‑level overview, diving into each component, its responsibilities, and how they interact to enable autonomous task execution.

---

## 1. Core Concepts

HephAIStos is built around three foundational pillars:

1. **Tool Implementations** – Concrete actions the agent can perform (e.g., file I/O, executing scripts). Each tool adheres to a standardized interface, accepting a JSON‑serializable argument dictionary and a `ToolContext`, then returning a `ToolResult` indicating success and any output.
2. **Planner** – The decision‑making engine. Currently rule‑based, it inspects the user goal and the agent’s scratchpad to propose the next action, whether that’s invoking a tool or returning a final response. Future versions will replace this with an LLM‑driven planner for richer reasoning.
3. **Agent Core** – Orchestrates the loop: receives the goal, queries the planner, executes the selected tool, records the outcome in the scratchpad, and determines termination conditions.

These concepts are deliberately decoupled to allow easy swapping or extension of any part of the system.

---

## 2. Architecture Walk‑through

### 2.1. Tool Registry

The `ToolRegistry` maintains a mapping of tool names to their implementation functions. It provides methods to:

- **Register** new tools (`registry.register(Tool(...))`).
- **Retrieve** a tool by name (`registry.get_tool('write_file')`).
- **List** all available tools for introspection.

By centralizing tool management, the planner can query the registry dynamically, making the system highly extensible.

### 2.2. Tool Implementations

Key built‑in tools include:

| Tool | Description |
|------|-------------|
| `read_file` | Safely reads a file’s contents, respecting the workspace sandbox. |
| `write_file` | Overwrites or creates a file with the supplied content. |
| `append_file` | Appends text to an existing file. |
| `list_dir` | Returns a list of files/folders in a directory. |
| `search_text_in_files` | Greps for a string across files in a directory. |
| `run_python_script` | Executes a Python script and captures stdout/stderr. |
| `patch_file` | Applies line‑based diffs (insert, replace, remove) to a target file. |

Each tool returns a `ToolResult` with `ok` flag and optional `output` for debugging.

### 2.3. Planner (Rule‑Based)

The planner follows a simple decision tree:

1. **Parse Goal** – Look for keywords indicating required actions (e.g., `create`, `list`, `run`).
2. **Select Tool** – Match keywords to a tool in the registry.
3. **Generate Arguments** – Build a minimal JSON argument set based on the goal.
4. **Return Action** – Emit a JSON step for the core to execute.

While rudimentary, this approach guarantees deterministic behavior and is easy to unit‑test. Future enhancements will involve prompt‑engineering an LLM to propose richer, multi‑step plans.

### 2.4. Agent Core Loop

The core loop performs the following steps until a termination condition is met:

1. **Receive Goal** – Input from the CLI.
2. **Query Planner** – Get the next step (tool + args).
3. **Execute Tool** – Invoke the tool function with the provided arguments and context.
4. **Record Result** – Append the outcome to the scratchpad for future reference.
5. **Check Completion** – If the planner returns a `final_message`, break the loop and display the result.

The scratchpad acts as a transparent log, enabling debugging and potential back‑tracking.

---

## 3. CLI Interface

The entry point `hephaistos_cli` parses a single positional argument representing the user’s goal. It then instantiates the `Agent`, starts the loop, and streams each step to stdout:

```bash
python -m hephaistos_cli "Generate a README for my project"
```

Output includes the selected tool, arguments, and the tool’s result, offering clear insight into the agent’s reasoning.

---

## 4. Extending the Framework

### Adding New Tools

1. **Implement the function** following the `ToolFn` signature `(args: dict, context: ToolContext) -> ToolResult`.
2. **Create a `Tool` instance** with a unique name and description.
3. **Register** it via `registry.register(new_tool)`.

### Custom Planners

Replace the built‑in rule‑based planner with a class that implements a `plan(goal: str, scratchpad: List[dict]) -> dict` method returning the next step. Plug it into the `Agent` constructor.

---

## 5. Safety & Utilities

HephAIStos incorporates several safeguards:

- **Workspace Sandboxing** – All file operations are confined to the current working directory, preventing directory traversal attacks.
- **Argument Validation** – Tools validate inputs (e.g., ensuring paths are strings, content is not `None`).
- **Result Normalization** – Every tool returns a structured `ToolResult`, making downstream handling predictable.

Utility modules also provide helpers for clamping numeric values, rate‑limiting, and logging.

---

## 6. Getting Started

```bash
# Clone the repo
git clone https://github.com/yourusername/HephAIStos.git
cd HephAIStos

# Install dependencies
pip install -r requirements.txt

# Run an example goal
python -m hephaistos_cli "Create a simple Python script that prints \"Hello, World!\""
```

You should see the agent decide to use `write_file` to create `hello.py`, then optionally `run_python_script` to execute it.

---

## 7. Future Roadmap

- **LLM‑Based Planner** – Integrate OpenAI/GPT models for more nuanced planning.
- **Tool Chaining** – Allow tools to output artifacts that become inputs for subsequent tools automatically.
- **Web UI** – Provide a browser‑based interface for richer interaction.
- **Plugin System** – Enable third‑party developers to contribute new tools via a simple plugin API.

---

*This document was generated by an autonomous coding assistant to provide a deeper look into HephAIStos. Feel free to modify or extend any section as your project evolves.*