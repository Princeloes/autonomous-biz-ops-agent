import os
from typing import List, Dict, Any
from langchain_core.tools import tool
from config import settings

@tool
def search_web(query: str) -> str:
    """Searches the web for information regarding the query and returns search results."""
    # 1. Try Tavily if API key is provided
    if settings.TAVILY_API_KEY and not settings.TAVILY_API_KEY.startswith("your_"):
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tavily = TavilySearchResults(max_results=5)
            results = tavily.invoke({"query": query})
            return str(results)
        except Exception as e:
            print(f"Tavily search failed: {e}. Falling back to DuckDuckGo.")

    # 2. Try DuckDuckGo
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if results:
                return "\n\n".join([f"Title: {r['title']}\nLink: {r['href']}\nSnippet: {r['body']}" for r in results])
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}. Falling back to Mock Search.")
        
    # 3. Fallback Mock Search (ensures app works offline/without keys)
    mock_results = {
        "langgraph": "LangGraph is a library for building stateful, multi-actor applications with LLMs, used to create agent and multi-agent workflows. It extends LangChain by allowing cycles and state management.",
        "mem0": "Mem0 (formerly EmbedChain memory) is a memory layer for AI agents, enabling personalized AI interactions by remembering user preferences and past interactions.",
        "langfuse": "Langfuse is an open-source LLM engineering platform that provides tracing, evaluations, prompt management, and metrics to monitor and improve AI applications.",
        "mcp": "Model Context Protocol (MCP) is an open standard that enables developers to build secure, bidirectional connections between AI models and data/tools.",
        "enterprise automation": "Enterprise automation refers to the use of technology, particularly AI agents and RPA, to automate complex business processes like data entry, scheduling, reporting, and emailing."
    }
    
    query_lower = query.lower()
    found = []
    for key, val in mock_results.items():
        if key in query_lower:
            found.append(f"Result for '{key}': {val}")
            
    if found:
        return "\n\n".join(found)
    return f"Mock search result for '{query}': No specific matches found. Please configure a valid TAVILY_API_KEY or verify internet connection."
