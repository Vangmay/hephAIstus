from dataclasses import dataclass, field
from typing import  Dict, List, Optional
import os 

from hephaistos.tools.registry import ToolResult
from hephaistos.utils.helpers import _clip


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