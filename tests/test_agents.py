import os
import pytest
from core.memory import MemoryManager
from core.agent import AutonomousAgentSystem
from tools.research_tool import search_web
from tools.email_tool import list_emails, send_email
from tools.calendar_tool import list_calendar_events, schedule_event
from tools.reporting_tool import generate_report

def test_memory_manager():
    """Test that the memory manager can store and retrieve memories."""
    # Ensure clean state by using a test database
    db_path = "test_memories.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    try:
        from core.memory import LocalMemoryStore
        store = LocalMemoryStore(db_path=db_path)
        
        # Test add
        mem_id = store.add("test_user", "Prefers reports in markdown format.")
        assert mem_id is not None
        
        # Test search
        results = store.search("test_user", "markdown")
        assert len(results) == 1
        assert "markdown" in results[0]["text"]
        
        # Test get_all
        all_mems = store.get_all("test_user")
        assert len(all_mems) == 1
        
        # Test delete
        store.delete(mem_id)
        assert len(store.get_all("test_user")) == 0
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass

def test_tools():
    """Test that the tools return expected responses."""
    # Test search mock fallback
    search_res = search_web.invoke({"query": "What is LangGraph?"})
    assert "LangGraph" in search_res
    
    # Test email mock
    email_res = send_email.invoke({
        "to_address": "test@example.com",
        "subject": "Test Subj",
        "body": "Test Body"
    })
    assert "Test Subj" in email_res
    assert "successfully sent" in email_res
    
    emails_list = list_emails.invoke({})
    assert "Test Subj" in emails_list

    # Test calendar mock
    cal_res = schedule_event.invoke({
        "title": "Test Meeting",
        "start_time": "2026-07-25 10:00:00",
        "end_time": "2026-07-25 11:00:00",
        "description": "Test"
    })
    assert "Test Meeting" in cal_res
    
    events_list = list_calendar_events.invoke({})
    assert "Test Meeting" in events_list

    # Test report generation
    report_res = generate_report.invoke({
        "title": "Test Report",
        "content": "Test content details."
    })
    assert "successfully generated" in report_res
    assert "reports" in report_res

def test_agent_graph():
    """Test that the LangGraph compiles and is runnable."""
    agent_sys = AutonomousAgentSystem()
    assert agent_sys.app is not None
    
    # Run a simple step in mock mode
    state = {
        "messages": [("user", "research LangGraph and send email")],
        "plan": [],
        "current_step": 0,
        "user_id": "test_user",
        "execution_logs": []
    }
    
    # Test planning node directly
    plan_out = agent_sys.plan_node(state)
    assert len(plan_out["plan"]) > 0
    assert plan_out["plan"][0]["tool"] == "search_web"
