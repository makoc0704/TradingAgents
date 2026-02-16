---
name: create-trading-agent
description: Create a new LLM trading agent for the TradingAgents framework. Use when the user wants to add a new analyst, researcher, debater, or any agent role to the multi-agent trading system.
---

# Create a New Trading Agent

## Workflow

Copy this checklist and track progress:

```
Task Progress:
- [ ] Step 1: Define agent role and category
- [ ] Step 2: Create agent implementation file
- [ ] Step 3: Register in __init__.py
- [ ] Step 4: Add tools/data access if needed
- [ ] Step 5: Integrate into LangGraph workflow
- [ ] Step 6: Update CLI display (if user-facing)
- [ ] Step 7: Write tests
```

## Step 1: Define Agent Role

Determine category and placement in the workflow:

| Category | Location | State Key | Examples |
|----------|----------|-----------|---------|
| Analyst | `agents/analysts/` | `<type>_report` | market, news, social, fundamentals |
| Researcher | `agents/researchers/` | `investment_debate_state` | bull, bear |
| Risk Mgmt | `agents/risk_mgmt/` | `risk_debate_state` | aggressive, conservative, neutral |
| Manager | `agents/managers/` | `investment_plan` or `final_trade_decision` | research_manager, risk_manager |
| Trader | `agents/trader/` | `trader_investment_plan` | trader |

## Step 2: Create Implementation

Create file at `tradingagents/agents/<category>/<role_name>.py`:

```python
import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logger = logging.getLogger(__name__)


def create_<role>_agent(llm, memory=None):
    """Create a <role> agent node.

    Args:
        llm: LangChain LLM instance.
        memory: Optional FinancialSituationMemory for past learnings.

    Returns:
        A callable node function for LangGraph.
    """
    def agent_node(state) -> dict:
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Build situation from reports for memory lookup
        if memory:
            curr_situation = "\n\n".join([
                state.get("market_report", ""),
                state.get("sentiment_report", ""),
                state.get("news_report", ""),
                state.get("fundamentals_report", ""),
            ])
            past_memories = memory.get_memories(curr_situation, n_matches=2)
            past_memory_str = "\n\n".join(
                rec["recommendation"] for rec in past_memories
            ) or "No past memories found."
        else:
            past_memory_str = ""

        # Define system prompt
        system_message = "Your role description here..."

        # Build and invoke chain
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        prompt = prompt.partial(system_message=system_message)

        result = llm.invoke(prompt.format_messages(messages=state["messages"]))

        return {
            "messages": [result],
            # Return appropriate state key for your category
        }

    return agent_node
```

## Step 3: Register in __init__.py

Edit `tradingagents/agents/__init__.py` and add:
```python
from tradingagents.agents.<category>.<role_name> import create_<role>_agent
```

## Step 4: Add Tools (Analyst Agents Only)

If the agent needs data tools:
1. Add tool functions in `agents/utils/agent_utils.py` or reuse existing ones
2. Create a `ToolNode` in `TradingAgentsGraph._create_tool_nodes()` in `graph/trading_graph.py`
3. Bind tools to the agent's LLM chain via `llm.bind_tools(tools)`

## Step 5: Integrate into LangGraph

Edit `tradingagents/graph/setup.py`:

1. Import the factory function
2. Create the node instance in `setup_graph()`
3. Add to workflow: `workflow.add_node("Agent Name", node)`
4. Add edges connecting it to the existing flow
5. If conditional routing needed, add method to `conditional_logic.py`

## Step 6: Update AgentState (if new state fields)

Edit `tradingagents/agents/utils/agent_states.py` to add new fields to `AgentState` TypedDict.

## Step 7: Update CLI

If the agent should appear in the CLI progress display, add it to:
- `cli/main.py` → `MessageBuffer.agent_status` dict
- `cli/main.py` → `teams` dict in `update_display()`

## Step 8: Write Tests

Create `tests/test_agents/test_<role_name>.py`:
- Mock the LLM to return predictable responses
- Test that state updates are correct
- Test memory integration if applicable
