from dataclasses import dataclass, field
from typing import Callable, Dict
import os 
import requests
import json 
from urllib import request, error as urlerror
from cerebras.cloud.sdk import Cerebras

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
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> ToolFn | None:
        if name in self.tools:
            return self.tools[name]
        else:
            raise KeyError(f"Unknown tool: {name}")
    def list_tools(self):
        for idx, tool in enumerate(self.tools.values()):
            print(f"Tool {idx}: {tool.name}, Description: {tool.description}")

# ========== Defining the Tools ========== 

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
tool_dict = {
    "read_file": Tool(
        name="read_file",
        description="Reads the content of a file.",
        fn=_tool_read_file
    ),
    "write_file": Tool(
        name="write_file",
        description="Writes content to a file.",
        fn=_tool_write_file
    ),
    "append_file": Tool(
        name="append_file",
        description="Appends content to a file.",
        fn=_tool_append_file
    ),
    "list_dir": Tool(
        name="list_dir",
        description="Lists files in a directory.",
        fn=_tool_list_dir
    ),
    "search_text_in_files": Tool(
        name="search_text_in_files",
        description="Searches for text in files within a directory.",
        fn=_tool_search_text_in_files
    ),
    "run_python_script": Tool(
        name="run_python_script",
        description="Executes a Python script from a file.",
        fn=_tool_run_python_script
    )
}

tool_registry = ToolRegistry()
for tool in tool_dict.items():
    tool_registry.register(tool[1])

tool_registry.list_tools()
# This will print the list of registered tools with their descriptions.

# ========== Agent Planner ==========

def planner(goal: str, scratchpad: list[str], tools: ToolRegistry) -> dict:
    """
    Prompts an LLM to select a tool and arguments for the agent.
    Returns a dict: {"tool": <tool_name>, "args": {...}, "thought": <reasoning>}
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"tool": None, "args": {}, "thought": "OPENAI_API_KEY not set."}

    prompt = f"""
        You are an autonomous coding assistant. You have these tools:
        {tools.list_tools()}

        Given the user's goal and the scratchpad (history), reply ONLY with a JSON object:
        - tool: tool name to use
        - args: arguments for the tool (as a JSON object)
        - thought: short reasoning

        User goal: {goal}
        Scratchpad: {scratchpad}
        """

    client = Cerebras(
        # This is the default and can be omitted
        api_key=os.environ.get("cerebras_api_key"),
    )
    
    stream = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "Hello you an assistant"
            }
        ],
        model="qwen-3-coder-480b",
        stream=True,
        max_completion_tokens=40000,
        temperature=0.57,
        top_p=0.8
    )


    response_text = ""
    for chunk in stream:
        if hasattr(chunk, "choices") and chunk.choices:
            delta = chunk.choices[0].delta
            if delta and "content" in delta:
                response_text += delta["content"]
    
    try:
        plan = json.loads(response_text)
        return plan
    except Exception as e:
        return {"tool": None, "args": {}, "thought": f"Planner error: {e}\nRaw response: {response_text}"}

# ========== Agent Core ==========
