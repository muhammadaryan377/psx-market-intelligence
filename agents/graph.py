"""
LangGraph Workflow - Complete agent orchestration
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
import sys
from pathlib import Path

# Fix: Import MemorySaver from correct location
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    try:
        from langgraph.checkpoint import MemorySaver
    except ImportError:
        # If MemorySaver not available, define a simple version
        class MemorySaver:
            def __init__(self):
                self.checkpoints = {}
            
            def get(self, config):
                return self.checkpoints.get(config.get("configurable", {}).get("thread_id"))
            
            def put(self, config, state):
                thread_id = config.get("configurable", {}).get("thread_id")
                if thread_id:
                    self.checkpoints[thread_id] = state

sys.path.append(str(Path(__file__).parent.parent))

from agents.state import AgentState
from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.decision_agent import DecisionAgent

class PSXGraph:
    """LangGraph workflow for PSX agents"""
    
    def __init__(self):
        # Initialize agents
        self.data_agent = DataAgent()
        self.news_agent = NewsAgent()
        self.sentiment_agent = SentimentAgent()
        self.analysis_agent = AnalysisAgent()
        self.decision_agent = DecisionAgent()
        
        # Build graph
        self.app = self._build_graph()
        self.memory = MemorySaver()
    
    def _build_graph(self):
        """Build the workflow graph"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("data", lambda s: self.data_agent.process(s))
        workflow.add_node("news", lambda s: self.news_agent.process(s))
        workflow.add_node("sentiment", lambda s: self.sentiment_agent.process(s))
        workflow.add_node("analysis", lambda s: self.analysis_agent.process(s))
        workflow.add_node("decision", lambda s: self.decision_agent.process(s))
        
        # Set entry
        workflow.set_entry_point("data")
        
        # Add edges - simple linear flow
        workflow.add_edge("data", "news")
        workflow.add_edge("news", "sentiment")
        workflow.add_edge("sentiment", "analysis")
        workflow.add_edge("analysis", "decision")
        workflow.add_edge("decision", END)
        
        return workflow.compile()
    
    def run(self, query: str, symbol: str = None) -> Dict[str, Any]:
        """Run the workflow"""
        
        initial_state: AgentState = {
            "messages": [],
            "query": query,
            "user_id": None,
            "market_data": {"symbol": symbol} if symbol else {},
            "news_data": [],
            "historical_data": [],
            "technical_analysis": {},
            "sentiment_analysis": {},
            "rag_context": [],
            "risk_assessment": {},
            "recommendations": [],
            "confidence_score": 0.0,
            "current_step": "start",
            "next_agent": "",
            "errors": [],
            "completed": False,
            "iteration": 0
        }
        
        result = self.app.invoke(initial_state)
        return result

_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = PSXGraph()
    return _graph