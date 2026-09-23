from fastapi import FastAPI
from app.auth.routes import router as auth_router
from app.agent.routes import router as agent_router
from app.agent.approval_routes import router as approval_router

app = FastAPI(title="Rowans")

app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(approval_router)

@app.get("/")
def root():
    return {"status": "Sentinel is running"}