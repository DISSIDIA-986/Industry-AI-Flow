/**
 * Command: Create LangChain Agent
 * Generates a new LangChain 1.0 agent with State Graph pattern
 */

import { Message } from "@claude/types";

export const metadata = {
  name: "create-agent",
  description: "Generate a new LangChain 1.0 agent with tools and state management",
  category: "code-generation",
};

export async function execute(args: string[]): Promise<Message> {
  const agentName = args[0] || "custom_agent";
  const agentType = args[1] || "react"; // react, openai-functions, structured

  const agentTemplate = `"""
${agentName} - LangChain 1.0 Agent for Industry AI Flow
Generated with claude-code-templates
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor
import logging

logger = logging.getLogger(__name__)


class ${capitalize(agentName)}State(TypedDict):
    """State for ${agentName}"""
    messages: List[BaseMessage]
    agent_outcome: Optional[AgentAction | AgentFinish]
    intermediate_steps: List[tuple[AgentAction, str]]
    tenant_id: str
    user_id: Optional[str]


class ${capitalize(agentName)}:
    """
    ${capitalize(agentName)} implementation using LangChain 1.0 State Graph.

    Type: ${agentType}
    Purpose: [Describe agent's purpose]

    Tools:
    - [List tools this agent uses]

    Flow:
    1. Parse user input
    2. Execute tools as needed
    3. Generate final response
    """

    def __init__(
        self,
        llm: Any,
        tools: List[BaseTool],
        system_prompt: Optional[str] = None,
    ):
        self.llm = llm
        self.tools = tools
        self.tool_executor = ToolExecutor(tools)

        # Default system prompt
        self.system_prompt = system_prompt or """You are ${agentName}.

Your role: [Define role]
Your capabilities: [List capabilities]
Your constraints: [List constraints]

When responding:
1. Be concise and accurate
2. Use tools when necessary
3. Cite sources when available
4. Handle errors gracefully
"""

        # Build the agent graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        workflow = StateGraph(${capitalize(agentName)}State)

        # Define nodes
        workflow.add_node("agent", self._call_agent)
        workflow.add_node("action", self._execute_tools)

        # Define edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "action",
                "end": END,
            },
        )
        workflow.add_edge("action", "agent")

        return workflow.compile()

    async def _call_agent(
        self, state: ${capitalize(agentName)}State
    ) -> ${capitalize(agentName)}State:
        """Call the LLM agent"""
        messages = state["messages"]

        # Prepare prompt with system message
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("placeholder", "{messages}"),
        ])

        chain = prompt | self.llm.bind_tools(self.tools)
        response = await chain.ainvoke({"messages": messages})

        # Determine outcome
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            agent_outcome = AgentAction(
                tool=tool_call["name"],
                tool_input=tool_call["args"],
                log=str(response),
            )
        else:
            agent_outcome = AgentFinish(
                return_values={"output": response.content},
                log=str(response),
            )

        return {
            **state,
            "agent_outcome": agent_outcome,
            "messages": messages + [response],
        }

    async def _execute_tools(
        self, state: ${capitalize(agentName)}State
    ) -> ${capitalize(agentName)}State:
        """Execute tool actions"""
        agent_outcome = state["agent_outcome"]

        if not isinstance(agent_outcome, AgentAction):
            return state

        # Execute the tool
        try:
            observation = await self.tool_executor.ainvoke(agent_outcome)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            observation = f"Tool execution error: {str(e)}"

        # Update intermediate steps
        intermediate_steps = state.get("intermediate_steps", [])
        intermediate_steps.append((agent_outcome, observation))

        return {
            **state,
            "intermediate_steps": intermediate_steps,
        }

    def _should_continue(self, state: ${capitalize(agentName)}State) -> str:
        """Decide whether to continue or end"""
        agent_outcome = state.get("agent_outcome")

        if isinstance(agent_outcome, AgentFinish):
            return "end"
        return "continue"

    async def invoke(
        self,
        query: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Invoke the agent with a query.

        Args:
            query: User query
            tenant_id: Tenant identifier
            user_id: Optional user identifier
            **kwargs: Additional context

        Returns:
            Agent response with metadata
        """
        initial_state: ${capitalize(agentName)}State = {
            "messages": [HumanMessage(content=query)],
            "agent_outcome": None,
            "intermediate_steps": [],
            "tenant_id": tenant_id,
            "user_id": user_id,
        }

        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)

        # Extract result
        outcome = final_state.get("agent_outcome")
        if isinstance(outcome, AgentFinish):
            return {
                "output": outcome.return_values["output"],
                "intermediate_steps": final_state.get("intermediate_steps", []),
                "success": True,
            }

        return {
            "output": "Agent did not reach a conclusion",
            "intermediate_steps": final_state.get("intermediate_steps", []),
            "success": False,
        }


def capitalize(s: str) -> str:
    """Capitalize agent name"""
    return "".join(word.capitalize() for word in s.split("_"))


# Example usage
if __name__ == "__main__":
    import asyncio
    from langchain_community.llms import Ollama
    from langchain_core.tools import tool

    # Define example tools
    @tool
    def example_tool(query: str) -> str:
        """Example tool implementation"""
        return f"Tool executed with: {query}"

    # Create agent
    llm = Ollama(model="qwen2.5:7b")
    agent = ${capitalize(agentName)}(llm=llm, tools=[example_tool])

    # Test
    result = asyncio.run(
        agent.invoke(
            query="Test query",
            tenant_id="default",
        )
    )
    print(result)
`;

  const message = `Generated ${agentName} agent template at backend/agents/${agentName}.py

Template includes:
- LangChain 1.0 State Graph architecture
- Tool integration with ToolExecutor
- Async/await patterns
- Multi-tenant support
- Error handling
- Type hints (Python 3.13 compatible)

Next steps:
1. Review and customize the agent logic
2. Define specific tools for your use case
3. Update system prompt for domain expertise
4. Add tests in tests/unit/test_${agentName}.py
5. Register agent in backend/agents/__init__.py

Agent type: ${agentType}
Location: backend/agents/${agentName}.py`;

  return {
    role: "assistant",
    content: message,
    metadata: {
      template: agentTemplate,
      targetPath: \`backend/agents/\${agentName}.py\`,
    },
  };
}
