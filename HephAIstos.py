from dataclasses import dataclass, field
from typing import Callable, Dict
import os 

# ========== Defining the Tools Registry ========== 
 
@dataclass
class ToolContext:
    workspace_path: str = field(default_factory=lambda: os.getcwd())

@dataclass
class ToolResult: 
    ok: bool
    output: str

ToolFn = Callable[[dict, ToolContext], ToolResult]
# A Type that defines how a tool is used

@dataclass
class Tool:
    name: str
    description: str
    fn: ToolFn 
    context: ToolContext = field(default_factory=ToolContext)

@dataclass
class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolFn] = {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool.fn

    def get_tool(self, name: str) -> ToolFn | None:
        if name in self.tools:
            return self.tools[name]
        else:
            raise KeyError(f"Unknown tool: {name}")
    def list_tools(self):
        for tool in self.tools.values():
            print(f"Tool: {tool.name}, Description: {tool.description}")

# ========== Defining the Tools Functions ========== 

def _tool_read_file(args: dict, context: ToolContext) -> ToolResult:
    file_path = args.get("path")
    if not file_path:
        return ToolResult(ok=False, output="No file path provided.")
    full_path = os.path.join(context.workspace_path, file_path)
    try:
        with open(full_path, 'r') as file:
            content = file.read()
        return ToolResult(ok=True, output=content)
    except Exception as e:
        return ToolResult(ok=False, output=f"Error reading file: {e}")

def _tool_write_file(args: dict, context: ToolContext) -> ToolResult:
    file_path = args.get("path")
    content = args.get("content")

    if not file_path or content is None:
        return ToolResult(ok=False, output="File path or content not provided.")
    full_path = os.path.join(context.workspace_path, file_path)
    try:
        with open(full_path, 'w') as file:
            file.write(content)
        return ToolResult(ok=True, output=f"File written successfully to {full_path}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error writing file: {e}")

def _tool_append_file(args: dict, context: ToolContext) -> ToolResult:
    file_path = args.get("path")
    content = args.get('content')

    if not file_path or content is None:
        return ToolResult(ok=False, output="File path or content not provided.")
    full_path = os.path.join(context.workspace_path, file_path)
    try:
        with open(full_path, 'a') as file:
            file.write(content)
        return ToolResult(ok = True, output=f"File appended successfully to {full_path}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error appending file: {e}")

def _tool_list_dir(args: dict, context: ToolContext) -> ToolResult:
    dir_path = args.get("path", context.workspace_path)
    full_path = os.path.join(context.workspace_path, dir_path)
    try:
        files = os.listdir(full_path)
        return ToolResult(ok=True, output="\n".join(files))
    except Exception as e:
        return ToolResult(ok=False, output=f"Error listing directory: {e}")

def _tool_search_text_in_files(args: dict, context: ToolContext) -> ToolResult:
    search_text = args.get("text")
    dir_path = args.get("path", context.workspace_path)
    full_path = os.path.join(context.workspace_path, dir_path)

    if not search_text:
        return ToolResult(ok = False, output = "No search text provided.")
    try:
        matching_files = []
        for root, _, files in os.walk(full_path):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    if search_text in f.read():
                        matching_files.append(file_path)
        return ToolResult(ok=True, output="\n".join(matching_files) if matching_files else "No matching files found.")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error searching files: {e}")
def _tool_run_python_script(args: dict, context: ToolContext) -> ToolResult:
    script_path = args.get("path")
    if not script_path:
        return ToolResult(ok = False, output = "No Script path provided.")
    full_path = os.path.join(context.workspace_path, script_path)
    try:
        with open(full_path, 'r') as file:
            script_content = file.read()
        exec(script_content, {'__name__': '__main__'})
        return ToolResult(ok=True, output=f"Script executed successfully: {full_path}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error executing script: {e}")
    
# ========== Registering Tools ==========
tool_registry = ToolRegistry()
read_file = Tool(name = "read_file", description="Read the contexts of file", fn = _tool_read_file)