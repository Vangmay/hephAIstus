import os 
import  json
import subprocess
from openai import OpenAI
from hephaistos.tools.registry import Tool, ToolContext, ToolResult, ToolRegistry
from hephaistos.utils.helpers import safe_path

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