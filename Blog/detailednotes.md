```
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
    def __init__(self):
        self.tools: Dict[str, ToolFn] = {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool.fn

    def get_tool(self, name: str) -> ToolFn | None:
        if name in self.tools:
            return self.tools[name]
        else:
            raise KeyError(f"Unknown tool: {name}")
    def list_tools(self):
        for tool in self.tools.values():
            print(f"Tool: {tool.name}, Description: {tool.description}")
```

This is the tooling system of the agent
We define a ToolFn that tells what exactly is a tool, so a tool is something that takes in as arugments a dictionary and toolContext and returns a type ToolResult
Finally we define ToolRegistry which is a system to keep track of the avaialbale tools and retrieve them as possible.
