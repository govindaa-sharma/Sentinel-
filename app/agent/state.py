from typing import TypedDict, Optional, Literal


class QueryPlan(TypedDict):
    sql: str
    operation: Literal["SELECT", "UPDATE", "DELETE", "INSERT"]
    tables: list[str]


class AgentState(TypedDict):
    user_request: str          # the original natural-language ask
    requester_id: str          # from the JWT, who asked
    query_plan: Optional[QueryPlan]   # filled in by Codegen
    risk_tier: Optional[Literal["LOW", "HIGH"]]  # filled in by Risk Classifier
    execution_result: Optional[dict]  # filled in by Sandbox Executor
    verification_passed: Optional[bool]
    error_feedback: Optional[str]     # filled in by Critic on failure
    retry_count: int
    terminal_state: Optional[str]     # SUCCESS / FAILED_MAX_RETRIES / etc.