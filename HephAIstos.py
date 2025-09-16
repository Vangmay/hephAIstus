from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
import os 
import json 
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv
import subprocess
load_dotenv()

# ========== Helper Functions / Guard Rails ==========
def safe_path(workspace, path) -> str:
    if ".." in path.replace("\\", "/").split("/"):
        raise ValueError("Access to parent directories ('../') is not allowed.")
    abs_path = os.path.abspath(os.path.join(workspace, path))
    return abs_path

def _clip(s, n=4000):
    return s if len(s) <= n else s[:n] + "\n...[truncated]"

def _parse_json(txt: str) -> dict:
    txt = txt.strip()
    # Remove code fences if present
    if txt.startswith("```") and txt.endswith("```"):
        txt = txt.strip("`").strip()
    # Find first '{' and last '}'
    start = txt.find("{")
    end = txt.rfind("}")
    if start != -1 and end != -1 and end > start:
        txt = txt[start:end+1]
    try:
        obj = json.loads(txt)
        # Validate shape
        if "thought" in obj and ("action" in obj or "final" in obj):
            return obj
        else:
            return {"thought": "Parse error: missing required keys.", "action": None, "final": None}
    except Exception as e:
        return {"thought": f"JSON parse error: {e}\nRaw: {txt[:500]}", "action": None, "final": None}
    
# ========== Defining the Tools Registry ========== 
 
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

def _tool_search_web(args: dict, context: ToolContext) -> ToolResult:
    query = args.get("query", "")
    if not query:
        return ToolResult(ok=False, output="No query provided.")
    
    client = OpenAI(
        base_url = "https://api.exa.ai",
        api_key = os.environ.get("EXA_API_KEY"),
    )

    completion = client.chat.completions.create(
        model = "exa",
        messages = [{"role":"user","content": query}],
        stream = False
    )
    return ToolResult(ok=True, output=f"Search Results: {completion.choices[0].message.content}")

def _tool_git_add(args: dict, context: ToolContext) -> ToolResult:
    files = args.get("files", ".")
    try:
        if isinstance(files, str):
            files = [files]
        
        for file in files:
            result = subprocess.run(['git', 'add', file], 
                                   cwd=context.workspace_path, capture_output=True, text=True)
            if result.returncode != 0:
                return ToolResult(ok=False, output=f"Error adding {file}: {result.stderr}")
        
        return ToolResult(ok=True, output=f"Successfully added {files}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error adding files: {e}")

def _tool_git_commit(args: dict, context: ToolContext) -> ToolResult:
    message = args.get("message")
    if not message:
        return ToolResult(ok=False, output="Commit message is required")
    
    try:
        result = subprocess.run(['git', 'commit', '-m', message], 
                               cwd=context.workspace_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            return ToolResult(ok=False, output=f"Error committing: {result.stderr}")
        
        return ToolResult(ok=True, output=f"Committed successfully: {message}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error committing: {e}")
    
def _tool_git_push(args: dict, context: ToolContext) -> ToolResult:
    remote = args.get("remote", "origin")
    branch = args.get("branch", "main")
    try:
        result = subprocess.run(['git', 'push', remote, branch], 
                               cwd=context.workspace_path, capture_output=True, text=True)
        if result.returncode != 0:
            return ToolResult(ok=False, output=f"Error pushing to {remote}/{branch}: {result.stderr}")
        
        return ToolResult(ok=True, output=f"Pushed successfully to {remote}/{branch}")
    except Exception as e:
        return ToolResult(ok=False, output=f"Error pushing: {e}")
    
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
    ),
    "search_web": Tool(
        name="search_web",
        description="Searches the web for a query and returns summarized results.",
        fn=_tool_search_web
    ),
    "git_add": Tool(
        name="git_add",
        description="Add files to git staging area.",
        fn=_tool_git_add
    ),
    "git_commit": Tool(
        name="git_commit",
        description="Commit changes to git repository.",
        fn=_tool_git_commit
    ),
    "git_push": Tool(
        name="git_push",
        description="Push committed changes to remote git repository.",
        fn=_tool_git_push
    ),
}

def build_tool_registry(tool_dict) -> ToolRegistry:
    tool_context = ToolContext()
    tool_registry = ToolRegistry(tool_context)
    for tool in tool_dict.items():
        tool_registry.register(tool[1])
    return tool_registry 

tool_registry = build_tool_registry(tool_dict)
# This will print the list of registered tools with their descriptions.

# ========== Context Matters ==========
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

@dataclass
class AgentState:
    last_modified_file: Optional[str] = None
    recently_created_files: List[str] = field(default_factory=list)
    current_files: Dict[str, str] = field(default_factory=dict)
    session_context: str = ""
    workspace_context: str = analyze_workspace(workspace_path = "./")

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

        if self.workspace_context:
            context_parts.append(f"WORKSPACE CONTEXT:\n{_clip(self.workspace_context, 1000)}")
        
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

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

