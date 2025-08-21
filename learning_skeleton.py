#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Callable, Dict

"""
Learning Exercise: Building an AI Assistant System

Your task is to implement each component below. Read the comments and 
fill in the implementations. The goal is to understand how each part
works and how they fit together.

Start with something simple like a calculator that can:
- Add two numbers
- Subtract two numbers 
- Multiply two numbers
"""

# ========== STEP 1: Define the basic structures ==========

@dataclass
class ToolContext:
    """
    Task 1: Define what context your tools need
    Think about:
    - What shared information might tools need?
    - What configuration might be useful?
    """
    pass  # Add your context attributes here

@dataclass 
class ToolResult:
    """
    Task 2: Define how tools report their results
    Think about:
    - How do you know if the tool succeeded?
    - What information should be returned?
    """
    pass  # Add your result attributes here

@dataclass
class Tool:
    """
    Task 3: Define what makes up a tool
    Think about:
    - What information defines a tool?
    - What does a tool need to be usable?
    """
    pass  # Add your tool attributes here

# ========== STEP 2: Implement the Tool Registry ==========

class ToolRegistry:
    """
    Task 4: Implement the tool registry
    Think about:
    - How will you store tools?
    - How will you register new tools?
    - How will you look up tools?
    """
    def __init__(self):
        pass  # Initialize your storage

    def register(self, tool: Tool):
        pass  # Implement tool registration

    def get(self, name: str) -> Tool:
        pass  # Implement tool lookup

    def list_tools(self) -> str:
        pass  # Implement tool listing

# ========== STEP 3: Create Some Basic Tools ==========

def tool_add(args: dict, context: ToolContext) -> ToolResult:
    """
    Task 5: Implement an addition tool
    Think about:
    - What arguments does it need?
    - How do you handle invalid input?
    - What should the result look like?
    """
    pass  # Implement addition

# Add more tools here (subtract, multiply, etc.)

# ========== STEP 4: Implement the Planner ==========

class SimplePlanner:
    """
    Task 6: Implement the planner
    Think about:
    - How will you decide which tool to use?
    - How will you parse the user's goal?
    - How will you handle unknown requests?
    """
    def propose_next_action(self, goal: str, history: list[str]) -> dict:
        pass  # Implement planning logic

# ========== STEP 5: Implement the Agent ==========

class SimpleAgent:
    """
    Task 7: Implement the agent
    Think about:
    - How will the execution loop work?
    - How will you handle errors?
    - How will you track progress?
    """
    def __init__(self, tools: ToolRegistry):
        pass  # Initialize your agent

    def run(self, goal: str, max_steps: int = 3) -> str:
        pass  # Implement the execution loop

# ========== STEP 6: Testing ==========

def main():
    """
    Task 8: Test your implementation
    Think about:
    - What test cases should you try?
    - How will you handle edge cases?
    - How will you display results?
    """
    # 1. Create registry
    # 2. Create and register tools
    # 3. Create agent
    # 4. Test different inputs
    pass

if __name__ == "__main__":
    main()
