"""RAG Agent - Retrieval Augmented Generation for PSX market intelligence"""
import os
import pickle
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass, asdict

# Try to import optional dependencies with fallbacks
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: faiss not installed. Install with: pip install faiss-cpu")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")

try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    print("Warning: newspaper3k not installed. Install with: pip install newspaper3k")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

# Local imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.state import AgentState

@dataclass
class Document:
    """Document structure for RAG"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class SimpleVectorStore:
    """Simple vector store for when FAISS is not available"""
    
    def __init__(self):
        self.documents = []
        self.embeddings = []
    
    def add_documents(self, documents: List[Document]):
        """Add documents to store"""
        for doc in documents:
            self.documents.append(doc)
            if doc.embedding is not None:
                self.embeddings.append(doc.embedding)
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[Document, float]]:
        """Simple cosine similarity search"""
        if not self.embeddings:
            return []
        
        # Compute similarities
        similarities = []
        for doc, emb in zip(self.documents, self.embeddings):
            # Cosine similarity
            similarity = np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            similarities.append((doc, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:min(k, len(similarities))]
    
    def save(self, path: str):
        """Save to disk"""
        with open(path, 'wb') as f:
            pickle.dump({'documents': self.documents, 'embeddings': self.embeddings}, f)
    
    def load(self, path: str):
        """Load from disk"""
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.embeddings = data['embeddings']
            return True
        return False

class RAGAgent:
    """RAG Agent for intelligent context retrieval"""
    
    def __init__(self):
        """Initialize RAG Agent with fallbacks"""
        print("🔧 Initializing RAG Agent...")
        
        # Initialize embedding model or use fallback
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
            print("✓ Using Sentence Transformers for embeddings")
        else:
            self.embedding_model = None
            self.embedding_dimension = 384
            print("⚠ Using simple embedding fallback")
        
        # Initialize vector store
        if FAISS_AVAILABLE:
            self.vector_store = self._create_faiss_store()
        else:
            self.vector_store = SimpleVectorStore()
            print("⚠ Using simple vector store (FAISS not available)")
        
        # Cache for query results
        self.query_cache = {}
        
        # Initialize knowledge base
        self._initialize_knowledge_base()
        
        print(f"✓ RAG Agent ready")
    
    def _create_faiss_store(self):
        """Create FAISS vector store"""
        from agents.rag_agent import VectorStore  # Import here to avoid circular import
        return VectorStore(dimension=self.embedding_dimension)
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with PSX data"""
        print("📚 Initializing knowledge base...")
        
        # Create documents from PSX knowledge base
        psx_docs = self._create_psx_documents()
        
        # Generate embeddings for documents
        documents_with_embeddings = []
        for doc in psx_docs:
            embedding = self._generate_embedding(doc.content)
            doc.embedding = embedding
            documents_with_embeddings.append(doc)
        
        # Add to vector store
        self.vector_store.add_documents(documents_with_embeddings)
        print(f"✓ Added {len(documents_with_embeddings)} documents to knowledge base")
    
    def _create_psx_documents(self) -> List[Document]:
        """Create documents from PSX knowledge base"""
        documents = []
        
        # PSX company data
        companies = {
            "SYS": {
                "name": "Systems Limited",
                "sector": "Technology",
                "description": "Leading IT services and software development company",
                "market_cap": "PKR 150B",
                "pe_ratio": 12.5,
                "eps": 45.2,
                "dividend_yield": 3.5
            },
            "ENGRO": {
                "name": "Engro Corporation",
                "sector": "Fertilizer/Chemicals",
                "description": "Diversified conglomerate",
                "market_cap": "PKR 200B",
                "pe_ratio": 8.2,
                "eps": 62.8,
                "dividend_yield": 5.2
            },
            "LUCK": {
                "name": "Lucky Cement",
                "sector": "Cement",
                "description": "Pakistan's largest cement manufacturer",
                "market_cap": "PKR 180B",
                "pe_ratio": 6.5,
                "eps": 85.3,
                "dividend_yield": 4.8
            }
        }
        
        # Create documents for each company
        for symbol, data in companies.items():
            content = f"""
            Company: {data['name']} ({symbol})
            Sector: {data['sector']}
            Description: {data['description']}
            Market Cap: {data['market_cap']}
            P/E Ratio: {data['pe_ratio']}
            EPS: PKR {data['eps']}
            Dividend Yield: {data['dividend_yield']}%
            """
            
            doc = Document(
                id=f"company_{symbol}",
                content=content.strip(),
                metadata={
                    "type": "company_fundamentals",
                    "symbol": symbol,
                    "company_name": data['name'],
                    "sector": data['sector']
                }
            )
            documents.append(doc)
        
        # Add market knowledge
        market_knowledge = [
            "PSX (Pakistan Stock Exchange) is the only stock exchange in Pakistan",
            "KSE-100 index tracks top 100 companies by market capitalization",
            "Market timings: Monday-Friday, 9:30 AM to 3:30 PM PKT"
        ]
        
        for i, knowledge in enumerate(market_knowledge):
            doc = Document(
                id=f"market_knowledge_{i}",
                content=knowledge,
                metadata={"type": "market_knowledge"}
            )
            documents.append(doc)
        
        return documents
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        if self.embedding_model:
            return self.embedding_model.encode(text, convert_to_numpy=True)
        else:
            # Simple fallback: use TF-IDF style hashing
            return self._simple_hash_embedding(text)
    
    def _simple_hash_embedding(self, text: str) -> np.ndarray:
        """Simple embedding fallback when sentence-transformers not available"""
        # Create a simple embedding based on character frequencies
        embedding = np.zeros(self.embedding_dimension)
        for i, char in enumerate(text[:1000]):
            idx = hash(char) % self.embedding_dimension
            embedding[idx] += 1
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding
    
    def retrieve_context(self, query: str, k: int = 5) -> Tuple[List[Document], List[float]]:
        """Retrieve relevant context for a query"""
        # Check cache
        cache_key = hashlib.md5(f"{query}_{k}".encode()).hexdigest()
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Search vector store
        results = self.vector_store.search(query_embedding, k)
        
        if not results:
            return [], []
        
        documents, scores = zip(*results) if results else ([], [])
        
        # Cache results
        self.query_cache[cache_key] = (list(documents), list(scores))
        
        return list(documents), list(scores)
    
    def get_relevant_financials(self, symbol: str) -> Dict[str, Any]:
        """Get relevant financial information for a symbol"""
        query = f"Financial information for {symbol}"
        documents, scores = self.retrieve_context(query, k=3)
        
        financials = {
            "symbol": symbol,
            "found": False,
            "metrics": {}
        }
        
        for doc, score in zip(documents, scores):
            if doc.metadata.get("type") == "company_fundamentals" and doc.metadata.get("symbol") == symbol:
                financials["found"] = True
                # Parse metrics from content
                content = doc.content
                if "Market Cap:" in content:
                    financials["metrics"]["market_cap"] = content.split("Market Cap:")[-1].split("\n")[0].strip()
                if "P/E Ratio:" in content:
                    financials["metrics"]["pe_ratio"] = float(content.split("P/E Ratio:")[-1].split("\n")[0].strip())
                if "EPS:" in content:
                    financials["metrics"]["eps"] = float(content.split("EPS: PKR")[-1].split("\n")[0].strip())
                if "Dividend Yield:" in content:
                    financials["metrics"]["dividend_yield"] = float(content.split("Dividend Yield:")[-1].split("%")[0].strip())
                break
        
        return financials
    
    def process(self, state: AgentState) -> AgentState:
        """Process state through RAG agent"""
        print("🔍 RAG Agent: Retrieving relevant context...")
        
        query = state.get("query", "")
        symbol = state.get("market_data", {}).get("symbol", "")
        
        # Build search query
        if symbol:
            search_query = f"{query} about {symbol}"
        else:
            search_query = query
        
        # Retrieve relevant context
        documents, scores = self.retrieve_context(search_query, k=5)
        
        # Format context for response
        context_list = []
        for doc, score in zip(documents, scores):
            context_list.append({
                "content": doc.content[:300],
                "relevance": float(score),
                "source": doc.metadata.get("type", "unknown"),
                "symbol": doc.metadata.get("symbol", "")
            })
        
        # Get financials if symbol provided
        financial_context = {}
        if symbol:
            financial_context = self.get_relevant_financials(symbol)
        
        # Update state
        state["rag_context"] = context_list
        state["rag_financials"] = financial_context
        state["current_step"] = "rag_complete"
        
        print(f"✓ Retrieved {len(documents)} relevant documents")
        return state

