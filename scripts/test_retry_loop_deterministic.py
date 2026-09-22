from app.agent.critic import critic_node

state = {"retry_count": 0, "terminal_state": None}
for i in range(5):
    update = critic_node(state)
    state.update(update)
    print(f"Attempt {i+1}: retry_count={state['retry_count']}, terminal_state={state.get('terminal_state')}")
    if state.get("terminal_state") == "FAILED_MAX_RETRIES":
        print("Stopped correctly at max retries.")
        break