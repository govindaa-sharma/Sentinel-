from app.db import Base, engine
from app import models  # noqa: F401 — import so SQLAlchemy registers the User model

Base.metadata.create_all(bind=engine)
print("Tables created.")