import os
import time
import asyncio
from core.agent import AutonomousAgentSystem
from config import settings

async def run_evaluation():
    print("=" * 60)
    print("Autonomous Business Operations Agent - Evaluation Suite")
    print("=" * 60)
    print(f"Target Model: {settings.OPENAI_MODEL_NAME}")
    print(f"Mock Mode: {settings.is_mock_mode}")
    print(f"Langfuse Observability: {'Enabled' if settings.LANGFUSE_PUBLIC_KEY else 'Disabled (Offline)'}")
    print("-" * 60)
    
    agent_sys = AutonomousAgentSystem()
    
    test_cases = [
        {
            "name": "Research Only",
            "prompt": "Find the latest updates on LangGraph features and performance."
        },
        {
            "name": "Research + Email + Calendar",
            "prompt": "Research the latest advancements in generative AI, draft a summary report, send it to manager@enterprise.com, and schedule a status review for next Monday at 10 AM."
        },
        {
            "name": "Calendar Only",
            "prompt": "Schedule a meeting for tomorrow at 2 PM to discuss marketing strategies."
        }
    ]
    
    for case in test_cases:
        print(f"\nRunning Test Case: '{case['name']}'")
        print(f"Prompt: \"{case['prompt']}\"")
        
        start_time = time.time()
        
        state = {
            "messages": [("user", case["prompt"])],
            "plan": [],
            "current_step": 0,
            "user_id": "eval_test_user",
            "execution_logs": []
        }
        
        steps = 0
        try:
            async for output in agent_sys.app.astream(state):
                node_name = list(output.keys())[0]
                node_output = output[node_name]
                steps += 1
                print(f"  -> Node Executed: {node_name} (Step {node_output.get('current_step', 0)})")
                
            elapsed = time.time() - start_time
            print(f"Result: Success | Time taken: {elapsed:.2f}s | Graph Nodes traversed: {steps}")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Result: FAILED | Time taken: {elapsed:.2f}s | Error: {e}")
            
    print("\n" + "=" * 60)
    print("Evaluation Complete.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
