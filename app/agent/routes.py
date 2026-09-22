from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.routes import get_current_user
from app.models import User
from app.agent.graph import sentinel_graph

router = APIRouter(prefix="/agent", tags=["agent"])


class AskRequest(BaseModel):
    request: str


class AskResponse(BaseModel):
    risk_tier: str | None
    query_plan: dict | None
    execution_result: dict | None
    status: str


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, current_user: User = Depends(get_current_user)):
    result = sentinel_graph.invoke({
        "user_request": payload.request,
        "requester_id": str(current_user.id),   # from the JWT, never trust client-supplied identity
        "query_plan": None,
        "risk_tier": None,
        "execution_result": None,
        "verification_passed": None,
        "error_feedback": None,
        "retry_count": 0,
        "terminal_state": None,
    })

    if result["risk_tier"] == "HIGH":
        status = "pending_approval"
    elif result.get("execution_result", {}).get("success"):
        status = "success"
    else:
        status = "failed"

    return AskResponse(
        risk_tier=result["risk_tier"],
        query_plan=result["query_plan"],
        execution_result=result.get("execution_result"),
        status=status,
    )