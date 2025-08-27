- We have tool Registry that is being used to keep track and context of all the available tools for the agent.

- We have a bunch of tools defined

- Then We have a Planner function which outputs a series of steps for the agent to use
- The output of the planner function goes to run_agent which is a function being used to execute the tools and basically the plan provided by the planner.

But the problem is that this is not how the loop is supposed to work, the agent is provided with a task, thenn I ask it to think in steps and to output the first step, suppose the agent invokes a tool call then I must call that tool for the agent, after calling I will get an observation I must feed this to the agent and then get another step. This process goes on in a loop for n number of iterations.

Reason
Act
Observe
Repeat for n steps until a task is finished.

Now in the updated implementation
`run_agent`: Is supposed to act as the react_loop
`planner`: Is the brain?
