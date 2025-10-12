from groq import Groq
import os

from hephaistos.tools.registry import ToolRegistry, ToolResult
from hephaistos.utils.helpers import _parse_json, _clip
from hephaistos.core.state import AgentState

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
            model="moonshotai/kimi-k2-instruct-0905",
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
        prompt = goal if step == 0 else f"Observation: {observation.output if observation else ''}"
        response = agent(prompt)
        if "action" in response:
            print("Taking some action...")
            # Some action to take 
            tool_name = response["action"].get("tool")
            tool = tool_registry.get_tool(tool_name).fn
            args = response["action"].get("args", {}) 
            reason = response["action"].get("reason", "") 
            print(response)
            print(f"Using the tool {tool_name} with args {args} so that I can {reason}")
            tool_result = tool(args, tool_registry.get_context())
            agent_state.update_from_tool_result(tool_name, args, tool_result)
            observation = tool_result

        elif "final" in response:
            print("Final answer reached.")
            return response["final"]["message"]
    return agent.messages[-1]["content"] 
