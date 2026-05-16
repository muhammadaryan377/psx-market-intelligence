"""
PSX Market Intelligence - Main Entry
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from agents.graph import get_graph

def main():
    print("="*60)
    print("PSX MARKET INTELLIGENCE - LangGraph Agent System")
    print("="*60)
    print("\n💡 Enter ANY PSX stock symbol")
    print("   Example: MCB, SYS, ENGRO, LUCK\n")
    
    query = input("📊 Enter symbol: ").strip()
    
    print("\n🔄 Running LangGraph workflow...\n")
    print("-" * 40)
    
    graph = get_graph()
    result = graph.run(query)
    
    print("\n" + "="*60)
    print("📈 FINAL RECOMMENDATION")
    print("="*60)
    
    for rec in result.get("recommendations", []):
        print(f"   {rec}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()