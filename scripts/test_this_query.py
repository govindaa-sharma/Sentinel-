# scripts/test_this_query.py
from app.agent.sandbox_executor import run_sandboxed_query

sql = "SELECT DISTINCT c.id, c.name, c.status, c.risk_score, c.created_at FROM clients c JOIN risk_reports rr ON c.id = rr.client_id WHERE rr.month = TO_CHAR(NOW(), 'YYYY-MM') AND rr.risk_score_snapshot != 0 AND ABS((c.risk_score - rr.risk_score_snapshot) / rr.risk_score_snapshot) > 0.10"
print(run_sandboxed_query(sql, risk_tier="LOW"))