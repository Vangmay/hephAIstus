from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
import os 
import requests
import json 
from urllib import request, error as urlerror
from groq import Groq
import random
from dotenv import load_dotenv
load_dotenv()

# ========== Helper Functions / Guard Rails ==========
def safe_path(workspace, path) -> str:
    if ".." in path.replace("\\", "/").split("/"):
        raise ValueError("Access to parent directories ('../') is not allowed.")
    abs_path = os.path.abspath(os.path.join(workspace, path))
    return abs_path

def _clip(s, n=4000):
    return s if len(s) <= n else s[:n] + "\n...[truncated]"

def _parse_json(txt: str) -> list:
    txt = txt.strip()
    if not txt:
        return [{"tool": None, "args": {}, "thought": "Planner returned empty content."}]
    # Find first '[' and last ']'
    start = txt.find("[")
    end = txt.rfind("]")
    if start != -1 and end != -1 and end > start:
        txt = txt[start:end+1]
    try:
        obj = json.loads(txt)
        return obj if isinstance(obj, list) else [{"tool": None, "args": {}, "thought": f"Non-list planner output: {txt}..."}]
    except Exception as e:
        return [{"tool": None, "args": {}, "thought": f"Planner JSON error: {e}\nRaw: {txt[:500]}"}]
    
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
    def __init__(self, client, tool_registry: ToolRegistry, system_prompt: str = "", agent_state: AgentState = AgentState()):
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
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
        return result
    
    def execute(self):
        params = dict(
            model="moonshotai/kimi-k2-instruct",
            messages=self.messages,
            # temperature=0.6,
            # max_completion_tokens=4096,
            # top_p=1,
            stream=True,
            # stop=None
        )
        completion = self.client.chat.completions.create(**params)
        response = ""
        for chunk in completion:
            response += chunk.choices[0].delta.content or ""
        return response



state = AgentState()
jarvis = Agent(client, tool_registry, agent_state=state)
system_prompt = jarvis.system_prompt
Result = jarvis("Read the content of HephAIstos.py and summarize its purpose.")
print(Result)
observation = _tool_read_file({"path": "HephAIstos.py"}, tool_registry.get_context())
Result = jarvis(f"Observation: {observation.output}")


# def planner(goal: str, scratchpad: list[str], tools: ToolRegistry, steps: int = 5, workspace_context: str = "Workspace is empty", agent_context: str = "") -> dict:
#     """
#     Prompts an LLM to select a tool and arguments for the agent.
#     Returns a dict: {"tool": <tool_name>, "args": {...}, "thought": <reasoning>}
#     """
#     def _clip(s, n=4000):
#         return s if len(s) <= n else s[:n] + "\n...[truncated]"
    
    
    
#     user_prompt = f"""
#         You are a ReAct (Reasoning and Acting) coding agent tasked with answering the following query:
#         User query: {goal}

#         WORKSPACE CONTEXT:
#         {_clip(workspace_context, )}

#         AGENT CONTEXT:
#         {_clip(agent_context)}

#         Previous reasoning steps and observations: {_clip("".join(scratchpad))}

#         Instructions:
#             1. Analyze the query, previous reasoning steps, observations, and the provided Agent and Workspace contexts.
#             2. Decide on the next action: use a tool or provide a final answer.
#             3. Respond in the following JSON format:
        
#         Break the task into sequential steps. Return ONLY the JSON array, no markdown.
#         Example:
#             {{
#                 "thought": "Your detailed reasoning about what to do next",
#                 "action": {{
#                     "tool": "tool_name",
#                     "args": {{"path": "file path if applicable", "content": "file content if applicable",}},
#                     "reason": "Short reason for using this tool."
#                 }}
#             }}

#         Remember:
#             - Be thorough in your reasoning.
#             - Use tools when you need more information.
#             - Always base your reasoning on the actual observations from tool use.
#             - If a tool returns no results or fails, acknowledge this and consider using a different tool or approach.
#             - Provide a final answer only when you're confident you have sufficient information.
#             - If you cannot find the necessary information after using available tools, admit that you don't have enough information to answer the query confidently.
#         """

#     client = Cerebras(
#         # This is the default and can be omitted
#         api_key=os.environ.get("cerebras_api_key"),
#     )

#     params = dict(
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt},
#         ],
#         model="qwen-3-32b",
#         max_completion_tokens=2048,
#         temperature=0.6,
#         top_p=0.95
#     )

#     def _parse_json(txt: str) -> list:
#         txt = txt.strip()
#         if not txt:
#             return [{"tool": None, "args": {}, "thought": "Planner returned empty content."}]
#         # Find first '[' and last ']'
#         start = txt.find("[")
#         end = txt.rfind("]")
#         if start != -1 and end != -1 and end > start:
#             txt = txt[start:end+1]
#         try:
#             obj = json.loads(txt)
#             return obj if isinstance(obj, list) else [{"tool": None, "args": {}, "thought": f"Non-list planner output: {txt[:200]}..."}]
#         except Exception as e:
#             return [{"tool": None, "args": {}, "thought": f"Planner JSON error: {e}\nRaw: {txt[:500]}"}]

#     response_text = ""
#     try:
#         stream = client.chat.completions.create(stream=True, **params)
#         for chunk in stream:
#             delta = chunk.choices[0].delta
#             if delta and getattr(delta, "content", None):
#                 response_text += delta.content
#     except Exception as _:
#         response_text = ""

#     if not response_text.strip():
#         try:
#             resp = client.chat.completions.create(stream=False, **params)
#             response_text = resp.choices[0].message.content or ""
#         except Exception as e:
#             return [{"tool": None, "args": {}, "thought": f"Planner transport error: {e}"}]
        
#     print("Response from planner: ", response_text)
#     return _parse_json(response_text)


# def run_agent(goal: str, tool_registry: ToolRegistry, max_steps: int = 5, workspace_content: str = "Workspace is empty", agent_state: AgentState = None) -> str:
#     if agent_state is None:  
#         agent_state = AgentState() 
    
#     scratchpad = []
#     plan_steps = planner(goal, scratchpad, tool_registry, max_steps, workspace_content, agent_state.get_context_string())
    
#     for idx, step in enumerate(plan_steps):
#         print(step)
#         action = step.get("action", {})
#         tool_name = action.get("tool")
#         args = action.get("args", {})
#         reasoning = action.get("reason", "")
        
#         if not tool_name or tool_name not in tool_registry.tools:
#             print(f"Invalid tool name: {tool_name}. Stopping.")
#             break

#         tool_fn = tool_registry.get_tool(tool_name).fn
#         result = tool_fn(args, tool_registry.get_context())
#         # print(f"Result: {result.output}")

#         agent_state.update_from_tool_result(tool_name, args, result)
#         if tool_name == "chat" and result.ok:
#             agent_state.last_topic = args.get("message", "")[:100]
#             agent_state.last_answer = result.output[:200]

#         scratchpad_entry = f"Thought: {reasoning}\nAction: {tool_name}\nAction Input: {json.dumps(args)}\nObservation: {result.output}\n" 
#         scratchpad.append(scratchpad_entry)
    
#     print("\nAgent Run complete")
#     return "\n".join(scratchpad)


