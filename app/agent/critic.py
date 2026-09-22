from app.agent.state import AgentState

MAX_RETRIES = 3


def critic_node(state: AgentState) -> dict:
    new_retry_count = state["retry_count"] + 1

    if new_retry_count >= MAX_RETRIES:
        return {
            "retry_count": new_retry_count,
            "terminal_state": "FAILED_MAX_RETRIES",
        }

    return {"retry_count": new_retry_count}