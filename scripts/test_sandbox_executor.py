from app.agent.sandbox_executor import run_sandboxed_query

print("LOW risk read:")
print(run_sandboxed_query("SELECT id, name, risk_score FROM clients LIMIT 3", risk_tier="LOW"))

print("\nLOW risk attempting a write (should be blocked by the DB role, not by our code):")
print(run_sandboxed_query("UPDATE clients SET status='inactive' WHERE id=1", risk_tier="LOW"))

print("\nHIGH risk write (using writer role, simulating post-approval execution):")
print(run_sandboxed_query("UPDATE clients SET status='active' WHERE id=1", risk_tier="HIGH"))