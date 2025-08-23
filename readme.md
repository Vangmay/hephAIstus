# HephAIStos

An extensible AI agent framework built in Python. This repository contains the core engine, tooling system, and examples to get started.

## Overview

HephAIStos is designed around three main concepts:

- **Tool Implementations** – concrete actions the agent can perform.
- **Planner** – decides the next action based on the goal and current state.
- **Agent Core** – orchestrates the loop, maintains a scratchpad, and interacts with the planner.

The architecture aims to be modular, testable, and easy to extend with new tools or planning strategies.

## Components

- **Tool Registry** – registers and retrieves tool functions.
- **Planner** – rule‑based (future: LLM‑based) decision maker.
- **Agent Core** – main loop handling goals, tool calls, and scratchpad.
- **CLI Interface** – simple command‑line entry point for users.
- **Utilities** – safety helpers (file sandboxing, clamping, etc.).

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/HephAIStos.git
   cd HephAIStos
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the CLI**
   ```bash
   python -m hephaistos_cli "Your goal here"
   ```

The CLI will display the agent's actions and results in real time.
