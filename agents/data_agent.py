from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.state import PSXAgentState


def data_agent_node(state: PSXAgentState) -> PSXAgentState:
    """Week 2 placeholder. TODO Week 3: add live data enrichment."""

    state.setdefault("audit_log", [])
    return state
