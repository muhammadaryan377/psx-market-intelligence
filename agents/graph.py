"""Main LangGraph workflow for PSX intelligence system"""
from typing import Dict, Any, Literal, Optional, List
from langgraph.graph import StateGraph, END
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.state import AgentState
from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.rag_agent import RAGAgent
from agents.decision_agent import DecisionAgent

class PSXIntelligenceGraph:
    """Main orchestration graph for all agents"""
    
    def __init__(self):
        # Initialize all agents
        self.data_agent = DataAgent()
        self.news_agent = NewsAgent()
        self.sentiment_agent = SentimentAgent()
        self.analysis_agent = AnalysisAgent()
        self.rag_agent = RAGAgent()
        self.decision_agent = DecisionAgent()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the complete workflow graph"""
        workflow = StateGraph(AgentState)
        
        # Add all agent nodes
        workflow.add_node("data_collection", self.data_agent.process)
        workflow.add_node("news_fetching", self.news_agent.process)
        workflow.add_node("sentiment_analysis", self.sentiment_agent.process)
        workflow.add_node("technical_analysis", self.analysis_agent.process)
        workflow.add_node("rag_retrieval", self.rag_agent.process)
        workflow.add_node("decision_making", self.decision_agent.process)
        
        # Set entry point
        workflow.set_entry_point("data_collection")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "data_collection",
            self._after_data_collection,
            {
                "has_symbol": "news_fetching",
                "no_symbol": "decision_making"
            }
        )
        
        workflow.add_edge("news_fetching", "sentiment_analysis")
        workflow.add_edge("sentiment_analysis", "technical_analysis")
        workflow.add_edge("technical_analysis", "rag_retrieval")
        workflow.add_edge("rag_retrieval", "decision_making")
        workflow.add_edge("decision_making", END)
        
        return workflow.compile()
    
    def _after_data_collection(self, state: AgentState) -> Literal["has_symbol", "no_symbol"]:
        """Decide next step based on whether we have a symbol"""
        if state.get("market_data") and state["market_data"].get("symbol"):
            return "has_symbol"
        return "no_symbol"
    
    def run(self, query: str, symbol: str = None) -> Dict[str, Any]:
        """Run the complete agent pipeline"""
        initial_state = {
            "messages": [],
            "query": query,
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
            "completed": False
        }
        
        result = self.graph.invoke(initial_state)
        return result
"""Main LangGraph workflow for PSX intelligence system"""
from langgraph.graph import StateGraph, END
from typing import Literal
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.state import AgentState
from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.rag_agent import RAGAgent
from agents.decision_agent import DecisionAgent

class PSXIntelligenceGraph:
    """Main orchestration graph for all agents"""
    
    def __init__(self):
        # Initialize all agents
        self.data_agent = DataAgent()
        self.news_agent = NewsAgent()
        self.sentiment_agent = SentimentAgent()
        self.analysis_agent = AnalysisAgent()
        self.rag_agent = RAGAgent()
        self.decision_agent = DecisionAgent()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the complete workflow graph"""
        workflow = StateGraph(AgentState)
        
        # Add all agent nodes
        workflow.add_node("data_collection", self.data_agent.process)
        workflow.add_node("news_fetching", self.news_agent.process)
        workflow.add_node("sentiment_analysis", self.sentiment_agent.process)
        workflow.add_node("technical_analysis", self.analysis_agent.process)
        workflow.add_node("rag_retrieval", self.rag_agent.process)
        workflow.add_node("decision_making", self.decision_agent.process)
        
        # Set entry point
        workflow.set_entry_point("data_collection")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "data_collection",
            self._after_data_collection,
            {
                "has_symbol": "news_fetching",
                "no_symbol": "decision_making"
            }
        )
        
        workflow.add_edge("news_fetching", "sentiment_analysis")
        workflow.add_edge("sentiment_analysis", "technical_analysis")
        workflow.add_edge("technical_analysis", "rag_retrieval")
        workflow.add_edge("rag_retrieval", "decision_making")
        workflow.add_edge("decision_making", END)
        
        return workflow.compile()
    
    def _after_data_collection(self, state: AgentState) -> Literal["has_symbol", "no_symbol"]:
        """Decide next step based on whether we have a symbol"""
        if state.get("market_data") and state["market_data"].get("symbol"):
            return "has_symbol"
        return "no_symbol"
    
    def run(self, query: str, symbol: str = None) -> Dict[str, Any]:
        """Run the complete agent pipeline"""
        initial_state = {
            "messages": [],
            "query": query,
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
            "completed": False
        }
        
        result = self.graph.invoke(initial_state)
        return result