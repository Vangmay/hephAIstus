from dataclasses import dataclass, field
from typing import Callable, Dict
import os 
import requests
import json 
from urllib import request, error as urlerror
from cerebras.cloud.sdk import Cerebras
import random
from dotenv import load_dotenv
load_dotenv()

# ========== Helper Functions / Guard Rails ==========
def safe_path(workspace, path) -> str:
    if ".." in path.replace("\\", "/").split("/"):
        raise ValueError("Access to parent directories ('../') is not allowed.")
    abs_path = os.path.abspath(os.path.join(workspace, path))
    return abs_path

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

# ========== Defining the Tools ========== 

def _tool_read_file(args: dict, context: ToolContext) -> ToolResult:
    file_path = args.get("path")
    if not file_path:
        return ToolResult(ok=False, output="No file path provided.")
    full_path = safe_path(context.workspace_path, file_path)
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
    full_path = safe_path(context.workspace_path, file_path)
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
    full_path = safe_path(context.workspace_path, file_path)
    try:
        with open(full_path, 'a') as file:
            file.write(content)
        return ToolResult(ok = True, output=f"File appended successfully to {full_path}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error appending file: {e}")

def _tool_list_dir(args: dict, context: ToolContext) -> ToolResult:
    dir_path = args.get("path", context.workspace_path)
    full_path = safe_path(context.workspace_path, dir_path)
    try:
        files = os.listdir(full_path)
        return ToolResult(ok=True, output="\n".join(files))
    except Exception as e:
        return ToolResult(ok=False, output=f"Error listing directory: {e}")

def _tool_search_text_in_files(args: dict, context: ToolContext) -> ToolResult:
    search_text = args.get("text")
    dir_path = args.get("path", context.workspace_path)
    full_path = safe_path(context.workspace_path, dir_path)

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
    
def _tool_patch_file(args: dict, context: ToolContext) -> ToolResult:
    """
    Applies a list of changes (patches) to a file.
    Args:
        path: file to edit
        changes: list of dicts, each with:
            - action: "remove", "replace", or "insert"
            - line: line number (0-based)
            - content: new content (for replace/insert)
    """
    file_path = args.get("path")
    changes = args.get("changes")
    if not file_path or not isinstance(changes, list):
        return ToolResult(ok=False, output="Missing 'path' or 'changes' (must be a list).")
    try:
        full_path = safe_path(context.workspace_path, file_path)
        with open(full_path, "r") as f:
            lines = f.readlines()
        for change in sorted(changes, key=lambda c: c.get("line", 0), reverse=True):
            action = change.get("action")
            line = change.get("line")
            content = change.get("content", "")
            if action == "remove":
                if 0 <= line < len(lines):
                    lines.pop(line)
            elif action == "replace":
                if 0 <= line < len(lines):
                    lines[line] = content + "\n"
            elif action == "insert":
                if 0 <= line <= len(lines):
                    lines.insert(line, content + "\n")
        with open(full_path, "w") as f:
            f.writelines(lines)
        return ToolResult(ok=True, output=f"Applied {len(changes)} changes to {full_path}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error patching file: {e}")
    
def _tool_delete_file(args: dict, context: ToolContext) -> ToolResult:
    return ToolResult(ok=False, output="File deletion is not allowed by safety policy.")

def _tool_run_python_script(args: dict, context: ToolContext) -> ToolResult:
    script_path = args.get("path")
    if not script_path:
        return ToolResult(ok = False, output = "No Script path provided.")
    try:
        full_path = safe_path(context.workspace_path, script_path)
        with open(full_path, 'r') as file:
            script_content = file.read()
        
        if "os.remove" in script_content or "shutil.rmtree" in script_content:
            return ToolResult(ok=False, output="Script contains unsafe operations.")
    
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
    ),
    "delete_file": Tool(
        name="delete_file",
        description="Deletes a file. (Disabled for safety)",
        fn=_tool_delete_file
    ),
    "patch_file": Tool(
        name="patch_file",
        description="Applies a list of line-based changes (diff patch) to a file. Usage: args={'path':..., 'changes':[{'action':'replace','line':2,'content':'new text'}, ...]}",
        fn=_tool_patch_file
    )
}

