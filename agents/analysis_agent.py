from agents.state import PSXAgentState


def analysis_agent_node(state: PSXAgentState) -> PSXAgentState:
    """Week 2 placeholder. TODO Week 3: add richer analytical reasoning."""

    state.setdefault("audit_log", [])
    return state
