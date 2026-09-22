import random
from datetime import datetime
from app.db import SessionLocal
from app.models import Client, RiskReport

db = SessionLocal()

NAMES = [f"Client {i}" for i in range(1, 51)]
MONTHS = ["2026-06", "2026-07", "2026-08", "2026-09"]

db.query(RiskReport).delete()
db.query(Client).delete()
db.commit()

clients = []
for name in NAMES:
    client = Client(name=name, status="active", risk_score=round(random.uniform(0.1, 0.9), 2))
    db.add(client)
    clients.append(client)
db.commit()

for client in clients:
    score = client.risk_score
    for month in MONTHS:
        score = round(max(0.05, min(0.95, score + random.uniform(-0.15, 0.15))), 2)
        db.add(RiskReport(client_id=client.id, risk_score_snapshot=score, month=month))
db.commit()

print(f"Seeded {len(clients)} clients and {len(clients) * len(MONTHS)} risk reports.")