"""
PSX Market Intelligence System - Main Entry Point
Run all agents together
"""
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all agents
from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.rag_agent_light import RAGAgent
from agents.decision_agent import DecisionAgent

def run_all_agents():
    """Run all agents in sequence"""
    print("="*60)
    print("PSX MARKET INTELLIGENCE - FULL PIPELINE")
    print("="*60)
    
    # Get query from user
    query = input("\n📊 Enter your query: ")
    
    # Create initial state
    state = {
        "messages": [],
        "query": query,
        "market_data": {},
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
    
    print("\n🔄 Processing your query...\n")
    
    # 1. Data Agent
    print("1️⃣ Data Agent: Fetching market data...")
    data_agent = DataAgent()
    state = data_agent.process(state)
    print(f"   ✓ {state['market_data'].get('symbol', 'Market summary')} retrieved\n")
    
    # 2. News Agent
    print("2️⃣ News Agent: Fetching latest news...")
    news_agent = NewsAgent()
    state = news_agent.process(state)
    print(f"   ✓ Found {len(state.get('news_data', []))} articles\n")
    
    # 3. Sentiment Agent
    print("3️⃣ Sentiment Agent: Analyzing sentiment...")
    sentiment_agent = SentimentAgent()
    state = sentiment_agent.process(state)
    sentiment = state.get('sentiment_analysis', {})
    print(f"   ✓ Sentiment: {sentiment.get('overall_sentiment', 'N/A')}\n")
    
    # 4. Analysis Agent
    print("4️⃣ Analysis Agent: Technical analysis...")
    analysis_agent = AnalysisAgent()
    state = analysis_agent.process(state)
    tech = state.get('technical_analysis', {})
    print(f"   ✓ RSI: {tech.get('rsi', 'N/A')} | Trend: {tech.get('trend', 'N/A')}\n")
    
    # 5. RAG Agent
    print("5️⃣ RAG Agent: Retrieving context...")
    rag_agent = RAGAgent()
    state = rag_agent.process(state)
    print(f"   ✓ Retrieved {len(state.get('rag_context', []))} documents\n")
    
    # 6. Decision Agent
    print("6️⃣ Decision Agent: Making recommendations...")
    decision_agent = DecisionAgent()
    state = decision_agent.process(state)
    
    # Display Results
    print("\n" + "="*60)
    print("📈 RESULTS")
    print("="*60)
    
    if state.get("market_data"):
        if "price" in state["market_data"]:
            print(f"\n💰 {state['market_data'].get('symbol', 'Stock')}: PKR {state['market_data'].get('price', 0)}")
            print(f"   Change: {state['market_data'].get('change_percent', 0)}%")
        else:
            indices = state['market_data'].get('indices', {})
            print(f"\n📊 KSE-100: {indices.get('KSE-100', {}).get('value', 'N/A')}")
    
    if state.get("recommendations"):
        print(f"\n🎯 RECOMMENDATIONS:")
        for i, rec in enumerate(state["recommendations"], 1):
            print(f"   {i}. {rec}")
    
    if state.get("confidence_score"):
        print(f"\n📊 Confidence: {state['confidence_score']*100:.1f}%")
    
    print("\n" + "="*60)

def main():
    """Main menu"""
    print("\n" + "="*60)
    print(" PSX MARKET INTELLIGENCE AGENTS")
    print("="*60)
    print("\n1. Run all agents (full pipeline)")
    print("2. Exit")
    
    choice = input("\nEnter choice (1-2): ")
    
    if choice == "1":
        run_all_agents()
    else:
        print("Goodbye!")

if __name__ == "__main__":
    main()
