# HepAIstos.py Documentation

## Overview

HephAIstos.py is an AI agent implementation that includes a tooling system, a planner, and core agent logic. It defines tools, a tool registry, and the orchestration needed for the agent to operate.

## Tooling System

The tooling system consists of `Tool`, `ToolContext`, `ToolResult`, and `ToolRegistry` classes. Tools are functions that accept arguments and a context, returning a `ToolResult`. The `ToolRegistry` manages registration and retrieval of tools.

## Planner

The planner decides the next action based on the goal and current state. It can propose either a tool call or a final message. Initially rule‑based, it can later be replaced with an LLM‑based planner.

## Agent Core

The agent core orchestrates the loop: it receives a goal, interacts with the planner, executes tool calls, maintains a scratchpad, and decides when to stop. It also provides a simple CLI for user interaction.

## Detailed Overview

HephAIstos.py provides a lightweight yet extensible framework for building AI agents. It separates concerns into three main components: a flexible tooling system, a planner that decides actions, and an orchestration core that ties everything together. The design aims for readability and easy extension for custom tools or planner strategies.

### Tooling System Deep Dive

The tooling system revolves around four core classes:

- **ToolContext** – encapsulates execution context (e.g., workspace path) allowing safe sandboxed operations.
- **ToolResult** – standardized result container with `ok` flag and textual `output`.
- **Tool** – bundles a name, description, the callable, and its default context.
- **ToolRegistry** – maintains a mapping of tool names to their implementations, provides registration, lookup, and a helper to list tools.
  Developers can add new tools by defining a function matching the `ToolFn` signature (`def fn(args: dict, ctx: ToolContext) -> ToolResult`) and registering it via `registry.register(Tool(...))`.

### Planner Mechanics

The planner currently implements a rule‑based strategy:

1. Inspect the user goal and the agent's scratchpad.
2. Decide whether a tool call can move the agent closer to the goal.
3. If no tool is appropriate, emit a final message.
   The planner returns a structured `PlanStep` indicating either a `tool_name` with arguments or `final_message`. Future work may replace this with an LLM‑driven planner for more sophisticated reasoning.

### Agent Core and CLI

The `Agent` class orchestrates the loop:

- Accepts a user goal.
- Queries the planner for the next step.
- Executes the suggested tool via the registry.
- Records each interaction in a scratchpad for context.
- Terminates when the planner signals a final message.
  A simple command‑line interface (`python HephAIstos.py`) lets users type goals, see each step printed, and exit with `quit`.
  Additional utilities (e.g., safe file path checks) are provided to prevent destructive actions.
