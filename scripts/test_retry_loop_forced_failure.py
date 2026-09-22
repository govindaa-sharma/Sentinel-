from app.agent.graph import sandbox_executor_node
from app.agent.verifier import verifier_node
from app.agent.critic import critic_node

# Deliberately reference a column that does not exist — guaranteed Postgres error, no LLM involved
state = {
    "user_request": "irrelevant for this test",
    "query_plan": {
        "sql": "SELECT id, totally_fake_column FROM clients LIMIT 5",
        "operation": "SELECT",
        "tables": ["clients"],
    },
    "risk_tier": "LOW",
    "retry_count": 0,
    "terminal_state": None,
}

for attempt in range(1, 5):
    state.update(sandbox_executor_node(state))
    print(f"\nAttempt {attempt} — execution result:", state["execution_result"])

    state.update(verifier_node(state))
    print(f"Attempt {attempt} — verification passed:", state["verification_passed"])

    if state["verification_passed"]:
        print("SUCCESS")
        break

    state.update(critic_node(state))
    print(f"Attempt {attempt} — retry_count now:", state["retry_count"], "terminal_state:", state.get("terminal_state"))

    if state.get("terminal_state") == "FAILED_MAX_RETRIES":
        print("Correctly stopped at max retries.")
        break