import os
import json
import subprocess
import asyncio
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()

_REPO_ROOT = r"C:\Users\Muskan Kirti\yash_lpi"
LPI_SERVER_CMD = ["node", os.path.join(_REPO_ROOT, "dist", "src", "index.js")]
LPI_SERVER_CWD = _REPO_ROOT

class LPIAgentResponse(BaseModel):
    """ Structured response for the LPI implementation advisor """
    answer: str = Field(description="The synthesized advice for the user's business scenario.")
    steps: List[str] = Field(description="A list of actionable implementation steps.")
    sources: List[str] = Field(description="Citations of the LPI tools and specific data points used.")

class AgentState(TypedDict):
    input: str
    tool_outputs: List[str]      
    final_output: LPIAgentResponse

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile", 
    temperature=0
)
structured_llm = llm.with_structured_output(LPIAgentResponse)

def call_lpi_tool_sync(tool_name: str, arguments: dict) -> str:
    """Synchronous bridge to the LPI MCP server with JSON-RPC logic."""
    try:
        proc = subprocess.Popen(
            LPI_SERVER_CMD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=LPI_SERVER_CWD,
            shell=True 
        )

        # Handshake logic
        init_req = {
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "langgraph-agent", "version": "1.0.0"},
            },
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()
        proc.stdout.readline() # Consume init response
        
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        # Tool calling logic
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()

        line = proc.stdout.readline()
        proc.terminate()
        
        if line:
            resp = json.loads(line)
            if "result" in resp and "content" in resp["result"]:
                return resp["result"]["content"][0].get("text", "No content")
        return f"[ERROR] Tool {tool_name} failed to return content."
    
    except Exception as e:
        return f"[ERROR] Subprocess crash: {str(e)}"

def choose_lpi_tools(query: str) -> List[str]:
    """Dynamically selects tools based on keywords in the query."""
    query = query.lower()
    tools = []

    if any(word in query for word in ["how", "implement"]):
        tools.extend(["get_methodology_step", "get_insights"])
    if any(word in query for word in ["example", "case"]):
        tools.append("get_case_studies")
    if any(word in query for word in ["what", "explain", "overview"]):
        tools.append("smile_overview")

    # Mandatory baseline tool for Level 3
    if "query_knowledge" not in tools:
        tools.append("query_knowledge")

    return list(set(tools))


def research_node(state: AgentState):
    """Executes selected LPI tools with error handling."""
    print(f"\n--- RESEARCHING: {state['input']} ---")
    selected_tools = choose_lpi_tools(state["input"])
    results = []
    
    for tool in selected_tools:
        try:
            print(f"Running LPI Tool: {tool}")
            data = call_lpi_tool_sync(tool, {"query": state["input"]})
            
            if not data or "[ERROR]" in data:
                raise ValueError(f"Tool {tool} execution failed or returned error.")
                
            results.append(f"Source [{tool}]: {data[:1000]}")
            
        except Exception as e:
            print(f"⚠️ Error in {tool}: {e}")
            results.append(f"Source [{tool}]: Execution Error ({str(e)})")
            
    state["tool_outputs"] = results if results else ["No data retrieved from LPI."]
    return state

def summarize_node(state: AgentState):
    """Synthesizes tool data into a structured response."""
    print("--- SUMMARIZING FINDINGS ---")
    prompt = f"""
    You are an expert LPI advisor. Answer the user question using ONLY the context provided.
    
    Context: {state['tool_outputs']}
    User Query: {state['input']}
    """
    
    try:
        state["final_output"] = structured_llm.invoke(prompt)
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        state["final_output"] = LPIAgentResponse(
            answer="Technical error in synthesis.",
            steps=["Verify API configuration"],
            sources=["System Fallback"]
        )
    return state

# --- WORKFLOW CONSTRUCTION ---

workflow = StateGraph(AgentState)
workflow.add_node("research", research_node)
workflow.add_node("summarize", summarize_node)
workflow.add_edge(START, "research")
workflow.add_edge("research", "summarize")
workflow.add_edge("summarize", END)
agent_app = workflow.compile()


if __name__ == "__main__":
    # Environment Check
    target_js = os.path.join(_REPO_ROOT, "dist", "src", "index.js")
    print(f"Server script found: {os.path.exists(target_js)}")
    
    query = "What are the core phases of the SMILE methodology?"
    final_result = agent_app.invoke({"input": query})
    
    print("\n--- FINAL AGENT RESPONSE ---")
    print(f"Answer: {final_result['final_output'].answer}")
    print(f"Steps: {final_result['final_output'].steps}")
    print(f"Sources: {final_result['final_output'].sources}")