class Agent():
    def __init__(self, client, tool_registry: ToolRegistry, agent_state: AgentState = AgentState()):
        self.tool_registry = tool_registry
        self.state = AgentState()
        self.messages = []
        self.agent_state = agent_state # Will be used the handle context of the agent
        self.client = client

        self.system_prompt = f"""
            You are a ReAct (Reasoning and Acting) coding assistant.

            Goal: On each turn, emit ONLY the next step needed to progress the task.

            - If your next step is to use a tool: output your "thought" and ONE "action".
            - If your next step is to answer in natural language: output your "thought" and ONE "final".
            Do not output plans, multiple steps, or arrays.

            Available tools: {self.tool_registry.list_tools()}

            AGENT CONTEXT:
            {_clip(self.agent_state.get_context_string())}

            CONTEXT CONTRACT (must follow exactly):

            - If the user refers to “it/this/the file/that” → target AGENT CONTEXT's LAST MODIFIED FILE.
            - If the user uses pronouns about a NON-FILE concept (e.g., places, people, facts),
            resolve them to AGENT CONTEXT's LAST TOPIC.
            - Prefer the 'chat' tool for general Q&A; do NOT mention repo files unless asked.
            - Every file-affecting step MUST include args.path. If missing, auto-fill it from LAST MODIFIED FILE
            and explicitly state that in "thought".
            - The "thought" must explicitly name the target (file or topic).

            I/O Protocol (STRICT):

            - Input to you may include an "observation" from the last tool call; incorporate it before choosing the next step.
            - Your entire output MUST be exactly ONE JSON object with these shapes:

            When the next step is to use a tool:
            {{
                "thought": "<1-2 sentences; name the specific target file or topic>",
                "action": {{
                    "tool": "tool_name",
                    "args": {{"path": "file path if applicable", "content": "file content if applicable",}},
                    "reason": "Short reason for using this tool."
                }}
            }}

            // When the next step is to answer directly (no tool use):
            {{
                "thought": "<1-2 sentences; name the specific target file or topic>",
                "final": {{
                    "message": "<your concise answer to the user>"
                }}
            }}

            Hard rules:

            - Output EXACTLY one of the two shapes above; never include both "action" and "final".
            - Never return an array. Never wrap in markdown/code fences. No extra keys.
            - Keep "thought" brief and target-explicit (e.g., “Target file: src/app.jsx” or “Target topic: API rate limits”).
            - Keep args minimal and valid for the chosen tool. Do not invent tool names or args not listed in Available tools.
            - If a file-affecting step is missing args.path, auto-fill it from the LAST MODIFIED FILE and state this in "thought".
            - If no tool fits, choose the 'chat' tool (general Q&A) or produce "final".
            - If prior observation indicates failure or no results, acknowledge that in "thought" and choose the most informative next step.

            Decision policy:

            - Choose the lowest-cost, most-informative next action that reduces uncertainty or makes concrete progress.
            - If you have sufficient information to answer, prefer "final".

            Now produce ONLY the next step as ONE JSON object, following the schema above.
        """.strip()
        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})
    
    def __call__(self, prompt:str = "") -> str: 
        self.messages.append({"role": "user", "content": prompt})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return _parse_json(result)
    
    def execute(self):
        params = dict(
            model="moonshotai/kimi-k2-instruct",
            messages=self.messages,
            stream=True,
        )
        completion = self.client.chat.completions.create(**params)
        response = ""
        for chunk in completion:
            response += chunk.choices[0].delta.content or ""
        return response

def react_loop(goal, agent: Agent, tool_registry: ToolRegistry, agent_state: AgentState, max_steps: int = 10):
    observation = None
    for step in range(max_steps):
        print(step)
        prompt = goal if step == 0 else f"Observation: {observation.output if observation else ''}"
        response = agent(prompt)
        if "action" in response:
            print("Taking some action...")
            # Some action to take 
            print("RESPONSE: ", response)
            tool_name = response["action"].get("tool")
            tool = tool_registry.get_tool(tool_name).fn
            args = response["action"].get("args", {}) 
            reason = response["action"].get("reason", "") 
            print(f"Using the tool {tool_name} with args {args} because {reason}")
            tool_result = tool(args, tool_registry.get_context())
            # print(f"Tool result: {tool_result.output}")
            agent_state.update_from_tool_result(tool_name, args, tool_result)
            observation = tool_result

        elif "final" in response:
            print("Final answer reached.")
            return response["final"]["message"]
    return agent.messages[-1]["content"] 


# state = AgentState()
# jarvis = Agent(client, tool_registry, agent_state=state)
# react_loop("Summarize the contents of HephAIstos.py in detail. Put them in a new file called blogg.md inside Blog directory", jarvis, tool_registry, state, max_steps=5)

# ========== CLI User Interface ==========

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
    return cli_art_1
    

def color_text(text, color_code):
    return f"\033[{color_code}m{text}\033[0m"

def print_banner():
    banner = get_cli_art()
    print(color_text(banner, "36"))  # Cyan

def cli():
    print_banner()
    print(status("WELCOME", "HephAIstos, your autonomous coding assistant.", "32"))
    print(status("HINT", "Type a goal, or use :help for commands.", "33"))

    session_agent_state = AgentState()
    agent = Agent(client, tool_registry, agent_state=session_agent_state)
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
            result = react_loop(goal, agent, tool_registry, session_agent_state, max_steps=25)

        print(color_text("\n--- Agent Scratchpad ---", "36"))
        print(pretty_steps(result))



if __name__ == "__main__":
    cli()