# Test function
def test_rag_agent():
    """Test the RAG agent"""
    print("\n" + "="*60)
    print("Testing RAG Agent")
    print("="*60)
    
    rag = RAGAgent()
    
    # Test queries
    test_queries = [
        "What is Systems Limited?",
        "Tell me about ENGRO",
        "PSX market information"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        docs, scores = rag.retrieve_context(query, k=2)
        for doc, score in zip(docs, scores):
            print(f"   Score: {score:.3f} - {doc.content[:100]}...")

if __name__ == "__main__":
    test_rag_agent()
"""RAG Agent - Retrieval Augmented Generation for PSX market intelligence"""
import os
import pickle
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, asdict

# Vector store and embeddings
import faiss
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel

# Document processing
from newspaper import Article
import requests
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import urlparse

# Local imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.state import AgentState

@dataclass
class Document:
    """Document structure for RAG"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class VectorStore:
    """FAISS vector store for document embeddings"""
    
    def __init__(self, dimension: int = 384, index_path: str = "vector_store/psx_index.faiss"):
        self.dimension = dimension
        self.index_path = index_path
        self.index = None
        self.documents = []  # Store document metadata
        self.id_to_index = {}  # Map document ID to index position
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        # Load existing index or create new one
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create a new one"""
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                # Load metadata
                metadata_path = self.index_path.replace('.faiss', '_metadata.pkl')
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'rb') as f:
                        metadata = pickle.load(f)
                        self.documents = metadata.get('documents', [])
                        self.id_to_index = metadata.get('id_to_index', {})
                print(f"✓ Loaded existing vector store with {len(self.documents)} documents")
            except Exception as e:
                print(f"⚠ Failed to load index: {e}, creating new one")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        self.index = faiss.IndexFlatL2(self.dimension)  # L2 distance for similarity
        self.documents = []
        self.id_to_index = {}
        print("✓ Created new vector store")
    
    def add_documents(self, documents: List[Document]):
        """Add documents to the vector store"""
        if not documents:
            return
        
        # Extract embeddings
        embeddings = []
        for doc in documents:
            if doc.embedding is not None:
                embeddings.append(doc.embedding)
                # Store metadata
                doc_id = doc.id
                if doc_id not in self.id_to_index:
                    self.id_to_index[doc_id] = len(self.documents)
                    self.documents.append({
                        'id': doc_id,
                        'content': doc.content,
                        'metadata': doc.metadata,
                        'timestamp': doc.timestamp
                    })
        
        if embeddings:
            embeddings_array = np.vstack(embeddings).astype('float32')
            self.index.add(embeddings_array)
            self._save()
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[Document, float]]:
        """Search for similar documents"""
        if self.index.ntotal == 0:
            return []
        
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.documents):
                doc_meta = self.documents[idx]
                doc = Document(
                    id=doc_meta['id'],
                    content=doc_meta['content'],
                    metadata=doc_meta['metadata'],
                    timestamp=doc_meta['timestamp']
                )
                # Convert distance to similarity score (lower distance = higher similarity)
                similarity = 1 / (1 + distances[0][i])
                results.append((doc, similarity))
        
        return results
    
    def _save(self):
        """Save index and metadata to disk"""
        if self.index is not None and self.index.ntotal > 0:
            faiss.write_index(self.index, self.index_path)
            metadata_path = self.index_path.replace('.faiss', '_metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'id_to_index': self.id_to_index
                }, f)

