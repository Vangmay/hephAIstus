# HephAIstos Documentation

## Overview

HephAIstos provides a modular tooling system for AI agents, including tool definitions, a registry, and execution helpers.

## Core Classes

- `ToolContext`: Holds workspace context.
- `ToolResult`: Represents the result of a tool execution.
- `Tool`: Defines a tool's metadata and function.
- `ToolRegistry`: Manages registration and retrieval of tools.

## Usage Example

```python
from HephAIstos import Tool, ToolRegistry

registry = ToolRegistry()
registry.register(Tool(name="read_file", description="Read a file", fn=read_file_fn))
# ... use registry.get_tool("read_file")(...)
```

## Extending the System

Developers can add new tools by defining a function that matches the `ToolFn` signature and registering it with `ToolRegistry`.
