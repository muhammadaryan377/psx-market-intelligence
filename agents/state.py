"""State definitions for LangGraph workflow"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator
from datetime import datetime


class MarketData(TypedDict):
    """Market data structure"""
    symbol: Optional[str]
    price: Optional[float]
    volume: Optional[int]
    change: Optional[float]
    timestamp: Optional[str]
    indicators: Optional[Dict[str, Any]]

class NewsItem(TypedDict):
    """News item structure"""
    title: str
    summary: str
    url: Optional[str]
    source: str
    date: str
    relevance: float
    sentiment: Optional[float]

class AgentState(TypedDict):
    """Main state object that flows through the graph"""
    # Messages and query
    news_signal: Optional[Dict[str, Any]]
    messages: Annotated[List[Dict[str, Any]], operator.add]
    query: str
    user_id: Optional[str]
    
    # Data collection
    market_data: Optional[MarketData]
    news_data: Optional[List[NewsItem]]
    historical_data: Optional[List[Dict]]
    
    # Analysis results
    technical_analysis: Optional[Dict[str, Any]]
    sentiment_analysis: Optional[Dict[str, Any]]
    rag_context: Optional[List[Dict]]
    
    # Decision making
    risk_assessment: Optional[Dict[str, Any]]
    recommendations: Optional[List[str]]
    confidence_score: Optional[float]
    
    # Workflow control
    current_step: str
    next_agent: str
    errors: List[str]
    completed: bool
    
    # NEW: For deterministic runs (backtesting / consistent behavior)
    simulation_date: Optional[datetime]   # ← ye line add karo