"""
Lightweight RAG Agent - No heavy dependencies
Uses simple keyword matching and a local knowledge base
"""

from datetime import datetime
import re
from typing import List, Dict, Any

class RAGAgent:
    """Lightweight RAG agent that doesn't require heavy ML libraries"""
    
    def __init__(self):
        # Local knowledge base for PSX
        self.knowledge_base = {
            "companies": {
                "SYS": {
                    "name": "Systems Limited",
                    "sector": "Technology",
                    "description": "Pakistan's leading IT services and software development company",
                    "market_cap": "PKR 150 Billion",
                    "pe_ratio": "12.5",
                    "eps": "PKR 45.2",
                    "dividend_yield": "3.5%"
                },
                "ENGRO": {
                    "name": "Engro Corporation",
                    "sector": "Fertilizer/Chemicals",
                    "description": "Diversified conglomerate with interests in fertilizers, foods, and energy",
                    "market_cap": "PKR 200 Billion",
                    "pe_ratio": "8.2",
                    "eps": "PKR 62.8",
                    "dividend_yield": "5.2%"
                },
                "LUCK": {
                    "name": "Lucky Cement",
                    "sector": "Cement",
                    "description": "Pakistan's largest cement manufacturer with global presence",
                    "market_cap": "PKR 180 Billion",
                    "pe_ratio": "6.5",
                    "eps": "PKR 85.3",
                    "dividend_yield": "4.8%"
                },
                "HUBC": {
                    "name": "Hub Power Company",
                    "sector": "Power Generation",
                    "description": "Pakistan's largest private power producer",
                    "market_cap": "PKR 120 Billion",
                    "pe_ratio": "4.2",
                    "eps": "PKR 28.5",
                    "dividend_yield": "9.5%"
                },
                "FCCL": {
                    "name": "Fauji Cement Company",
                    "sector": "Cement",
                    "description": "Major cement manufacturer in northern Pakistan",
                    "market_cap": "PKR 45 Billion",
                    "pe_ratio": "5.8",
                    "eps": "PKR 12.3",
                    "dividend_yield": "6.0%"
                },
                "MCB": {
                    "name": "MCB Bank",
                    "sector": "Banking",
                    "description": "One of Pakistan's largest private banks",
                    "market_cap": "PKR 110 Billion",
                    "pe_ratio": "7.2",
                    "eps": "PKR 35.8",
                    "dividend_yield": "8.0%"
                }
            },
            "general": [
                "PSX (Pakistan Stock Exchange) is the only stock exchange in Pakistan",
                "KSE-100 index tracks the top 100 companies by market capitalization",
                "Market timings: Monday-Friday, 9:30 AM to 3:30 PM PKT",
                "Key sectors: Banking, Cement, Fertilizer, Oil & Gas, Technology, Power",
                "PSX has a circuit breaker mechanism - 5% for individual stocks",
                "Settlement is T+2 (trade date plus 2 days)"
            ]
        }
        
        # Cache for results
        self.cache = {}
        
        print("✓ Lightweight RAG Agent initialized (no ML models needed)")
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state and retrieve relevant context"""
        print("🔍 RAG Agent: Retrieving context (lightweight mode)...")
        
        query = state.get("query", "").lower()
        symbol = state.get("market_data", {}).get("symbol", "")
        
        if symbol:
            symbol = symbol.upper()
        
        context = []
        
        # Search for company information
        if symbol and symbol in self.knowledge_base["companies"]:
            company = self.knowledge_base["companies"][symbol]
            context.append({
                "type": "company_info",
                "content": f"{company['name']} ({symbol}) - {company['sector']} sector. {company['description']}",
                "relevance": 0.95,
                "metadata": company
            })
            
            # Add financials
            context.append({
                "type": "financials",
                "content": f"Market Cap: {company['market_cap']}, P/E Ratio: {company['pe_ratio']}, EPS: {company['eps']}, Dividend Yield: {company['dividend_yield']}",
                "relevance": 0.9,
                "metadata": {"symbol": symbol}
            })
        
        # Search for company by name in query
        if not symbol:
            for sym, info in self.knowledge_base["companies"].items():
                if info["name"].lower() in query:
                    context.append({
                        "type": "company_info",
                        "content": f"{info['name']} ({sym}) - {info['sector']} sector. {info['description']}",
                        "relevance": 0.85,
                        "metadata": {"symbol": sym, "name": info["name"]}
                    })
                    break
        
        # Add general market knowledge based on keywords
        general_context = self._get_general_context(query)
        context.extend(general_context)
        
        # If no specific context found, add general info
        if not context:
            context.append({
                "type": "general",
                "content": "PSX (Pakistan Stock Exchange) is the stock market of Pakistan. Please ask about specific stocks like SYS, ENGRO, LUCK, HUBC, FCCL, or MCB.",
                "relevance": 0.5
            })
        
        # Limit to top 5 most relevant
        context.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        state["rag_context"] = context[:5]
        state["current_step"] = "rag_complete"
        
        print(f"   ✓ Retrieved {len(state['rag_context'])} relevant documents")
        return state
    
    def _get_general_context(self, query: str) -> List[Dict]:
        """Get general context based on keywords in query"""
        context = []
        query_lower = query.lower()
        
        # Keyword mapping to relevant knowledge
        keywords = {
            "market": ["KSE-100", "PSX", "trading", "market timings"],
            "index": ["KSE-100 index", "top companies", "market capitalization"],
            "sector": ["banking", "cement", "fertilizer", "technology", "oil", "gas", "power"],
            "trading": ["circuit breaker", "settlement", "T+2", "trading hours"],
            "psx": ["Pakistan Stock Exchange", "only stock exchange in Pakistan"]
        }
        
        matched_topics = set()
        for topic, words in keywords.items():
            for word in words:
                if word.lower() in query_lower:
                    matched_topics.add(topic)
                    break
        
        # Add relevant general knowledge
        for topic in matched_topics:
            if topic == "market":
                context.append({
                    "type": "market_info",
                    "content": self.knowledge_base["general"][0] + " " + self.knowledge_base["general"][1],
                    "relevance": 0.7
                })
            elif topic == "index":
                context.append({
                    "type": "index_info",
                    "content": self.knowledge_base["general"][1],
                    "relevance": 0.7
                })
            elif topic == "trading":
                context.append({
                    "type": "trading_info",
                    "content": self.knowledge_base["general"][3] + " " + self.knowledge_base["general"][4] + " " + self.knowledge_base["general"][5],
                    "relevance": 0.7
                })
        
        return context
    
    def get_company_info(self, symbol: str) -> Dict:
        """Get company information by symbol"""
        symbol = symbol.upper()
        if symbol in self.knowledge_base["companies"]:
            return self.knowledge_base["companies"][symbol]
        return None
    
    def search_companies(self, query: str) -> List[Dict]:
        """Search for companies by name or sector"""
        query_lower = query.lower()
        results = []
        
        for symbol, info in self.knowledge_base["companies"].items():
            if (query_lower in info["name"].lower() or 
                query_lower in info["sector"].lower() or
                query_lower in symbol.lower()):
                results.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "sector": info["sector"],
                    "description": info["description"]
                })
        
        return results
    
    def get_sector_info(self, sector: str) -> List[Dict]:
        """Get all companies in a sector"""
        sector_lower = sector.lower()
        results = []
        
        for symbol, info in self.knowledge_base["companies"].items():
            if info["sector"].lower() in sector_lower or sector_lower in info["sector"].lower():
                results.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "market_cap": info["market_cap"]
                })
        
        return results


# Test function
if __name__ == "__main__":
    print("Testing Lightweight RAG Agent...")
    agent = RAGAgent()
    
    # Test with a query
    test_state = {
        "query": "Tell me about SYS stock",
        "market_data": {"symbol": "SYS"},
        "messages": [],
        "current_step": ""
    }
    
    result = agent.process(test_state)
    
    print("\nRetrieved Context:")
    for i, ctx in enumerate(result.get("rag_context", []), 1):
        print(f"\n{i}. [{ctx['type']}] (relevance: {ctx['relevance']})")
        print(f"   {ctx['content'][:150]}...")
    
    print("\n✓ Lightweight RAG Agent working without heavy dependencies!")