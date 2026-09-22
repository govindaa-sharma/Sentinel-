from app.agent.graph import sentinel_graph

result = sentinel_graph.invoke({
    "user_request": "Show me all clients whose risk score changed by more than 10% this month",
    "requester_id": "test-user",
    "query_plan": None,
    "risk_tier": None,
    "execution_result": None,
    "verification_passed": None,
    "error_feedback": None,
    "retry_count": 0,
    "terminal_state": None,
})

print("Final user_request (after planner):", result["user_request"])
print("\nGenerated query plan:")
print(result["query_plan"])