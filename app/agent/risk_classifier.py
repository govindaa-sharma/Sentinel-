from app.agent.state import AgentState

WRITE_OPERATIONS = {"UPDATE", "DELETE", "INSERT"}


def risk_classifier_node(state: AgentState) -> dict:
    query_plan = state["query_plan"]
    operation = query_plan["operation"]

    risk_tier = "HIGH" if operation in WRITE_OPERATIONS else "LOW"

    return {"risk_tier": risk_tier}