from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import get_settings
from app.agent.state import AgentState

settings = get_settings()

# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key, temperature=0)
from app.agent.llm import get_llm
llm = get_llm()

PLANNER_SYSTEM_PROMPT = """You are a planning assistant for a database agent.
Given a user's request, restate it as a single, clear, database-actionable instruction.
Do not write SQL. Do not mention risk. Just clarify what data operation is being asked for.
If the request implies multiple sequential database changes, say so explicitly,
listing each as a separate numbered step.

Available tables: clients (id, name, status, risk_score, created_at),
risk_reports (id, client_id, risk_score_snapshot, month, archived, created_at)
"""


def planner_node(state: AgentState) -> dict:
    response = llm.invoke([
        ("system", PLANNER_SYSTEM_PROMPT),
        ("human", state["user_request"]),
    ])

    return {"user_request": response.content}