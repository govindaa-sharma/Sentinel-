from app.agent.graph import sentinel_graph

result = sentinel_graph.invoke({
    "user_request": "Show me all clients ordered by their imaginary_field_that_does_not_exist",
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
print("Verification passed:", result["verification_passed"])
print("Final execution result:", result.get("execution_result"))