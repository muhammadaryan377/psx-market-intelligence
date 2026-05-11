import json
import os
import pickle
import re
from typing import Any, Dict, List, Optional

from config.app_config import VECTOR_INDEX_DIR
from rag_layer.news_loader import load_news

os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")

try:
    import faiss
except ImportError as exc:  # pragma: no cover
    faiss = None
    FAISS_IMPORT_ERROR = str(exc)
else:
    FAISS_IMPORT_ERROR = ""

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover
    np = None
    NUMPY_IMPORT_ERROR = str(exc)
else:
    NUMPY_IMPORT_ERROR = ""

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:  # pragma: no cover
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_IMPORT_ERROR = str(exc)
else:
    SENTENCE_TRANSFORMERS_IMPORT_ERROR = ""

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
ALLOW_MODEL_DOWNLOADS_ENV = "PSX_ALLOW_MODEL_DOWNLOADS"

INDEX_DIR = VECTOR_INDEX_DIR
INDEX_FILE = INDEX_DIR / "news_index.faiss"
TFIDF_INDEX_FILE = INDEX_DIR / "tfidf_index.pkl"
METADATA_FILE = INDEX_DIR / "news_metadata.json"

LOW_QUALITY_TITLES = {"untitled", "notice"}
MIN_ARTICLE_OR_SUMMARY_LENGTH = 150
MIN_PSX_ANNOUNCEMENT_ARTICLE_LENGTH = 300
MARKET_WIDE_TERMS = (
    "psx",
    "kse-100",
    "kse100",
    "kse 100",
    "pakistan stock exchange",
    "benchmark index",
    "stock market",
    "bulls",
    "bears",
    "shares",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _allow_model_downloads() -> bool:
    value = os.getenv(ALLOW_MODEL_DOWNLOADS_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _set_huggingface_offline_mode() -> None:
    os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _vector_search_available() -> bool:
    return faiss is not None and np is not None and SentenceTransformer is not None


def _query_terms(query: str) -> List[str]:
    stop_terms = {
        "and",
        "are",
        "company",
        "event",
        "find",
        "for",
        "from",
        "market",
        "movement",
        "news",
        "pakistan",
        "stock",
        "the",
        "type",
        "with",
    }
    terms = [
        term
        for term in re.findall(r"[a-z0-9-]+", str(query).lower())
        if len(term) >= 3 and term not in stop_terms
    ]

    return list(dict.fromkeys(terms))


def is_low_quality_news(item):
    title = _clean_text(item.get("title"))
    title_lower = title.lower()
    article_text = _clean_text(item.get("article_text"))
    summary = _clean_text(item.get("summary"))
    source = _clean_text(item.get("source")).lower()

    if not title:
        return True

    if title_lower in LOW_QUALITY_TITLES:
        return True

    if "pitch deck presentation" in title_lower:
        return True

    if (
        len(article_text) < MIN_ARTICLE_OR_SUMMARY_LENGTH
        and len(summary) < MIN_ARTICLE_OR_SUMMARY_LENGTH
    ):
        return True

    if (
        source == "psx announcements"
        and len(article_text) < MIN_PSX_ANNOUNCEMENT_ARTICLE_LENGTH
    ):
        return True

    return False


def _contains_query_term(text: str, term: Optional[str]) -> bool:
    term = _clean_text(term)

    if not term:
        return False

    if len(term) <= 8 and term.replace("-", "").isalnum():
        pattern = rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    return term.lower() in text.lower()


def _symbol_or_company_match_counts(
    text: str,
    query_symbol: Optional[str],
    query_company: Optional[str],
) -> tuple[int, int]:
    query_symbol = _clean_text(query_symbol).upper()
    query_company = _clean_text(query_company)
    symbol_count = 0
    company_count = 0

    if query_symbol:
        symbol_pattern = rf"(?<![A-Za-z0-9]){re.escape(query_symbol)}(?![A-Za-z0-9])"
        symbol_count = len(re.findall(symbol_pattern, text, flags=re.IGNORECASE))

    if query_company:
        company_pattern = re.escape(query_company)
        company_count = len(re.findall(company_pattern, text, flags=re.IGNORECASE))

    return symbol_count, company_count


def _has_symbol_or_company_match(
    text: str,
    query_symbol: Optional[str],
    query_company: Optional[str],
) -> bool:
    symbol_count, company_count = _symbol_or_company_match_counts(
        text=text,
        query_symbol=query_symbol,
        query_company=query_company,
    )

    return symbol_count > 0 or company_count > 0


def _has_strong_symbol_or_company_match(
    item: Dict[str, Any],
    query_symbol: Optional[str],
    query_company: Optional[str],
) -> bool:
    title = _clean_text(item.get("title"))
    article_text = _clean_text(item.get("article_text"))

    if _has_symbol_or_company_match(title, query_symbol, query_company):
        return True

    symbol_count, company_count = _symbol_or_company_match_counts(
        text=article_text,
        query_symbol=query_symbol,
        query_company=query_company,
    )

    return symbol_count >= 2 or company_count >= 2


def _has_market_wide_terms(text: str) -> bool:
    text_lower = text.lower()

    return any(term in text_lower for term in MARKET_WIDE_TERMS)


def _calculate_relevance_bonus(
    item: Dict[str, Any],
    query_symbol: Optional[str] = None,
    query_sector: Optional[str] = None,
    query_company: Optional[str] = None,
) -> float:
    title = _clean_text(item.get("title"))
    article_text = _clean_text(item.get("article_text"))
    combined_text = f"{title} {article_text}"
    combined_lower = combined_text.lower()

    item_symbol = _clean_text(item.get("symbol")).upper()
    item_sector = _clean_text(item.get("sector")).lower()
    item_news_type = _clean_text(item.get("news_type")).lower()

    query_symbol = _clean_text(query_symbol).upper()
    query_sector = _clean_text(query_sector).lower()
    query_company = _clean_text(query_company)
    has_symbol_or_company_match = _has_symbol_or_company_match(
        text=combined_text,
        query_symbol=query_symbol,
        query_company=query_company,
    )

    relevance_bonus = 0.0

    if query_symbol and _contains_query_term(combined_text, query_symbol):
        relevance_bonus += 0.20

    if query_company and query_company.lower() in combined_lower:
        relevance_bonus += 0.20

    title_lower = title.lower()

    if (
        query_symbol
        and (
            _contains_query_term(title, query_symbol)
            or (query_company and query_company.lower() in title_lower)
        )
    ):
        relevance_bonus += 0.10

    if query_symbol and item_symbol == query_symbol and has_symbol_or_company_match:
        relevance_bonus += 0.15

    if query_sector and item_sector == query_sector:
        relevance_bonus += 0.10

    is_market_item = item_symbol == "KSE100" or item_news_type == "market_news"
    has_market_term = _has_market_wide_terms(combined_text)

    if is_market_item and has_market_term:
        relevance_bonus += 0.05

    if len(article_text) > 1000:
        relevance_bonus += 0.05

    return round(relevance_bonus, 4)


class NewsVectorStore:
    def __init__(self, metadata: Optional[List[Dict[str, Any]]] = None):
        self._external_metadata = metadata is not None
        self.metadata = metadata if metadata is not None else self._load_metadata()

        self.model = None
        self.index = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.embedding_error = ""

        try:
            if self._external_metadata:
                raise RuntimeError("Using injected metadata; dense persisted index skipped.")

            if not _vector_search_available():
                raise RuntimeError(
                    "Vector search dependencies are not installed. "
                    f"{FAISS_IMPORT_ERROR or NUMPY_IMPORT_ERROR or SENTENCE_TRANSFORMERS_IMPORT_ERROR}"
                )

            if not INDEX_FILE.exists():
                raise FileNotFoundError(
                    "FAISS index not found. Run: python -m rag_layer.create_embeddings"
                )

            local_files_only = not _allow_model_downloads()
            if local_files_only:
                _set_huggingface_offline_mode()

            mode = "local cache only" if local_files_only else "downloads allowed"
            print(f"Loading embedding model ({mode})...")
            self.model = SentenceTransformer(
                MODEL_NAME,
                local_files_only=local_files_only,
                model_kwargs={"use_safetensors": False},
            )

            print("Loading FAISS index...")
            self.index = faiss.read_index(str(INDEX_FILE))
        except Exception as exc:
            self.embedding_error = str(exc)
            print(
                "Embedding model unavailable; using lexical news fallback. "
                f"Set {ALLOW_MODEL_DOWNLOADS_ENV}=1 to allow model downloads. "
                f"Error: {exc}"
            )
            self._load_or_build_tfidf_index()

        self.known_symbols = {
            _clean_text(item.get("symbol")).upper()
            for item in self.metadata
            if len(_clean_text(item.get("symbol"))) >= 3
        }

        print(f"Vector store loaded with {len(self.metadata)} news records.")

    def _load_metadata(self) -> List[Dict[str, Any]]:
        if METADATA_FILE.exists():
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)

        print(
            "Vector metadata not found; loading data/psx_news.csv directly. "
            "Run python -m rag_layer.create_embeddings to persist an index."
        )
        df = load_news()
        if df.empty:
            return []

        df = df.copy()
        df["published_date"] = (
            df["published_date"]
            .dt.strftime("%Y-%m-%d")
            .fillna("")
            if hasattr(df["published_date"], "dt")
            else df["published_date"].astype(str)
        )
        return df.fillna("").to_dict(orient="records")

    def _load_or_build_tfidf_index(self) -> None:
        try:
            if TFIDF_INDEX_FILE.exists():
                with open(TFIDF_INDEX_FILE, "rb") as f:
                    payload = pickle.load(f)
                self.tfidf_vectorizer = payload["vectorizer"]
                self.tfidf_matrix = payload["matrix"]
                return

            from sklearn.feature_extraction.text import TfidfVectorizer

            documents = [
                _clean_text(item.get("document_text"))
                or " ".join(
                    [
                        _clean_text(item.get("title")),
                        _clean_text(item.get("summary")),
                        _clean_text(item.get("article_text")),
                    ]
                )
                for item in self.metadata
            ]

            if not documents:
                return

            self.tfidf_vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                max_features=20000,
                ngram_range=(1, 2),
            )
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
        except Exception as exc:
            print(f"TF-IDF fallback unavailable; using keyword search only. Error: {exc}")
            self.tfidf_vectorizer = None
            self.tfidf_matrix = None

    def _has_competing_symbol_title(
        self,
        item: Dict[str, Any],
        query_symbol: Optional[str],
        query_company: Optional[str],
    ) -> bool:
        title = _clean_text(item.get("title"))
        title_lower = title.lower()
        item_symbol = _clean_text(item.get("symbol")).upper()
        query_symbol = _clean_text(query_symbol).upper()
        query_company = _clean_text(query_company)

        if not title or not query_symbol or item_symbol != query_symbol:
            return False

        if _contains_query_term(title, query_symbol):
            return False

        if query_company and query_company.lower() in title_lower:
            return False

        for known_symbol in self.known_symbols:
            if known_symbol in {query_symbol, "KSE100"}:
                continue

            if _contains_query_term(title, known_symbol):
                return True

        return False

    def _passes_search_filters(
        self,
        item: Dict[str, Any],
        symbol: Optional[str],
        sector: Optional[str],
        company: Optional[str],
        query_symbol: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        news_type: Optional[str],
    ) -> bool:
        if is_low_quality_news(item):
            return False

        if self._has_competing_symbol_title(
            item=item,
            query_symbol=query_symbol or symbol,
            query_company=company,
        ):
            return False

        if not self._passes_relevance_filter(
            item=item,
            filter_symbol=symbol,
            query_symbol=query_symbol or symbol,
            query_company=company,
        ):
            return False

        item_symbol = str(item.get("symbol", "")).upper()
        item_sector = str(item.get("sector", "")).lower()
        item_news_type = str(item.get("news_type", "")).lower()
        published_date = str(item.get("published_date", ""))[:10]
        has_valid_date = published_date.lower() not in ["", "nat", "nan", "none"]

        if symbol and item_symbol != symbol.upper():
            return False

        if sector and item_sector != sector.lower():
            return False

        if news_type and item_news_type != news_type.lower():
            return False

        if start_date and has_valid_date and published_date < start_date:
            return False

        if end_date and has_valid_date and published_date > end_date:
            return False

        return True

    def _lexical_similarity_score(
        self,
        item: Dict[str, Any],
        terms: List[str],
        query_symbol: Optional[str],
        query_company: Optional[str],
    ) -> float:
        title = _clean_text(item.get("title"))
        summary = _clean_text(item.get("summary"))
        article_text = _clean_text(item.get("article_text"))
        combined_text = f"{title} {summary} {article_text}"

        if not terms:
            return 0.0

        title_matches = sum(1 for term in terms if _contains_query_term(title, term))
        text_matches = sum(
            1 for term in terms if _contains_query_term(combined_text, term)
        )

        score = (text_matches / len(terms)) * 0.45
        score += (title_matches / len(terms)) * 0.25

        if query_symbol and _contains_query_term(combined_text, query_symbol):
            score += 0.20

        if query_company and query_company.lower() in combined_text.lower():
            score += 0.20

        return round(min(score, 0.95), 4)

    def _sort_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            results,
            key=lambda item: (
                item.get("final_score", 0.0),
                item.get("similarity_score", 0.0),
            ),
            reverse=True,
        )

    def _lexical_search(
        self,
        query: str,
        top_k: int,
        symbol: Optional[str],
        sector: Optional[str],
        company: Optional[str],
        query_symbol: Optional[str],
        query_sector: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        news_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        terms = _query_terms(query)
        results = []

        for raw_item in self.metadata:
            item = raw_item.copy()

            if not self._passes_search_filters(
                item=item,
                symbol=symbol,
                sector=sector,
                company=company,
                query_symbol=query_symbol,
                start_date=start_date,
                end_date=end_date,
                news_type=news_type,
            ):
                continue

            similarity_score = self._lexical_similarity_score(
                item=item,
                terms=terms,
                query_symbol=query_symbol or symbol,
                query_company=company,
            )
            relevance_bonus = _calculate_relevance_bonus(
                item=item,
                query_symbol=query_symbol or symbol,
                query_sector=query_sector or sector,
                query_company=company,
            )

            item["similarity_score"] = similarity_score
            item["relevance_bonus"] = relevance_bonus
            item["final_score"] = round(similarity_score + relevance_bonus, 4)
            results.append(item)

        return self._sort_results(results)[:top_k]

    def _tfidf_search(
        self,
        query: str,
        top_k: int,
        symbol: Optional[str],
        sector: Optional[str],
        company: Optional[str],
        query_symbol: Optional[str],
        query_sector: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        news_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        if self.tfidf_vectorizer is None or self.tfidf_matrix is None:
            return self._lexical_search(
                query=query,
                top_k=top_k,
                symbol=symbol,
                sector=sector,
                company=company,
                query_symbol=query_symbol,
                query_sector=query_sector,
                start_date=start_date,
                end_date=end_date,
                news_type=news_type,
            )

        query_vector = self.tfidf_vectorizer.transform([query])
        scores = (self.tfidf_matrix @ query_vector.T).toarray().ravel()
        search_k = min(len(self.metadata), max(top_k * 50, 200))
        ranked_indices = scores.argsort()[::-1][:search_k]
        results = []

        for idx in ranked_indices:
            item = self.metadata[int(idx)].copy()

            if not self._passes_search_filters(
                item=item,
                symbol=symbol,
                sector=sector,
                company=company,
                query_symbol=query_symbol,
                start_date=start_date,
                end_date=end_date,
                news_type=news_type,
            ):
                continue

            similarity_score = round(float(scores[idx]), 4)
            relevance_bonus = _calculate_relevance_bonus(
                item=item,
                query_symbol=query_symbol or symbol,
                query_sector=query_sector or sector,
                query_company=company,
            )
            item["similarity_score"] = similarity_score
            item["relevance_bonus"] = relevance_bonus
            item["final_score"] = round(similarity_score + relevance_bonus, 4)
            results.append(item)

        return self._sort_results(results)[:top_k]

    def _passes_relevance_filter(
        self,
        item: Dict[str, Any],
        filter_symbol: Optional[str],
        query_symbol: Optional[str],
        query_company: Optional[str],
    ) -> bool:
        title = _clean_text(item.get("title"))
        article_text = _clean_text(item.get("article_text"))
        combined_text = f"{title} {article_text}"
        item_symbol = _clean_text(item.get("symbol")).upper()
        item_news_type = _clean_text(item.get("news_type")).lower()
        filter_symbol = _clean_text(filter_symbol).upper()
        query_symbol = _clean_text(query_symbol).upper()

        has_market_terms = _has_market_wide_terms(combined_text)
        is_market_item = item_symbol == "KSE100" or item_news_type == "market_news"

        if is_market_item and not has_market_terms:
            return False

        if not query_symbol or query_symbol == "KSE100":
            return True

        is_same_symbol_lookup = (
            item_symbol == query_symbol
            or (filter_symbol and filter_symbol == query_symbol)
        )

        if not is_same_symbol_lookup:
            return True

        return (
            _has_strong_symbol_or_company_match(
                item=item,
                query_symbol=query_symbol,
                query_company=query_company,
            )
            or has_market_terms
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        symbol: Optional[str] = None,
        sector: Optional[str] = None,
        company: Optional[str] = None,
        query_symbol: Optional[str] = None,
        query_sector: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        news_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if top_k <= 0:
            return []

        if self.model is None or self.index is None:
            return self._tfidf_search(
                query=query,
                top_k=top_k,
                symbol=symbol,
                sector=sector,
                company=company,
                query_symbol=query_symbol,
                query_sector=query_sector,
                start_date=start_date,
                end_date=end_date,
                news_type=news_type,
            )

        try:
            query_embedding = self.model.encode(
                [query],
                convert_to_numpy=True
            )

            query_embedding = np.array(query_embedding).astype("float32")
            faiss.normalize_L2(query_embedding)

            search_k = min(len(self.metadata), max(top_k * 50, 200))

            scores, indices = self.index.search(query_embedding, search_k)
        except Exception as exc:
            print(f"Embedding search failed; using lexical fallback. Error: {exc}")
            return self._lexical_search(
                query=query,
                top_k=top_k,
                symbol=symbol,
                sector=sector,
                company=company,
                query_symbol=query_symbol,
                query_sector=query_sector,
                start_date=start_date,
                end_date=end_date,
                news_type=news_type,
            )

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            item = self.metadata[idx].copy()

            if not self._passes_search_filters(
                item=item,
                symbol=symbol,
                sector=sector,
                company=company,
                query_symbol=query_symbol,
                start_date=start_date,
                end_date=end_date,
                news_type=news_type,
            ):
                continue

            similarity_score = round(float(score), 4)
            relevance_bonus = _calculate_relevance_bonus(
                item=item,
                query_symbol=query_symbol or symbol,
                query_sector=query_sector or sector,
                query_company=company,
            )

            item["similarity_score"] = similarity_score
            item["relevance_bonus"] = relevance_bonus
            item["final_score"] = round(similarity_score + relevance_bonus, 4)
            results.append(item)

        return self._sort_results(results)[:top_k]


if __name__ == "__main__":
    store = NewsVectorStore()

    results = store.search(
        query="HBL PSX banking market price movement",
        top_k=5,
        symbol="HBL",
        sector="Banking",
        company="Habib Bank Limited",
        start_date="2026-05-01",
        end_date="2026-05-09",
    )

    print("\nSearch Results:")
    for item in results:
        print("-" * 80)
        print("Date:", item.get("published_date"))
        print("Symbol:", item.get("symbol"))
        print("Sector:", item.get("sector"))
        print("Source:", item.get("source"))
        print("Type:", item.get("news_type"))
        print("Similarity Score:", item.get("similarity_score"))
        print("Final Score:", item.get("final_score"))
        print("Title:", item.get("title"))
        print("Original URL:", item.get("original_url"))
        print("Article Length:", len(str(item.get("article_text", ""))))
