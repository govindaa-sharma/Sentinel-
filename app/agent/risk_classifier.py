import re
from app.agent.state import AgentState

WRITE_OPERATIONS = {"UPDATE", "DELETE", "INSERT"}
WRITE_KEYWORDS = re.compile(r"\b(UPDATE|DELETE|INSERT|DROP|TRUNCATE|ALTER)\b", re.IGNORECASE)


def risk_classifier_node(state: AgentState) -> dict:
    query_plan = state["query_plan"]
    sql = query_plan["sql"]
    reported_operation = query_plan["operation"]

    # Reject multi-statement SQL outright — a single legitimate request never needs more
    # than one statement, and every real attack in our benchmark relied on smuggling extra
    # statements past a self-reported "operation" label.
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) > 1:
        return {
            "risk_tier": "HIGH",
            "verification_passed": False,
            "error_feedback": "Multiple SQL statements detected in one query — not permitted. Write exactly one statement.",
        }

    # Don't trust Codegen's self-reported operation — scan the actual SQL text.
    actual_has_write_keyword = bool(WRITE_KEYWORDS.search(sql))

    risk_tier = "HIGH" if (reported_operation in WRITE_OPERATIONS or actual_has_write_keyword) else "LOW"

    return {"risk_tier": risk_tier}