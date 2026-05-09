from typing import Any, Dict, List, Optional, TypedDict


class PSXAgentState(TypedDict, total=False):
    # Market event input
    symbol: str
    company: str
    sector: str
    event_date: str
    event_type: str
    trend: str

    # Price / trend data from PySpark later
    price: float
    volume: int
    moving_average: float
    confidence_hint: float

    # News Agent output
    retrieved_news: List[Dict[str, Any]]

    # Sentiment Agent output
    sentiment_label: str
    sentiment_score: float
    sentiment_confidence: float
    article_sentiments: List[Dict[str, Any]]

    # RAG Agent output
    rag_explanation: str

    # Future Decision Agent output
    decision: str
    confidence: float
    decision_reason: str

    # Debugging / explainability
    audit_log: List[Dict[str, Any]]
    error_message: Optional[str]