class DocumentProcessor:
    """Process documents for RAG ingestion"""
    
    def __init__(self):
        self.psx_knowledge_base = {
            "companies": {
                "SYS": {
                    "name": "Systems Limited",
                    "sector": "Technology",
                    "description": "Leading IT services and software development company in Pakistan",
                    "fundamentals": {
                        "market_cap": "PKR 150B",
                        "pe_ratio": 12.5,
                        "eps": 45.2,
                        "dividend_yield": 3.5
                    }
                },
                "ENGRO": {
                    "name": "Engro Corporation",
                    "sector": "Fertilizer/Chemicals",
                    "description": "Diversified conglomerate with interests in fertilizers, foods, and energy",
                    "fundamentals": {
                        "market_cap": "PKR 200B",
                        "pe_ratio": 8.2,
                        "eps": 62.8,
                        "dividend_yield": 5.2
                    }
                },
                "LUCK": {
                    "name": "Lucky Cement",
                    "sector": "Cement",
                    "description": "Pakistan's largest cement manufacturer with global presence",
                    "fundamentals": {
                        "market_cap": "PKR 180B",
                        "pe_ratio": 6.5,
                        "eps": 85.3,
                        "dividend_yield": 4.8
                    }
                },
                "HUBC": {
                    "name": "Hub Power Company",
                    "sector": "Power Generation",
                    "description": "Pakistan's largest private power producer",
                    "fundamentals": {
                        "market_cap": "PKR 120B",
                        "pe_ratio": 4.2,
                        "eps": 28.5,
                        "dividend_yield": 9.5
                    }
                },
                "FCCL": {
                    "name": "Fauji Cement Company",
                    "sector": "Cement",
                    "description": "Major cement manufacturer in northern Pakistan",
                    "fundamentals": {
                        "market_cap": "PKR 45B",
                        "pe_ratio": 5.8,
                        "eps": 12.3,
                        "dividend_yield": 6.0
                    }
                }
            },
            "market_knowledge": [
                "PSX (Pakistan Stock Exchange) is the only stock exchange in Pakistan",
                "KSE-100 index tracks top 100 companies by market capitalization",
                "Market timings: Monday-Friday, 9:30 AM to 3:30 PM PKT",
                "Key sectors: Banking, Cement, Fertilizer, Oil & Gas, Technology, Power"
            ],
            "trading_rules": [
                "PSX has a circuit breaker mechanism - 5% for individual stocks",
                "Settlement is T+2 (trade date plus 2 days)",
                "CDC handles central depository services",
                "Investors need a CDC account to trade shares"
            ]
        }
    
    def create_documents_from_psx_data(self) -> List[Document]:
        """Create documents from PSX knowledge base"""
        documents = []
        
        # Create documents for each company
        for symbol, data in self.psx_knowledge_base["companies"].items():
            content = f"""
            Company: {data['name']} ({symbol})
            Sector: {data['sector']}
            Description: {data['description']}
            
            Financial Metrics:
            - Market Cap: {data['fundamentals']['market_cap']}
            - P/E Ratio: {data['fundamentals']['pe_ratio']}
            - EPS: PKR {data['fundamentals']['eps']}
            - Dividend Yield: {data['fundamentals']['dividend_yield']}%
            """
            
            doc = Document(
                id=f"company_{symbol}",
                content=content.strip(),
                metadata={
                    "type": "company_fundamentals",
                    "symbol": symbol,
                    "company_name": data['name'],
                    "sector": data['sector']
                }
            )
            documents.append(doc)
        
        # Create documents for market knowledge
        for i, knowledge in enumerate(self.psx_knowledge_base["market_knowledge"]):
            doc = Document(
                id=f"market_knowledge_{i}",
                content=knowledge,
                metadata={"type": "market_knowledge", "category": "general"}
            )
            documents.append(doc)
        
        # Create documents for trading rules
        for i, rule in enumerate(self.psx_knowledge_base["trading_rules"]):
            doc = Document(
                id=f"trading_rule_{i}",
                content=rule,
                metadata={"type": "trading_rule", "category": "regulation"}
            )
            documents.append(doc)
        
        return documents
    
    def create_document_from_article(self, url: str) -> Optional[Document]:
        """Extract and create document from news article"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            doc = Document(
                id=hashlib.md5(url.encode()).hexdigest(),
                content=article.text[:2000],  # Limit length
                metadata={
                    "type": "news_article",
                    "url": url,
                    "title": article.title,
                    "authors": article.authors,
                    "publish_date": str(article.publish_date) if article.publish_date else None,
                    "source": urlparse(url).netloc
                }
            )
            return doc
        except Exception as e:
            print(f"Failed to process article {url}: {e}")
            return None

class RAGAgent:
    """RAG Agent for intelligent context retrieval"""
    
    def __init__(self, use_gpu: bool = False, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize RAG Agent
        
        Args:
            use_gpu: Whether to use GPU for FAISS (default: False)
            embedding_model: Sentence transformer model name
        """
        print("🔧 Initializing RAG Agent...")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        # Initialize vector store
        self.vector_store = VectorStore(dimension=self.embedding_dimension)
        
        # Initialize document processor
        self.doc_processor = DocumentProcessor()
        
        # Cache for query results
        self.query_cache = {}
        
        # Load or create initial documents
        self._initialize_knowledge_base()
        
        print(f"✓ RAG Agent ready (embedding dimension: {self.embedding_dimension})")
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with PSX data"""
        print("📚 Initializing knowledge base...")
        
        # Create documents from PSX knowledge base
        psx_docs = self.doc_processor.create_documents_from_psx_data()
        
        # Generate embeddings for documents
        documents_with_embeddings = []
        for doc in psx_docs:
            embedding = self._generate_embedding(doc.content)
            doc.embedding = embedding
            documents_with_embeddings.append(doc)
        
        # Add to vector store
        self.vector_store.add_documents(documents_with_embeddings)
        print(f"✓ Added {len(documents_with_embeddings)} documents to knowledge base")
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        return self.embedding_model.encode(text, convert_to_numpy=True)
    
    def add_news_article(self, url: str) -> bool:
        """Add a news article to the knowledge base"""
        doc = self.doc_processor.create_document_from_article(url)
        if doc:
            doc.embedding = self._generate_embedding(doc.content)
            self.vector_store.add_documents([doc])
            return True
        return False
    
    def add_text_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add a text document to the knowledge base"""
        doc_id = hashlib.md5(content.encode()).hexdigest()
        doc = Document(
            id=doc_id,
            content=content,
            metadata=metadata
        )
        doc.embedding = self._generate_embedding(content)
        self.vector_store.add_documents([doc])
        return doc_id
    
    def retrieve_context(self, query: str, k: int = 5, use_cache: bool = True) -> Tuple[List[Document], List[float]]:
        """
        Retrieve relevant context for a query
        
        Args:
            query: User query
            k: Number of documents to retrieve
            use_cache: Whether to use cached results
        
        Returns:
            Tuple of (documents, similarity_scores)
        """
        # Check cache
        cache_key = hashlib.md5(f"{query}_{k}".encode()).hexdigest()
        if use_cache and cache_key in self.query_cache:
            cached_result = self.query_cache[cache_key]
            print(f"✓ Returning cached result for query")
            return cached_result
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Search vector store
        results = self.vector_store.search(query_embedding, k)
        
        if not results:
            return [], []
        
        documents, scores = zip(*results) if results else ([], [])
        
        # Cache results
        if use_cache:
            self.query_cache[cache_key] = (list(documents), list(scores))
        
        return list(documents), list(scores)
    
    def enhance_query(self, original_query: str, context: List[Document]) -> str:
        """Enhance query with retrieved context"""
        if not context:
            return original_query
        
        # Extract relevant information from context
        context_text = "\n\n".join([doc.content[:500] for doc in context[:3]])
        
        enhanced_query = f"""
        Context Information:
        {context_text}
        
        User Question: {original_query}
        
        Please answer based on the above context and your knowledge of Pakistan Stock Exchange.
        """
        
        return enhanced_query
    
    def get_relevant_financials(self, symbol: str) -> Dict[str, Any]:
        """Get relevant financial information for a specific symbol"""
        query = f"Financial information for {symbol} including market cap, P/E ratio, EPS, and dividend yield"
        documents, scores = self.retrieve_context(query, k=3)
        
        financials = {
            "symbol": symbol,
            "found": False,
            "metrics": {},
            "source_documents": []
        }
        
        for doc, score in zip(documents, scores):
            if doc.metadata.get("type") == "company_fundamentals" and doc.metadata.get("symbol") == symbol:
                financials["found"] = True
                # Parse content for financial metrics
                content = doc.content
                financials["metrics"] = self._parse_financial_metrics(content)
                financials["relevance_score"] = score
                break
        
        return financials
    
    def _parse_financial_metrics(self, content: str) -> Dict[str, Any]:
        """Parse financial metrics from document content"""
        metrics = {}
        
        lines = content.split('\n')
        for line in lines:
            if 'Market Cap:' in line:
                metrics['market_cap'] = line.split('Market Cap:')[-1].strip()
            elif 'P/E Ratio:' in line:
                metrics['pe_ratio'] = float(line.split('P/E Ratio:')[-1].strip())
            elif 'EPS:' in line:
                metrics['eps'] = float(line.split('EPS: PKR')[-1].strip())
            elif 'Dividend Yield:' in line:
                metrics['dividend_yield'] = float(line.split('Dividend Yield:')[-1].strip('%'))
        
        return metrics
    
    def process(self, state: AgentState) -> AgentState:
        """
        Process state through RAG agent - main entry point for LangGraph
        
        Args:
            state: Current agent state
        
        Returns:
            Updated agent state with RAG context
        """
        print("🔍 RAG Agent: Retrieving relevant context...")
        
        query = state.get("query", "")
        symbol = state.get("market_data", {}).get("symbol", "")
        
        # Build enhanced query
        if symbol:
            search_query = f"{query} about {symbol} in Pakistan Stock Exchange"
        else:
            search_query = query
        
        # Retrieve relevant context
        documents, scores = self.retrieve_context(search_query, k=5)
        
        # Format context for response
        context_list = []
        for doc, score in zip(documents, scores):
            context_list.append({
                "content": doc.content[:500],  # Truncate for display
                "relevance": score,
                "source": doc.metadata.get("type", "unknown"),
                "symbol": doc.metadata.get("symbol", ""),
                "company": doc.metadata.get("company_name", "")
            })
        
        # Get specific financials if symbol provided
        financial_context = {}
        if symbol:
            financial_context = self.get_relevant_financials(symbol)
        
        # Update state
        state["rag_context"] = context_list
        state["rag_financials"] = financial_context
        
        # Enhanced query for next agents
        if context_list:
            enhanced = self.enhance_query(query, documents)
            state["enhanced_query"] = enhanced
        
        state["messages"].append({
            "agent": "RAGAgent",
            "content": f"Retrieved {len(documents)} relevant documents (avg relevance: {np.mean(scores) if scores else 0:.2f})",
            "timestamp": datetime.now().isoformat(),
            "context_summary": [c["source"] for c in context_list[:3]]
        })
        
        state["current_step"] = "rag_complete"
        
        print(f"✓ Retrieved {len(documents)} documents with relevance scores")
        return state
    
    def get_similar_companies(self, symbol: str, k: int = 3) -> List[Dict[str, Any]]:
        """Get similar companies based on sector and fundamentals"""
        # First get the company's sector
        financials = self.get_relevant_financials(symbol)
        sector = financials.get("metrics", {}).get("sector", "")
        
        if not sector:
            return []
        
        # Search for companies in same sector
        query = f"Companies in {sector} sector with financial metrics"
        documents, scores = self.retrieve_context(query, k=k+1)  # +1 to exclude current
        
        similar = []
        for doc, score in zip(documents, scores):
            if doc.metadata.get("symbol") != symbol:
                similar.append({
                    "symbol": doc.metadata.get("symbol", "Unknown"),
                    "company": doc.metadata.get("company_name", "Unknown"),
                    "relevance": score,
                    "financials": self._parse_financial_metrics(doc.content)
                })
        
        return similar[:k]
    
    def clear_cache(self):
        """Clear query cache"""
        self.query_cache.clear()
        print("✓ Query cache cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        return {
            "total_documents": len(self.vector_store.documents),
            "index_size": self.vector_store.index.ntotal if self.vector_store.index else 0,
            "cache_size": len(self.query_cache),
            "embedding_model": self.embedding_model._module_name if hasattr(self.embedding_model, '_module_name') else "unknown"
        }

