from agents.state import PSXAgentState


def data_agent_node(state: PSXAgentState) -> PSXAgentState:
    """Week 2 placeholder. TODO Week 3: add live data enrichment."""

    state.setdefault("audit_log", [])
    return state
