import os
import textwrap
import threading
import time
import sys
from typing import Optional

from ..tools import tool_registry, ToolRegistry
from ..core.state import AgentState
from ..core.agent import Agent, react_loop
from ..utils.helpers import _clip

# ========== UI Helpers ==========
BOLD  = "\033[1m"
DIM   = "\033[2m"
RESET = "\033[0m"

def hr(char="─", width=80):
    return char * width

def box(title: str, body: str, width: int = 120) -> str:
    title = f" {title} "
    top    = f"┌{hr('─', width-2)}┐"
    midttl = f"│{title[:width-2].ljust(width-2)}│"
    sep    = f"├{hr('─', width-2)}┤"
    # Wrap each line to the box width
    lines = []
    for line in body.splitlines() or [""]:
        for wrapped in textwrap.wrap(line, width=width-4) or [""]:
            lines.append(f"│ {wrapped.ljust(width-3)}│")
    bot    = f"└{hr('─', width-2)}┘"
    return "\n".join([top, midttl, sep, *lines, bot])

def status(label: str, msg: str, color="36"):  # default cyan
    return f"\033[{color}m[{label}]\033[0m {msg}"

def color_text(text, color_code):
    return f"\033[{color_code}m{text}\033[0m"

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

class Spinner:
    FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    
    def __init__(self, text="Thinking...", color="35"):
        self.text = text
        self.color = color
        self._running = False
    
    def __enter__(self):
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
        self._running = False
        self._t.join(timeout=0.1)
        sys.stdout.write("\r" + " " * 80 + "\r")  # clear line
        sys.stdout.flush()

def get_cli_art():
    return """
                                                                                        
 ▄    ▄               █        █▀     ▄▄   ▄▄▄▄▄   ▀█             ▄                 
 █    █  ▄▄▄   ▄▄▄▄   █ ▄▄     █      ██     █      █     ▄▄▄   ▄▄█▄▄  ▄   ▄   ▄▄▄  
 █▄▄▄▄█ █▀  █  █▀ ▀█  █▀  █    █     █  █    █      █    █   ▀    █    █   █  █   ▀ 
 █    █ █▀▀▀▀  █   █  █   █    █     █▄▄█    █      █     ▀▀▀▄    █    █   █   ▀▀▀▄ 
 █    █ ▀█▄▄▀  ██▄█▀  █   █    █    █    █ ▄▄█▄▄    █    ▀▄▄▄▀    ▀▄▄  ▀▄▄▀█  ▀▄▄▄▀ 
               █               ▀▀                  ▀▀                               
               ▀                                                                    
    """

def print_banner():
    banner = get_cli_art()
    print(color_text(banner, "36"))  # Cyan

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

def handle_command(cmd: str, tool_registry: ToolRegistry, session_agent_state: AgentState) -> Optional[str]:
    """
    Returns a string to print if handled; None if unknown command.
    Supported commands:
      :help           Show help
      :tools          List tools
      :state          Show agent context
      :clear          Clear screen
      :quit / :exit   Exit (signal by returning a sentinel string)
      :ls [path]      List directory contents
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
            ":ls [path]         List directory contents",
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
        return box(f"ls {path}", res.output) if res.ok else status("ERR", res.output, "31")
    
    return None

def cli():
    """Main CLI interface for HephAIstos agent."""
    from groq import Groq
    
    # Initialize client
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
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