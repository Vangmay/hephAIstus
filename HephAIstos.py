from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
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

def _tool_chat(args: dict, context: ToolContext) -> ToolResult:
    message = args.get("message", "")
    if not message:
        return ToolResult(ok=False, output="No message provided.")
    return ToolResult(ok=True, output=f"🤖 Suggestion: {message}")
    
# ========== Registering Tools ==========
tool_dict = {
    "chat": Tool(
        name="chat",
        description="General chat tool for suggestions and advice.",
        fn=_tool_chat
    ),
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

def planner(goal: str, scratchpad: list[str], tools: ToolRegistry, steps: int = 5, workspace_context: str = "Workspace is empty", agent_context: str = "") -> dict:
    """
    Prompts an LLM to select a tool and arguments for the agent.
    Returns a dict: {"tool": <tool_name>, "args": {...}, "thought": <reasoning>}
    """
    def _clip(s, n=4000):
        return s if len(s) <= n else s[:n] + "\n...[truncated]"
    
    system_prompt = f"""
        You are an autonomous coding assistant. You have these tools:
        {tools.list_tools()}

        CONTEXT CONTRACT:
        - If the user refers to “it/this/the file/that” → target AGENT CONTEXT's LAST MODIFIED FILE.
        - If the user uses pronouns about a NON-FILE concept (e.g., places, people, facts),
        resolve them to AGENT CONTEXT's LAST TOPIC.  # NEW
        - Prefer the 'chat' tool for general Q&A; do NOT mention repo files unless asked.  # NEW
        - Every file-affecting step MUST include args.path. If missing, auto-fill it from LAST MODIFIED FILE
        and say so in "thought".
        - The "thought" must explicitly name the target (file or topic).
        Return ONLY a JSON array of steps (tool, args, thought). No markdown/code fences.
        """
    
    print(f"AGENT CONTEXT: {agent_context}")
    user_prompt = f"""
        WORKSPACE CONTEXT:
        {_clip(workspace_context, )}

        AGENT CONTEXT:
        {_clip(agent_context)}

        User goal: {goal}
        
        Scratchpad: {_clip("".join(scratchpad))}

        Given the user's goal and the scratchpad (history), reply ONLY with a JSON array of step objects.
        Each step object must have:
        - tool: tool name to use
        - args: arguments for the tool (as a JSON object)
        - thought: short reasoning
        
        Break the task into sequential steps. Return ONLY the JSON array, no markdown.
        Example:
        [
        {{"tool": "write_file", "args": {{"path": "index.html", "content": "<html>...</html>"}}, "thought": "Create HTML file"}},
        {{"tool": "write_file", "args": {{"path": "style.css", "content": "body {{ ... }}" }}, "thought": "Create CSS file"}}
        ]
        """

    client = Cerebras(
        # This is the default and can be omitted
        api_key=os.environ.get("cerebras_api_key"),
    )
    params = dict(
        model="gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        top_p=0.95,
        max_completion_tokens=2048,
    )

    def _parse_json(txt: str) -> list:
        txt = txt.strip()
        if not txt:
            return [{"tool": None, "args": {}, "thought": "Planner returned empty content."}]
        if txt.startswith("```"):
            lines = txt.splitlines()
            txt = "\n".join(lines[1:-1]).strip()
        end = txt.rfind("]")
        if end != -1:
            txt = txt[:end+1]
        try:
            obj = json.loads(txt)
            return obj if isinstance(obj, list) else [{"tool": None, "args": {}, "thought": f"Non-list planner output: {txt[:200]}..."}]
        except Exception as e:
            return [{"tool": None, "args": {}, "thought": f"Planner JSON error: {e}\nRaw: {txt[:500]}"}]


    response_text = ""
    try:
        stream = client.chat.completions.create(stream=True, **params)
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                response_text += delta.content
    except Exception as _:
        response_text = ""

    if not response_text.strip():
        try:
            resp = client.chat.completions.create(stream=False, **params)
            response_text = resp.choices[0].message.content or ""
        except Exception as e:
            return [{"tool": None, "args": {}, "thought": f"Planner transport error: {e}"}]
    print("Response from planner: ", response_text)
    return _parse_json(response_text)



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

# ========== Agent State =========
@dataclass
class AgentState:
    last_modified_file: Optional[str] = None
    recently_created_files: List[str] = field(default_factory=list)
    current_files: Dict[str, str] = field(default_factory=dict)
    session_context: str = ""

    last_topic: Optional[str] = None
    last_answer: Optional[str] = None

    
    def update_from_tool_result(self, tool_name: str, args: dict, result: ToolResult):
        """Update state based on tool execution"""
        if tool_name in ["write_file", "patch_file", "append_file"] and result.ok:
            file_path = args.get("path")
            if file_path:
                self.last_modified_file = file_path
                self.current_files[file_path] = tool_name
                
        elif tool_name == "write_file" and result.ok:
            file_path = args.get("path")
            if file_path and file_path not in self.current_files:
                self.recently_created_files.append(file_path)
    
    def get_context_string(self) -> str:
        context_parts = []
        
        if self.last_modified_file:
            context_parts.append(f"LAST MODIFIED FILE: {self.last_modified_file}")
            
        if self.recently_created_files:
            context_parts.append(f"RECENTLY CREATED: {', '.join(self.recently_created_files[-3:])}")
            
        if self.current_files:
            active_files = list(self.current_files.keys())[-3:]
            context_parts.append(f"ACTIVE FILES: {', '.join(active_files)}")
        if self.last_topic:
            context_parts.append(f"LAST TOPIC: {self.last_topic}")
            
        return "\n".join(context_parts) if context_parts else "No recent file operations"

# ========== Agent Core ==========

def run_agent(goal: str, tool_registry: ToolRegistry, max_steps: int = 5, workspace_content: str = "Workspace is empty", agent_state: AgentState = None) -> str:
    if agent_state is None:  
        agent_state = AgentState() 
    
    scratchpad = []
    plan_steps = planner(goal, scratchpad, tool_registry, max_steps, workspace_content, agent_state.get_context_string())
    
    for idx, step in enumerate(plan_steps):
        print(step)
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

        agent_state.update_from_tool_result(tool_name, args, result)
        if tool_name == "chat" and result.ok:
            agent_state.last_topic = args.get("message", "")[:100]
            agent_state.last_answer = result.output[:200]

        scratchpad_entry = f"Thought: {reasoning}\nAction: {tool_name}\nAction Input: {json.dumps(args)}\nObservation: {result.output}\n" 
        scratchpad.append(scratchpad_entry)
    
    # print("\nAgent Run complete")
    return "\n".join(scratchpad)

# ans = run_agent("Writing a website using html and css and javascript", tool_registry, max_steps=5)
# print(ans)

# ========== CLI Core ==========

# ======== UI Helpers ==========
BOLD  = "\033[1m"
DIM   = "\033[2m"
RESET = "\033[0m"

def hr(char="─", width=80):
    return char * width

def box(title: str, body: str, width: int = 80) -> str:
    title = f" {title} "
    top    = f"┌{hr('─', width-2)}┐"
    midttl = f"│{title[:width-2].ljust(width-2)}│"
    sep    = f"├{hr('─', width-2)}┤"
    lines  = [f"│ {line[:width-3].ljust(width-3)}│" for line in body.splitlines() or [""]]
    bot    = f"└{hr('─', width-2)}┘"
    return "\n".join([top, midttl, sep, *lines, bot])

def status(label: str, msg: str, color="36"):  # default cyan
    return f"\033[{color}m[{label}]\033[0m {msg}"

def pretty_steps(scratchpad: str, width: int = 80) -> str:
    # Turn your "Thought/Action/Observation" text into numbered blocks
    blocks = [b.strip() for b in scratchpad.split("\nObservation: ") if b.strip()]
    rendered = []
    for i, b in enumerate(blocks, 1):
        # put Observation back for readability
        if "Action Input:" in b and "Thought:" in b and "Action:" in b:
            rendered.append(box(f"Step {i}", b.replace("Thought:", f"{BOLD}Thought:{RESET}")
                                     .replace("Action:", f"{BOLD}Action:{RESET}")
                                     .replace("Action Input:", f"{BOLD}Action Input:{RESET}")
                                     .replace("Observation:", f"{BOLD}Observation:{RESET}"),
                                width))
        else:
            rendered.append(box(f"Step {i}", b, width))
    return "\n".join(rendered) if rendered else "(no steps)"


def read_goal_multiline(prompt_text: str) -> str:
    """Allow multi-line input by ending lines with a backslash."""
    buff = []
    while True:
        line = input(prompt_text if not buff else "  ... ")
        if line.strip().endswith("\\"):
            buff.append(line.rstrip("\\"))
            continue
        buff.append(line)
        return "\n".join(buff).strip()

def handle_command(cmd: str, tool_registry: ToolRegistry, session_agent_state: "AgentState") -> Optional[str]:
    """
    Returns a string to print if handled; None if unknown command.
    Supported:
      :help           Show help
      :tools          List tools
      :state          Show agent context
      :clear          Clear screen
      :quit / :exit   Exit (signal by returning a sentinel string)
    """
    parts = cmd.split()
    name = parts[0].lower()

    if name in (":quit", ":exit"):
        return "__EXIT__"
    if name == ":help":
        return box("Help", "\n".join([
            ":help              Show this help",
            ":tools             Show registered tools",
            ":state             Show agent context",
            ":clear             Clear the screen",
            ":quit / :exit      Quit"
        ]))
    if name == ":tools":
        return box("Tools", tool_registry.list_tools())
    if name == ":state":
        return box("Agent Context", session_agent_state.get_context_string())
    if name == ":clear":
        # portable clear
        os.system("cls" if os.name == "nt" else "clear")
        return status("OK", "Screen cleared.", "32")
    if name == ":ls":
        path = parts[1] if len(parts) > 1 else session_agent_state.last_modified_file or "."
        tool = tool_registry.get_tool("list_dir").fn
        res = tool({"path": path}, tool_registry.get_context())
        color = "32" if res.ok else "31"
        return box(f"ls {path}", res.output) if res.ok else status("ERR", res.output, color)
    return None

class Spinner:
    FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    def __init__(self, text="Thinking...", color="35"):
        self.text = text
        self.color = color
        self._running = False
    def __enter__(self):
        import sys, threading, time
        self._running = True
        def run():
            i = 0
            while self._running:
                sys.stdout.write(f"\r\033[{self.color}m{self.FRAMES[i%len(self.FRAMES)]} {self.text}\033[0m ")
                sys.stdout.flush()
                i += 1
                time.sleep(0.08)
        self._t = threading.Thread(target=run, daemon=True)
        self._t.start()
        return self
    def __exit__(self, *exc):
        import sys
        self._running = False
        self._t.join(timeout=0.1)
        sys.stdout.write("\r" + " " * 80 + "\r")  # clear line
        sys.stdout.flush()


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

def cli(workspace_summary: str, session_agent_state: AgentState):
    print_banner()
    print(status("WELCOME", "HephAIstos, your autonomous coding assistant.", "32"))
    print(status("HINT", "Type a goal, or use :help for commands.", "33"))

    while True:
        goal = read_goal_multiline(color_text("\n🔎 Enter your goal (use '\\' to continue): ", "34"))

        if goal.startswith(":"):
            out = handle_command(goal, tool_registry, session_agent_state)
            if out == "__EXIT__":
                print(status("BYE", "Exiting HephAIstos. Goodbye!", "31"))
                break
            print(out or status("ERR", "Unknown command. Try :help.", "31"))
            continue

        if not goal.strip():
            print(status("WARN", "Empty goal. Try again.", "33"))
            continue

        print("\n" + box("Running", f"Goal: {goal}"))
        with Spinner("Planning & executing...", "35"):
            result = run_agent(goal, tool_registry, max_steps=5,
                               workspace_content=workspace_summary,
                               agent_state=session_agent_state)

        print(color_text("\n--- Agent Scratchpad ---", "36"))
        print(pretty_steps(result))



if __name__ == "__main__":
    workspace_summary = analyze_workspace(os.getcwd())
    session_agent_state = AgentState()
    cli(workspace_summary, session_agent_state)