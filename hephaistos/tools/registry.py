from dataclasses import dataclass, field
from typing import Callable, Dict
import os

@dataclass
class ToolContext:
    workspace_path: str = field(default_factory=lambda: os.getcwd())

@dataclass
class ToolResult: 
    ok: bool
    output: str

ToolFn = Callable[[dict, ToolContext], ToolResult]

@dataclass
class Tool:
    name: str
    description: str
    fn: ToolFn 
    context: ToolContext = field(default_factory=ToolContext)

@dataclass
class ToolRegistry:
    def __init__(self, context: ToolContext = ToolContext()):
        self.tools: Dict[str, Tool] = {}
        self.context = context 

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> ToolFn | None:
        if name in self.tools:
            return self.tools[name]
        else:
            raise KeyError(f"Unknown tool: {name}")
    
    def list_tools(self):
        ans = ""
        for idx, tool in enumerate(self.tools.values()):
            ans += f"Tool {idx}: {tool.name}, Description: {tool.description}\n"
        return ans.strip() if ans else "No tools registered."

    def get_context(self) -> ToolContext:
        return self.context

def build_tool_registry(tool_dict) -> ToolRegistry:
    tool_context = ToolContext()
    tool_registry = ToolRegistry(tool_context)
    for tool in tool_dict.items():
        tool_registry.register(tool[1])
    return tool_registry 