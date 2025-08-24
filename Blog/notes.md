- So to build an AI agent we have to build 3 systems in place
  Welcome to my friendly blog! 😊

- Tool Implementations
- Let’s talk about the cool tools we’re building

  - Provide conrete actions that the agent can perform
  - Each tool should have a function that takes arguments and context, performs the action and returns the results

- A Tool Registry

  - Its purpose is to manage available tools and to provide a standard interface

- Planner

  - Decide what action the agent should take next based on the goal and current state
  - Analyze the goal and scratchpad, propose either a tool call or a final message. Start with a rule based planner an later add a LLM-based planner
  - This is the brain of the agent, it decides how to systematically acheive a given task

- Agent Core

  - Orchestrate the agent loop: receive a goal, interact with the planner, execute tool calls, maintain a scratchpad and decide when to stop.

- CLI Interface

  - Provide a way for the users to interact with the agent.
  - Accept user goals, display agent actions and results, handle exit conditions.

- Utilities
  - Support common operations like safe file access, clamping
  - For Example, we might want to prevent the agent from calling rm rf
  - We might want to prevent the agent from accessing files not in the current direction (Going to ../)

Thanks for reading! Hope you enjoyed the friendly vibe. 🙌