# Standalone test function
def test_rag_agent():
    """Test the RAG agent functionality"""
    print("\n" + "="*60)
    print("Testing RAG Agent")
    print("="*60)
    
    # Initialize agent
    rag = RAGAgent()
    
    # Test queries
    test_queries = [
        "What is the market cap of Systems Limited?",
        "Tell me about ENGRO's financial performance",
        "What are the trading rules in PSX?",
        "Compare LUCK and FCCL fundamentals",
        "What is the dividend yield of Hub Power Company?"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        documents, scores = rag.retrieve_context(query, k=3)
        
        print(f"   Retrieved {len(documents)} documents:")
        for i, (doc, score) in enumerate(zip(documents, scores), 1):
            print(f"   {i}. {doc.metadata.get('type', 'unknown')} (score: {score:.3f})")
            print(f"      {doc.content[:100]}...")
    
    # Test financial lookup
    print("\n" + "="*60)
    print("Financial Lookup Test")
    print("="*60)
    
    for symbol in ["SYS", "ENGRO", "LUCK"]:
        financials = rag.get_relevant_financials(symbol)
        if financials["found"]:
            print(f"\n{symbol}: {financials['metrics']}")
        else:
            print(f"\n{symbol}: Not found in knowledge base")
    
    # Get statistics
    print("\n" + "="*60)
    print("RAG System Statistics")
    print("="*60)
    stats = rag.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    test_rag_agent()