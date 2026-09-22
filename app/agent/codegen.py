from pydantic import BaseModel, Field
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import get_settings
from app.agent.state import AgentState

settings = get_settings()


class GeneratedQuery(BaseModel):
    sql: str = Field(description="A single valid PostgreSQL statement, no trailing semicolon needed")
    operation: Literal["SELECT", "UPDATE", "DELETE", "INSERT"] = Field(
        description="The primary SQL operation this statement performs"
    )
    tables: list[str] = Field(description="Table names this query reads or writes")


CODEGEN_SYSTEM_PROMPT = """You write PostgreSQL queries for the following schema:

clients (id INTEGER, name TEXT, status TEXT, risk_score FLOAT, created_at TIMESTAMP)
risk_reports (id INTEGER, client_id INTEGER, risk_score_snapshot FLOAT, month TEXT, archived BOOLEAN, created_at TIMESTAMP)

Rules:
- Write exactly ONE SQL statement that accomplishes the instruction.
- Never use DROP, TRUNCATE, or ALTER under any circumstances.
- Use explicit WHERE clauses for UPDATE/DELETE — never affect a whole table unintentionally.
- month values look like '2026-08'.
"""

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.google_api_key,
    temperature=0,
).with_structured_output(GeneratedQuery)


def codegen_node(state: AgentState) -> dict:
    instruction = state["user_request"]
    feedback = state.get("error_feedback")

    human_message = instruction
    if feedback:
        human_message += f"\n\nYour previous attempt failed with this feedback, fix it: {feedback}"

    result: GeneratedQuery = llm.invoke([
        ("system", CODEGEN_SYSTEM_PROMPT),
        ("human", human_message),
    ])

    return {
        "query_plan": {
            "sql": result.sql,
            "operation": result.operation,
            "tables": result.tables,
        },
        "error_feedback": None,  # clear old feedback now that we've used it
    }