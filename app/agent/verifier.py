from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import get_settings
from app.agent.state import AgentState

settings = get_settings()


class SanityCheck(BaseModel):
    passes_sanity_check: bool
    reason: str


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.google_api_key,
    temperature=0,
).with_structured_output(SanityCheck)

SANITY_PROMPT = """You are reviewing whether a database query result plausibly answers the user's request.
You are NOT checking SQL syntax — only whether the result looks like a sane answer to the question.

Flag as failing sanity check if:
- The result set size seems implausibly large for a request implying a selective filter
  (e.g. "more than 10% change" matching 75%+ of all rows is suspicious)
- The result is empty when the request implies matches should exist
- The result shape doesn't match what was asked (e.g. asked for one client, got fifty)

Be lenient — only flag genuinely implausible results, not just "could be different."
"""


def verifier_node(state: AgentState) -> dict:
    execution_result = state["execution_result"]

    # Layer 1: did it even run without error? (rule-based, no LLM needed)
    if not execution_result or not execution_result.get("success"):
        return {
            "verification_passed": False,
            "error_feedback": f"Query execution failed: {execution_result.get('error') if execution_result else 'no result'}",
        }

    # Layer 2: rule-based structural sanity (cheap, catch obvious cases before spending an LLM call)
    rows = execution_result.get("rows", [])
    rowcount = execution_result.get("rowcount", 0)

    # Layer 3: LLM-based semantic sanity check — only run if layers 1-2 passed
    check: SanityCheck = llm.invoke([
        ("system", SANITY_PROMPT),
        ("human", f"User's request: {state['user_request']}\n\nQuery returned {rowcount} rows. Sample: {rows[:3]}"),
    ])

    if not check.passes_sanity_check:
        return {
            "verification_passed": False,
            "error_feedback": f"Result failed sanity check: {check.reason}",
        }

    return {"verification_passed": True, "error_feedback": None}