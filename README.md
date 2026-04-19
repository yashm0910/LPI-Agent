# LPI LangGraph Advisor

An advanced agentic workflow built with **LangGraph** and **Groq** that interfaces with the Life-Atlas Protocol Interface (LPI). It uses a dynamic "Research-and-Summarize" loop to provide explainable AI advice on digital twin implementations.

## How It Works

The agent uses a keyword-based routing system to determine which LPI tools will provide the most relevant context:

* **`how` / `implement`** -> Triggers `get_methodology_step` + `get_insights`
* **`example` / `case`** -> Triggers `get_case_studies`
* **`what` / `explain` / `overview`** -> Triggers `smile_overview`
* **Default Baseline** -> `query_knowledge` is always included to ensure a deep knowledge base search

## Features

* **Agentic State Machine**: Powered by `StateGraph` for a clear separation between data harvesting and synthesis.
* **Synchronous MCP Bridge**: A robust Python-to-Node.js bridge using JSON-RPC 2.0 to communicate with the LPI server.
* **Structured Explainability**: Uses Pydantic models to force the LLM to cite specific LPI tools used in the final answer.
* **Windows Optimized**: Specifically configured to handle Windows pathing and shell execution for `node` processes.

## Workflow Reference

```python
# Workflow definition in LangGraph
workflow = StateGraph(AgentState)

workflow.add_node("research", research_node)
workflow.add_node("summarize", summarize_node)

workflow.add_edge(START, "research")
workflow.add_edge("research", "summarize")
workflow.add_edge("summarize", END)
```

## Example Output

Below is the verified output from the `research_node` when querying the SMILE methodology:

```text
--- RESEARCHING FOR: What are the core phases of the SMILE methodology? ---
Running tool: query_knowledge
Running tool: smile_overview
--- GENERATING FINAL ANSWER ---

print(result['tool_outputs'])
>> ['Tool Used: query_knowledge | Data: # Knowledge Results\n\n43 entries found for SMILE methodology...', 
    'Tool Used: smile_overview | Data: The SMILE methodology consists of 5 core phases: Strategy, Modeling, Integration, Launch, and Evolution...']
```

## Insights

By utilizing a graph-based state, the agent maintains a **provenance log**. This ensures that every recommendation made by the LLM is backed by a specific tool output, fulfilling the requirements for "Explainable AI" in domain-specific tasks.