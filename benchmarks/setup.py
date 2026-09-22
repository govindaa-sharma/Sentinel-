from app.db import SessionLocal
from app.models import User, UserRole
from app.auth.security import hash_password

def get_or_create_benchmark_user() -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "benchmark_runner").first()
        if not user:
            user = User(
                username="benchmark_runner",
                hashed_password=hash_password("not-a-real-login"),
                role=UserRole.requester,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return str(user.id)
    finally:
        db.close()