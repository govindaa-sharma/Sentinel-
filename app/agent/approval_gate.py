import uuid
from app.db import SessionLocal
from app.models import PendingApproval
from app.agent.state import AgentState


def approval_gate_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        approval = PendingApproval(
            id=uuid.uuid4(),
            requester_id=state["requester_id"],
            sql=state["query_plan"]["sql"],
            operation=state["query_plan"]["operation"],
            tables=",".join(state["query_plan"]["tables"]),
            user_request=state["user_request"],
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        return {
            "terminal_state": "PENDING_APPROVAL",
            "execution_result": {"approval_id": str(approval.id)},
        }
    finally:
        db.close()