tool_context = ToolContext()
tool_registry = ToolRegistry(tool_context)
for tool in tool_dict.items():
    tool_registry.register(tool[1])
# This will print the list of registered tools with their descriptions.

# ========== Agent Planner ==========

def planner(goal: str, scratchpad: list[str], tools: ToolRegistry, steps: int = 5, workspace_context: str = "Workspace is empty") -> dict:
    """
    Prompts an LLM to select a tool and arguments for the agent.
    Returns a dict: {"tool": <tool_name>, "args": {...}, "thought": <reasoning>}
    """
    prompt = f"""
        You are an autonomous coding assistant. You have these tools:
        {tools.list_tools()}

        WORKSPACE CONTEXT:
        {workspace_context}

        TOOL USAGE EXAMPLES:
            - patch_file: Applies a list of line-based changes (diff patch) to a file.
            Example:
            {{
                "tool": "patch_file",
                "args": {{
                "path": "main.py",
                "changes": [
                    {{"action": "remove", "line": 2}},
                    {{"action": "replace", "line": 5, "content": "new line content"}},
                    {{"action": "insert", "line": 10, "content": "inserted line"}}
                ]
                }},
                "thought": "Edit main.py by removing, replacing, and inserting lines."
            }}

        Given the user's goal and the scratchpad (history), reply ONLY with a JSON array of step objects.
        Each step object must have:
        - tool: tool name to use
        - args: arguments for the tool (as a JSON object)
        - thought: short reasoning

        User goal: {goal}
        Scratchpad: {scratchpad}
        Break the task into {steps} sequential steps. Return ONLY the JSON array, no markdown.
        Example:
        [
        {{"tool": "write_file", "args": {{"path": "index.html", "content": "<html>...</html>"}}, "thought": "Create HTML file"}},
        {{"tool": "write_file", "args": {{"path": "style.css", "content": "body {{ ... }}" }}, "thought": "Create CSS file"}}
        ]
        """
    print("PLANNER PROMTP")
    print(prompt)

    client = Cerebras(
        # This is the default and can be omitted
        api_key=os.environ.get("cerebras_api_key"),
    )
    
    stream = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": prompt
            }
        ],
        model="gpt-oss-120b",
        stream=True,
        max_completion_tokens=65536,
        temperature=1,
        top_p=1,
        reasoning_effort="medium"
    )

    response_text = ""
    for chunk in stream:
        response_text += chunk.choices[0].delta.content or ""
    response_text += "\n"

    response_text = response_text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text

    try:
        plan = json.loads(response_text)
        if isinstance(plan, list):
            return plan
        else: 
            return [{"tool": None, "args": {}, "thought": f"Planner did not return a list. Raw response: {response_text}"}]
    except Exception as e:
        return [{"tool": None, "args": {}, "thought": f"Planner error: {e}\nRaw response: {response_text}"}]


def analyze_workspace(workspace_path: str, max_file_size: int = 4096) -> str:
    """
    Scans the workspace and returns a summary of files and their contents (truncated).
    """
    summary = []
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if d not in [".git", ".github"]]
        rel_root = os.path.relpath(root, workspace_path)

        if any(skip in rel_root.split(os.sep) for skip in [".git", ".github"]):
            continue

        for file in files:
            if file.startswith(".git") or file.startswith(".github"):
                continue
            file_path = os.path.join(root, file)
            rel_path = os.path.join(rel_root, file) if rel_root != "." else file
            try:
                size = os.path.getsize(file_path)
                if size > max_file_size:
                    summary.append(f"{rel_path} (size: {size} bytes, skipped)")
                else:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(max_file_size)
                    summary.append(f"{rel_path}:\n{content}\n---")
            except Exception as e:
                summary.append(f"{rel_path} (error reading: {e})")
    return "\n".join(summary)

# ans = planner("Writing a website using html and css and javascript", [], tool_registry)
# print(ans)
# ========== Agent Core ==========

