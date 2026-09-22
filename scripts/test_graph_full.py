from app.agent.graph import sentinel_graph

def run(request: str):
    result = sentinel_graph.invoke({
        "user_request": request,
        "requester_id": "test-user",
        "query_plan": None,
        "risk_tier": None,
        "execution_result": None,
        "verification_passed": None,
        "error_feedback": None,
        "retry_count": 0,
        "terminal_state": None,
    })
    print(f"Request: {request}")
    print(f"Risk tier: {result['risk_tier']}")
    print(f"Execution result: {result.get('execution_result')}")
    print("-" * 60)

run("Show me all clients whose risk score changed by more than 10% this month")
run("Mark client 4021 as inactive")