from fastapi import FastAPI
from app.auth.routes import router as auth_router
from app.agent.routes import router as agent_router

app = FastAPI(title="Sentinel")

app.include_router(auth_router)
app.include_router(agent_router)

@app.get("/")
def root():
    return {"status": "Sentinel is running"}