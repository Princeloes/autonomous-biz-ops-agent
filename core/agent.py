import os
import json
from typing import Annotated, Sequence, TypedDict, Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import settings
from tools.research_tool import search_web
from tools.browser_tool import browse_website
from tools.email_tool import list_emails, send_email, mark_as_read
from tools.calendar_tool import list_calendar_events, schedule_event
from tools.reporting_tool import generate_report
from core.memory import MemoryManager
from langfuse.langchain import CallbackHandler

# Initialize Langfuse Callback if credentials exist
langfuse_handler = None
if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
    langfuse_handler = CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST
    )

# Define State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    plan: List[Dict[str, Any]]
    current_step: int
    user_id: str
    execution_logs: List[str]

# Tools list
TOOLS = [
    search_web,
    browse_website,
    list_emails,
    send_email,
    mark_as_read,
    list_calendar_events,
    schedule_event,
    generate_report
]

# Helper to find tool by name
tools_by_name = {tool.name: tool for tool in TOOLS}

class AutonomousAgentSystem:
    def __init__(self):
        self.memory = MemoryManager()
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        # Define the nodes
        workflow.add_node("planner", self.plan_node)
        workflow.add_node("executor", self.execute_node)
        workflow.add_node("reporter", self.report_node)

        # Build graph
        workflow.add_edge(START, "planner")
        workflow.add_conditional_edges(
            "planner",
            self.route_after_planning,
            {
                "execute": "executor",
                "report": "reporter",
                "end": END
            }
        )
        workflow.add_edge("executor", "planner")
        workflow.add_edge("reporter", END)

        return workflow

    def plan_node(self, state: AgentState) -> Dict[str, Any]:
        """Planner Node: Evaluates progress, updates plan, and decides next step."""
        messages = state.get("messages", [])
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        user_id = state.get("user_id", "default_user")
        logs = state.get("execution_logs", [])

        user_query = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_query = m.content
                break

        # Load memories to enrich the planner
        memories = self.memory.search_memories(user_id, user_query, limit=3)
        memory_context = "\n".join([f"- {m['text']}" for m in memories]) if memories else "None"

        logs.append(f"[Planner] Analyzing goals. Current step: {current_step}/{len(plan)}. Memory Context found: {len(memories)} items.")

        if not plan:
            # Generate plan
            if settings.is_mock_mode:
                # Rule-based plan generation for demonstration
                logs.append("[Planner] Mock mode active. Generating rule-based plan.")
                plan = self._generate_mock_plan(user_query)
            else:
                # LLM based plan generation
                llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL_NAME, 
                    openai_api_key=settings.OPENAI_API_KEY,
                    temperature=0
                )
                prompt = (
                    f"You are the Lead Planner for an Autonomous Business Operations Agent.\n"
                    f"User goal: {user_query}\n"
                    f"User Memories:\n{memory_context}\n\n"
                    f"Break down this request into a sequential list of tasks. Each task must specify a 'tool' and a 'description'.\n"
                    f"Available tools: {[t.name for t in TOOLS]}\n\n"
                    f"Respond ONLY with a JSON list of tasks, e.g.:\n"
                    f"[{{\"task_index\": 0, \"tool\": \"search_web\", \"description\": \"search for target query\", \"status\": \"pending\"}}]"
                )
                try:
                    callbacks = [langfuse_handler] if langfuse_handler else []
                    response = llm.invoke(prompt, config={"callbacks": callbacks})
                    plan = json.loads(response.content)
                except Exception as e:
                    logs.append(f"[Planner Error] Failed LLM planning, using fallback. Error: {e}")
                    plan = self._generate_mock_plan(user_query)

        # Check if we have more steps to execute
        next_action = "execute"
        if len(plan) == 0:
            next_action = "end"
        elif current_step >= len(plan):
            next_action = "report"

        return {
            "plan": plan,
            "current_step": current_step,
            "execution_logs": logs
        }

    def route_after_planning(self, state: AgentState) -> str:
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        if not plan:
            return "end"
        if current_step >= len(plan):
            return "report"
        return "execute"

    def execute_node(self, state: AgentState) -> Dict[str, Any]:
        """Executor Node: Runs the current step in the plan using the assigned tool."""
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        logs = state.get("execution_logs", [])
        
        if current_step >= len(plan):
            return {"current_step": current_step}

        task = plan[current_step]
        tool_name = task.get("tool")
        description = task.get("description")
        
        logs.append(f"[Executor] Executing step {current_step}: {description} using tool '{tool_name}'")

        tool_result = ""
        if settings.is_mock_mode:
            # Mock execution
            tool_result = self._execute_mock_tool(tool_name, description)
        else:
            # LLM-based tool calling
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL_NAME, 
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0
            )
            # Create a tool execution loop or single tool call
            # For robustness, we map the tool to its parameters using the description
            prompt = (
                f"We need to run the tool '{tool_name}' for the task: '{description}'.\n"
                f"Explain what argument/parameters we should pass to this tool based on the task description.\n"
                f"Respond with a JSON dictionary matching the tool's expected argument name(s) and value(s).\n"
                f"Tool info: {tools_by_name[tool_name].description}\n"
                f"Example format: {{\"query\": \"value\"}}"
            )
            try:
                callbacks = [langfuse_handler] if langfuse_handler else []
                response = llm.invoke(prompt, config={"callbacks": callbacks})
                args = json.loads(response.content)
                target_tool = tools_by_name[tool_name]
                tool_result = target_tool.invoke(args)
            except Exception as e:
                logs.append(f"[Executor Error] LLM tool call failed: {e}. Attempting manual execution fallback.")
                tool_result = self._execute_mock_tool(tool_name, description)

        logs.append(f"[Executor] Completed step {current_step}. Result snippet: {str(tool_result)[:100]}...")
        plan[current_step]["status"] = "completed"
        plan[current_step]["result"] = tool_result
        
        # Save memory of this execution if it is key information
        user_id = state.get("user_id", "default_user")
        self.memory.add_memory(user_id, f"Executed task '{description}' using '{tool_name}'.")

        return {
            "plan": plan,
            "current_step": current_step + 1,
            "execution_logs": logs
        }

    def report_node(self, state: AgentState) -> Dict[str, Any]:
        """Reporter Node: Generates the final report and aggregates all task outcomes."""
        plan = state.get("plan", [])
        logs = state.get("execution_logs", [])
        user_id = state.get("user_id", "default_user")
        
        logs.append("[Reporter] Compiling results into final report.")
        
        summary_results = []
        for task in plan:
            summary_results.append(
                f"### Task {task.get('task_index', 0)}: {task.get('description')}\n"
                f"- **Tool Used**: {task.get('tool')}\n"
                f"- **Status**: {task.get('status')}\n"
                f"- **Result**: {task.get('result')}\n"
            )
            
        full_report_content = "\n".join(summary_results)
        
        # Call generate report tool
        report_output = ""
        try:
            report_output = generate_report.invoke({
                "title": "Business Operations Summary Report",
                "content": full_report_content
            })
            logs.append(f"[Reporter] {report_output}")
        except Exception as e:
            logs.append(f"[Reporter Error] Failed to generate report: {e}")
            
        final_message = AIMessage(
            content=f"Operations completed successfully.\n\n### Report Summary\n{full_report_content}\n\n{report_output}"
        )
        
        return {
            "messages": [final_message],
            "execution_logs": logs
        }

    def _generate_mock_plan(self, query: str) -> List[Dict[str, Any]]:
        query_l = query.lower()
        plan = []
        index = 0
        
        # Always do a search first
        plan.append({
            "task_index": index,
            "tool": "search_web",
            "description": f"Search the web for details related to: {query}",
            "status": "pending"
        })
        index += 1

        # If email mentioned
        if "email" in query_l or "send" in query_l:
            plan.append({
                "task_index": index,
                "tool": "send_email",
                "description": f"Send summary email of research to manager@enterprise.com",
                "status": "pending"
            })
            index += 1
            
        # If calendar mentioned
        if "calendar" in query_l or "schedule" in query_l or "meeting" in query_l:
            plan.append({
                "task_index": index,
                "tool": "schedule_event",
                "description": "Schedule a Q3 Planning Review meeting for next Monday at 10 AM",
                "status": "pending"
            })
            index += 1

        # Generate final report
        plan.append({
            "task_index": index,
            "tool": "generate_report",
            "description": "Compile research and operations summary report",
            "status": "pending"
        })
        
        return plan

    def _execute_mock_tool(self, name: str, description: str) -> str:
        """Executes the tool with simulated input arguments based on description."""
        tool_fn = tools_by_name.get(name)
        if not tool_fn:
            return f"Error: Tool {name} not found."
            
        # Extract plausible arguments
        if name == "search_web":
            # Extract query after 'related to:' or use description
            q = description.split("related to:")[-1].strip() if "related to:" in description else description
            return tool_fn.invoke({"query": q})
        elif name == "send_email":
            return tool_fn.invoke({
                "to_address": "manager@enterprise.com",
                "subject": "Automated Business Operations Report",
                "body": "Hi, please find the attached research report compiled by your AI Employee."
            })
        elif name == "schedule_event":
            return tool_fn.invoke({
                "title": "Operations Review",
                "start_time": "2026-07-27 10:00:00",
                "end_time": "2026-07-27 11:00:00",
                "description": "Meeting to review automated report."
            })
        elif name == "generate_report":
            return tool_fn.invoke({
                "title": "Operations Report",
                "content": f"Automated summary generated from execution: {description}"
            })
        elif name == "browse_website":
            return "Mock browse content for: " + description
        else:
            return tool_fn.invoke({})
