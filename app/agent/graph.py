from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.planner import planner_node
from app.agent.codegen import codegen_node
from app.agent.risk_classifier import risk_classifier_node
from app.agent.sandbox_executor import run_sandboxed_query
from app.agent.verifier import verifier_node
from app.agent.critic import critic_node


def sandbox_executor_node(state: AgentState) -> dict:
    result = run_sandboxed_query(state["query_plan"]["sql"], state["risk_tier"])
    return {"execution_result": result}


def mark_success(state: AgentState) -> dict:
    return {"terminal_state": "SUCCESS"}


def route_by_risk(state: AgentState) -> str:
    return "execute" if state["risk_tier"] == "LOW" else "approval_pending"


def route_after_verification(state: AgentState) -> str:
    return "success" if state["verification_passed"] else "retry"


def route_after_critic(state: AgentState) -> str:
    return "give_up" if state.get("terminal_state") == "FAILED_MAX_RETRIES" else "retry_codegen"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("codegen", codegen_node)
    graph.add_node("risk_classifier", risk_classifier_node)
    graph.add_node("execute", sandbox_executor_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("critic", critic_node)
    graph.add_node("mark_success", mark_success)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "codegen")
    graph.add_edge("codegen", "risk_classifier")

    graph.add_conditional_edges(
        "risk_classifier",
        route_by_risk,
        {
            "execute": "execute",
            "approval_pending": END,  # still temporary — Week 3 builds the real approval gate
        },
    )

    graph.add_edge("execute", "verifier")

    graph.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "success": "mark_success",
            "retry": "critic",
        },
    )

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "retry_codegen": "codegen",
            "give_up": END,
        },
    )

    graph.add_edge("mark_success", END)

    return graph.compile()


sentinel_graph = build_graph()