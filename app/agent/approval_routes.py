from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db
from app.models import User, UserRole, PendingApproval, ApprovalStatus
from app.auth.routes import get_current_user, require_role
from app.agent.sandbox_executor import run_sandboxed_query

router = APIRouter(prefix="/approvals", tags=["approvals"])


class RejectRequest(BaseModel):
    reason: str | None = None


class ApprovalResponse(BaseModel):
    id: str
    status: str
    sql: str
    operation: str
    tables: str
    user_request: str
    requester_id: str
    approver_id: str | None
    execution_result: dict | None = None


@router.get("/pending", response_model=list[ApprovalResponse])
def list_pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.approver)),
):
    pending = db.query(PendingApproval).filter(PendingApproval.status == ApprovalStatus.pending).all()
    return [
        ApprovalResponse(
            id=str(p.id), status=p.status.value, sql=p.sql, operation=p.operation,
            tables=p.tables, user_request=p.user_request,
            requester_id=str(p.requester_id), approver_id=None,
        )
        for p in pending
    ]


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
def approve(
    approval_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.approver)),
):
    approval = db.query(PendingApproval).filter(PendingApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Already resolved (status: {approval.status.value})")

    # Separation of duties — enforced here, at the endpoint, not just assumed in the UI
    if str(approval.requester_id) == str(current_user.id):
        raise HTTPException(status_code=403, detail="You cannot approve your own request")

    # Only NOW, after every check above, does the write credential ever get used
    exec_result = run_sandboxed_query(approval.sql, risk_tier="HIGH")

    approval.status = ApprovalStatus.approved
    approval.approver_id = current_user.id
    approval.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)

    return ApprovalResponse(
        id=str(approval.id), status=approval.status.value, sql=approval.sql,
        operation=approval.operation, tables=approval.tables, user_request=approval.user_request,
        requester_id=str(approval.requester_id), approver_id=str(approval.approver_id),
        execution_result=exec_result,
    )


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
def reject(
    approval_id: str,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.approver)),
):
    approval = db.query(PendingApproval).filter(PendingApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Already resolved (status: {approval.status.value})")

    if str(approval.requester_id) == str(current_user.id):
        raise HTTPException(status_code=403, detail="You cannot reject your own request")

    approval.status = ApprovalStatus.rejected
    approval.approver_id = current_user.id
    approval.rejection_reason = payload.reason
    approval.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)

    return ApprovalResponse(
        id=str(approval.id), status=approval.status.value, sql=approval.sql,
        operation=approval.operation, tables=approval.tables, user_request=approval.user_request,
        requester_id=str(approval.requester_id), approver_id=str(approval.approver_id),
    )