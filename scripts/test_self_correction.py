# scripts/test_self_correction.py
from app.agent.graph import sentinel_graph

result = sentinel_graph.invoke({
    "user_request": "Show me the risk score history for client 5, most recent snapshot first",
    "requester_id": "test-user",
    "query_plan": None,
    "risk_tier": None,
    "execution_result": None,
    "verification_passed": None,
    "error_feedback": None,
    "retry_count": 0,
    "terminal_state": None,
})

print("Retry count:", result["retry_count"])
print("Terminal state:", result.get("terminal_state"))
print("Final SQL used:", result["query_plan"]["sql"])
print("Final execution result:", result.get("execution_result"))