def run_agent(goal: str, tool_registry: ToolRegistry, max_steps: int = 5, workspace_content: str = "Workspace is empty") -> str:
    scratchpad = []
    plan_steps = planner(goal, scratchpad, tool_registry, max_steps, workspace_content)
    
    for idx, step in enumerate(plan_steps):
        tool_name = step.get("tool")
        args = step.get("args", {})
        reasoning = step.get("thought", "")
        # print(f"\nStep {idx+1}: {reasoning} using tool '{tool_name}' with args {args}")
        
        if not tool_name or tool_name not in tool_registry.tools:
            # print(f"Invalid tool name: {tool_name}. Stopping.")
            break

        tool_fn = tool_registry.get_tool(tool_name).fn
        result = tool_fn(args, tool_registry.get_context())
        # print(f"Result: {result.output}")

        scratchpad_entry = f"Thought: {reasoning}\nAction: {tool_name}\nAction Input: {json.dumps(args)}\nObservation: {result.output}\n"
        scratchpad.append(scratchpad_entry)
    
    # print("\nAgent Run complete")
    return "\n".join(scratchpad)

# ans = run_agent("Writing a website using html and css and javascript", tool_registry, max_steps=5)
# print(ans)

def dummy_run_agent(goal):
    return f"Dummy run for goal: {goal}"

# ========== CLI Core ==========

def get_cli_art():
    cli_art_1 = """
    ██╗  ██╗███████╗██████╗  █████╗ ██╗███████╗████████╗██╗   ██╗███████╗
    ██║  ██║██╔════╝██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝██║   ██║██╔════╝
    ███████║█████╗  ██████╔╝███████║██║███████╗   ██║   ██║   ██║███████╗
    ██╔══██║██╔══╝  ██╔═══╝ ██╔══██║██║╚════██║   ██║   ██║   ██║╚════██║
    ██║  ██║███████╗██║     ██║  ██║██║███████║   ██║   ╚██████╔╝███████║
    ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝
                                                                        
    """

    cli_art_2 = """
    __                             ______   ______              __                         
    /  |                           /      \ /      |            /  |                        
    $$ |____    ______    ______  /$$$$$$  |$$$$$$/   _______  _$$ |_    __    __   _______ 
    $$      \  /      \  /      \ $$ |__$$ |  $$ |   /       |/ $$   |  /  |  /  | /       |
    $$$$$$$  |/$$$$$$  |/$$$$$$  |$$    $$ |  $$ |  /$$$$$$$/ $$$$$$/   $$ |  $$ |/$$$$$$$/ 
    $$ |  $$ |$$    $$ |$$ |  $$ |$$$$$$$$ |  $$ |  $$      \   $$ | __ $$ |  $$ |$$      \ 
    $$ |  $$ |$$$$$$$$/ $$ |__$$ |$$ |  $$ | _$$ |_  $$$$$$  |  $$ |/  |$$ \__$$ | $$$$$$  |
    $$ |  $$ |$$       |$$    $$/ $$ |  $$ |/ $$   |/     $$/   $$  $$/ $$    $$/ /     $$/ 
    $$/   $$/  $$$$$$$/ $$$$$$$/  $$/   $$/ $$$$$$/ $$$$$$$/     $$$$/   $$$$$$/  $$$$$$$/  
                        $$ |                                                                
                        $$ |                                                                
                        $$/                                                                     

    """
    return random.choice([cli_art_1, cli_art_2])
    

def color_text(text, color_code):
    return f"\033[{color_code}m{text}\033[0m"

def print_banner():
    banner = get_cli_art()
    print(color_text(banner, "36"))  # Cyan

def cli(workspace_summary: str):
    print_banner()
    print(color_text("Welcome to HephAIstos, your autonomous coding assistant!", "32"))  # Green
    print(color_text("Type 'exit' to quit.", "33"))  # Yellow

    while True:
        goal = input(color_text("\n🔎 Enter your coding goal: ", "34"))  # Blue
        if goal.lower() in ['exit', 'quit']:
            print(color_text("👋 Exiting HephAIstos. Goodbye!", "31"))  # Red
            break
        print(color_text(f"\n⚡ Running agent for goal: {goal}\n", "35"))  # Magenta

        # Run the real agent, not dummy
        result = run_agent(goal, tool_registry, max_steps=5, workspace_content=workspace_summary)
        print(color_text("\n--- Agent Scratchpad ---", "36"))
        print(color_text(result, "37"))  # White


if __name__ == "__main__":
    workspace_summary = analyze_workspace(os.getcwd())
    cli(workspace_summary)