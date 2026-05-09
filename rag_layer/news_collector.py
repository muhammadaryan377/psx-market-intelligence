import argparse
import hashlib
import html
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote, quote_plus, urlparse

import feedparser
import pandas as pd
import requests
import trafilatura
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from newspaper import Article


OUTPUT_FILE = Path("data/psx_news.csv")
SYMBOLS_FILE = Path("data/symbols_seed.csv")
MANUAL_URL_FILE = Path("data/manual_news_urls.csv")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    )
}
MIN_ARTICLE_TEXT_CHARS = 300
REQUEST_DELAY_SECONDS = 0.2

CSV_COLUMNS = [
    "record_id",
    "published_date",
    "symbol",
    "company",
    "sector",
    "title",
    "summary",
    "article_text",
    "source",
    "publisher",
    "url",
    "original_url",
    "news_type",
]


ALLOWED_SOURCES = {
    "Business Recorder": ["brecorder.com", "markets.brecorder.com"],
    "Dawn Business": ["dawn.com"],
    "Mettis Global": ["mettisglobal.news"],
    "Profit by Pakistan Today": ["profit.pakistantoday.com.pk"],
    "The News Business": ["thenews.com.pk"],
    "PSX Announcements": ["psx.com.pk", "dps.psx.com.pk"],

    # Extra PSX / market news sources
    "Aaj English": ["aajenglish.tv"],
    "Samaa Money": ["samaa.tv"],
    "Associated Press of Pakistan": ["app.com.pk"],

    # Brokerage / research sources
    "Arif Habib Research": ["arifhabibltd.com"],
    "Topline Securities Research": ["topline.com.pk"],
    "AKD Securities Research": ["akdsl.com"],
    "JS Global Research": ["jsglobalonline.com"],

    # PSX data / announcement mirrors
    "KSE Stocks": ["ksestocks.com"],
    "SCS Trade Announcements": ["scstrade.com"],
}


SOURCE_SEARCH_DOMAINS = {
    "Business Recorder": ["brecorder.com", "markets.brecorder.com"],
    "Dawn Business": ["dawn.com"],
    "Mettis Global": ["mettisglobal.news"],
    "Profit by Pakistan Today": ["profit.pakistantoday.com.pk"],
    "The News Business": ["thenews.com.pk"],
    "PSX Announcements": ["psx.com.pk", "dps.psx.com.pk"],

    # Extra news sources
    "Aaj English": ["aajenglish.tv"],
    "Samaa Money": ["samaa.tv"],
    "Associated Press of Pakistan": ["app.com.pk"],

    # Research sources
    "Arif Habib Research": ["arifhabibltd.com"],
    "Topline Securities Research": ["topline.com.pk"],
    "AKD Securities Research": ["akdsl.com"],
    "JS Global Research": ["jsglobalonline.com"],

    # PSX data / announcements
    "KSE Stocks": ["ksestocks.com"],
    "SCS Trade Announcements": ["scstrade.com"],
}


MARKET_KEYWORDS = [
    "psx",
    "kse-100",
    "kse100",
    "benchmark index",
    "stock market",
    "stocks",
    "shares",
    "market closes",
    "market gains",
    "market falls",
    "bulls",
    "bears",
    "index gains",
    "index loses",
]


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = html.unescape(str(text))
    text = BeautifulSoup(text, "html.parser").get_text(" ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_title(title: str, source: str = "", publisher: str = "") -> str:
    title = clean_text(title)
    source = clean_text(source)
    publisher = clean_text(publisher)

    for suffix in [source, publisher]:
        if suffix and title.lower().endswith(f"- {suffix}".lower()):
            title = title[: -(len(suffix) + 2)].strip()

    return title


def make_record_id(source: str, url: str, title: str) -> str:
    raw = f"{source}|{str(url).strip()}|{title}".lower().encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def parse_date(value) -> str:
    if not value:
        return ""

    try:
        dt = date_parser.parse(str(value))
        return dt.date().isoformat()
    except Exception:
        return ""


def is_date_in_range(date_str: str, start_date: str, end_date: str) -> bool:
    if not date_str:
        return True

    try:
        d = datetime.fromisoformat(str(date_str)[:10]).date()
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
        return start <= d <= end
    except Exception:
        return True


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def get_source_from_url(url: str) -> Optional[str]:
    host = get_domain(url)

    for source_name, domains in ALLOWED_SOURCES.items():
        for domain in domains:
            if host == domain or host.endswith("." + domain) or domain in host:
                return source_name

    return None


def is_market_wide_news(symbol: str, company: str, title: str, content: str) -> bool:
    symbol = str(symbol).upper().strip()
    company = str(company).lower().strip()
    text = f"{title} {content}".lower()

    if symbol in ["KSE100", "KSE-100", "MARKET"]:
        return True

    has_market_keyword = any(word in text for word in MARKET_KEYWORDS)
    has_symbol_reference = bool(
        re.search(rf"(?<![a-z0-9]){re.escape(symbol.lower())}(?![a-z0-9])", text)
    )

    company_variants = [company]
    if company.endswith(" limited"):
        company_variants.append(company[: -len(" limited")].strip())
    if company.endswith(" ltd"):
        company_variants.append(company[: -len(" ltd")].strip())

    has_company_reference = has_symbol_reference or any(
        variant and variant in text for variant in company_variants
    )

    return has_market_keyword and not has_company_reference


def detect_news_type(symbol: str, source: str, title: str, content: str) -> str:
    text = f"{title} {content}".lower()
    symbol = str(symbol).upper().strip()

    if source == "PSX Announcements":
        return "company_announcement"

    if source == "SCS Trade Announcements":
        return "company_announcement"

    if source in [
        "Arif Habib Research",
        "Topline Securities Research",
        "AKD Securities Research",
        "JS Global Research",
    ]:
        return "brokerage_research"

    if source == "KSE Stocks":
        return "market_data_summary"

    if symbol in ["KSE100", "KSE-100", "MARKET"]:
        return "market_news"

    macro_keywords = [
        "imf",
        "inflation",
        "interest rate",
        "policy rate",
        "rupee",
        "dollar",
        "oil prices",
        "sbp",
        "current account",
        "fiscal",
        "budget",
        "exports",
        "imports",
    ]

    if any(word in text for word in macro_keywords):
        return "macro_news"

    sector_keywords = [
        "banking sector",
        "cement sector",
        "oil and gas sector",
        "fertilizer sector",
        "technology sector",
        "power sector",
        "textile sector",
        "automobile sector",
        "pharmaceutical sector",
    ]

    if any(word in text for word in sector_keywords):
        return "sector_news"

    return "company_news"


def summarize_content(content: str, max_chars: int = 900) -> str:
    content = clean_text(content)

    if len(content) <= max_chars:
        return content

    return content[:max_chars].rsplit(" ", 1)[0] + "..."


def build_queries(symbol: str, company: str, sector: str, domain: str) -> List[str]:
    symbol = str(symbol).upper().strip()
    company = str(company).strip()
    sector = str(sector).strip()

    if symbol in ["KSE100", "KSE-100", "MARKET"]:
        return [
            f'"Pakistan Stock Exchange" site:{domain}',
            f'"KSE-100" site:{domain}',
            f'"PSX" "market" site:{domain}',
        ]

    queries = [f'"{symbol}" "PSX" site:{domain}']

    if company:
        queries.append(f'"{company}" site:{domain}')

    if sector:
        queries.append(f'"{sector}" "PSX" site:{domain}')

    return list(dict.fromkeys(queries))


def google_after_date(start_date: str) -> str:
    try:
        return (datetime.fromisoformat(start_date).date() - timedelta(days=1)).isoformat()
    except Exception:
        return start_date


def google_before_date(end_date: str) -> str:
    try:
        return (datetime.fromisoformat(end_date).date() + timedelta(days=1)).isoformat()
    except Exception:
        return end_date


def search_google_news_rss(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    encoded_query = quote_plus(query)

    rss_url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=en-PK&gl=PK&ceid=PK:en"
    )

    try:
        response = requests.get(
            rss_url,
            timeout=20,
            headers=REQUEST_HEADERS,
        )

        response.raise_for_status()
        feed = feedparser.parse(response.text)

        results = []

        for entry in feed.entries[:max_results]:
            publisher = ""

            try:
                publisher = entry.get("source", {}).get("title", "")
            except Exception:
                publisher = ""

            results.append(
                {
                    "title": clean_text(entry.get("title", "")),
                    "description": clean_text(entry.get("summary", "")),
                    "url": entry.get("link", ""),
                    "published_date": parse_date(
                        entry.get("published", "") or entry.get("updated", "")
                    ),
                    "publisher": clean_text(publisher),
                }
            )

        return results

    except Exception as e:
        print(f"RSS search failed: {e}")
        return []


def decode_google_news_url(url: str) -> str:
    """
    Decode modern Google News RSS article URLs by using the signed Google News
    batchexecute endpoint. Returns an empty string if Google does not decode it.
    """
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        if parsed.netloc.lower() != "news.google.com":
            return ""

        if len(path_parts) < 2 or path_parts[-2] not in ["articles", "read"]:
            return ""

        article_id = path_parts[-1]
        param_urls = [
            f"https://news.google.com/articles/{article_id}",
            f"https://news.google.com/rss/articles/{article_id}",
        ]

        signature = ""
        timestamp = ""

        for param_url in param_urls:
            try:
                response = requests.get(param_url, timeout=20, headers=REQUEST_HEADERS)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                data_element = soup.select_one("c-wiz > div[jscontroller]")
            except Exception:
                continue

            if data_element:
                signature = data_element.get("data-n-a-sg", "")
                timestamp = data_element.get("data-n-a-ts", "")
                break

        if not signature or not timestamp:
            return ""

        payload = [
            "Fbv4je",
            (
                '["garturlreq",'
                '[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,'
                'null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,'
                f'0,0,null,0],"{article_id}",{timestamp},"{signature}"]'
            ),
        ]

        response = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            timeout=20,
            headers={
                **REQUEST_HEADERS,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            data=f"f.req={quote(json.dumps([[payload]]))}",
        )
        response.raise_for_status()

        response_payload = json.loads(response.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(response_payload[0][2])[1]

        if decoded_url and "news.google.com" not in decoded_url.lower():
            return decoded_url.strip()

    except Exception:
        return ""

    return ""


def resolve_google_news_url(url: str) -> str:
    if not url:
        return ""

    if "news.google.com" not in url.lower():
        return url.strip()

    decoded_url = decode_google_news_url(url)

    if decoded_url:
        return decoded_url

    try:
        response = requests.get(
            url,
            timeout=20,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        final_url = response.url.strip()

        if final_url and "news.google.com" not in final_url.lower():
            return final_url

        return url

    except Exception:
        return url


def extract_article_with_newspaper(url: str) -> Dict[str, str]:
    try:
        article = Article(url, browser_user_agent=REQUEST_HEADERS["User-Agent"])
        article.download()
        article.parse()

        return {
            "title": clean_text(article.title or ""),
            "content": clean_text(article.text or ""),
            "published_date": parse_date(article.publish_date),
        }

    except Exception:
        return {"title": "", "content": "", "published_date": ""}


def extract_article_with_trafilatura(url: str) -> Dict[str, str]:
    try:
        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            return {"title": "", "content": "", "published_date": ""}

        content = trafilatura.extract(
            downloaded,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        return {
            "title": "",
            "content": clean_text(content or ""),
            "published_date": "",
        }

    except Exception:
        return {"title": "", "content": "", "published_date": ""}


def extract_full_article(url: str) -> Dict[str, str]:
    """
    Pehle newspaper3k try karta hai.
    Agar result weak ho to trafilatura try karta hai.
    """
    if not url:
        return {"title": "", "content": "", "published_date": ""}

    # Google News redirect links se aksar article text extract nahi hota.
    if "news.google.com" in url.lower():
        return {"title": "", "content": "", "published_date": ""}

    article = extract_article_with_newspaper(url)

    if len(article.get("content", "")) >= MIN_ARTICLE_TEXT_CHARS:
        return article

    fallback = extract_article_with_trafilatura(url)

    if len(fallback.get("content", "")) > len(article.get("content", "")):
        return fallback

    return article


def build_record(
    source_name: str,
    symbol: str,
    company: str,
    sector: str,
    title: str,
    description: str,
    published_date: str,
    publisher: str,
    google_news_url: str,
    original_url: str,
    article: Dict[str, str],
) -> Optional[Dict[str, str]]:

    article_title = clean_title(
        article.get("title", "") or title,
        source=source_name,
        publisher=publisher,
    )

    article_text = clean_text(article.get("content", ""))

    if not article_text:
        article_text = clean_text(description) or article_title

    article_date = article.get("published_date", "") or published_date
    summary = summarize_content(article_text)

    if not article_title and not summary:
        return None

    final_symbol = symbol
    final_company = company
    final_sector = sector

    if is_market_wide_news(symbol, company, article_title, article_text):
        final_symbol = "KSE100"
        final_company = "Market Index"
        final_sector = "Market"

    news_type = detect_news_type(
        symbol=final_symbol,
        source=source_name,
        title=article_title,
        content=article_text,
    )

    record = {
        "record_id": make_record_id(source_name, original_url or google_news_url, article_title),
        "published_date": article_date,
        "symbol": final_symbol,
        "company": final_company,
        "sector": final_sector,
        "title": article_title,
        "summary": summary,
        "article_text": article_text,
        "source": source_name,
        "publisher": publisher,
        "url": google_news_url,
        "original_url": original_url,
        "news_type": news_type,
    }

    return record


def collect_from_google_news_rss(
    start_date: str,
    end_date: str,
    max_per_query: int = 5,
    selected_symbols: Optional[List[str]] = None,
) -> List[Dict[str, str]]:

    if not SYMBOLS_FILE.exists():
        raise FileNotFoundError(
            f"Symbols file not found: {SYMBOLS_FILE}. Please create data/symbols_seed.csv"
        )

    symbols_df = pd.read_csv(SYMBOLS_FILE).fillna("")

    if selected_symbols:
        selected_symbols = [s.upper() for s in selected_symbols]
        symbols_df = symbols_df[
            symbols_df["symbol"].astype(str).str.upper().isin(selected_symbols)
        ]

    records = []
    seen_google_urls = set()
    query_after = google_after_date(start_date)
    query_before = google_before_date(end_date)

    for _, row in symbols_df.iterrows():
        symbol = str(row["symbol"]).upper().strip()
        company = str(row["company"]).strip()
        sector = str(row["sector"]).strip()

        print(f"\nCollecting news for {symbol} - {company}")

        for source_name, domains in SOURCE_SEARCH_DOMAINS.items():
            for domain in domains:
                queries = build_queries(symbol, company, sector, domain)

                for query in queries:
                    dated_query = f"{query} after:{query_after} before:{query_before}"

                    print(f"  Searching: {dated_query}")

                    results = search_google_news_rss(
                        query=dated_query,
                        max_results=max_per_query,
                    )

                    if not results:
                        print("  No results found.")
                        continue

                    for item in results[:max_per_query]:
                        title = clean_text(item.get("title", ""))
                        description = clean_text(item.get("description", ""))
                        google_news_url = item.get("url", "").strip()
                        published_date = parse_date(item.get("published_date", ""))
                        publisher = clean_text(item.get("publisher", ""))

                        if not google_news_url or google_news_url in seen_google_urls:
                            continue

                        seen_google_urls.add(google_news_url)

                        if published_date and not is_date_in_range(
                            published_date,
                            start_date,
                            end_date,
                        ):
                            continue

                        original_url = resolve_google_news_url(google_news_url)
                        resolved_source = get_source_from_url(original_url)

                        if (
                            original_url
                            and "news.google.com" not in original_url.lower()
                            and not resolved_source
                        ):
                            print(f"  Skipping non-allowed resolved URL: {original_url}")
                            continue

                        article = extract_full_article(original_url)

                        record = build_record(
                            source_name=resolved_source or source_name,
                            symbol=symbol,
                            company=company,
                            sector=sector,
                            title=title,
                            description=description,
                            published_date=published_date,
                            publisher=publisher,
                            google_news_url=google_news_url,
                            original_url=original_url,
                            article=article,
                        )

                        if record and is_date_in_range(
                            record.get("published_date", ""), start_date, end_date
                        ):
                            records.append(record)

                        time.sleep(REQUEST_DELAY_SECONDS)

    return records


def collect_from_manual_urls(
    manual_file: Path = MANUAL_URL_FILE,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, str]]:

    if not manual_file.exists():
        return []

    try:
        df = pd.read_csv(manual_file).fillna("")
    except pd.errors.EmptyDataError:
        return []

    if df.empty:
        return []

    records = []

    for _, row in df.iterrows():
        url = str(row.get("url", "")).strip()

        if not url:
            continue

        original_url = resolve_google_news_url(url)
        row_source = str(row.get("source", "")).strip()
        url_source = get_source_from_url(original_url) or get_source_from_url(url)
        source = row_source if row_source in ALLOWED_SOURCES else url_source or row_source

        if source not in ALLOWED_SOURCES:
            print(f"Skipping non-allowed source URL: {url}")
            continue

        published_date = parse_date(row.get("published_date", ""))

        if start_date and end_date and published_date:
            if not is_date_in_range(published_date, start_date, end_date):
                continue

        article = extract_full_article(original_url)

        title = (
            clean_text(row.get("title", ""))
            or article.get("title", "")
            or "Untitled news"
        )

        manual_summary = clean_text(row.get("summary", ""))
        article_text = clean_text(article.get("content", "")) or manual_summary or title

        symbol = str(row.get("symbol", "")).upper().strip()
        company = str(row.get("company", "")).strip()
        sector = str(row.get("sector", "")).strip()
        publisher = str(row.get("publisher", "")).strip()

        news_type = str(row.get("news_type", "")).strip()

        if not news_type:
            news_type = detect_news_type(
                symbol=symbol,
                source=source,
                title=title,
                content=article_text,
            )

        record = {
            "record_id": make_record_id(source, original_url or url, title),
            "published_date": published_date or article.get("published_date", ""),
            "symbol": symbol,
            "company": company,
            "sector": sector,
            "title": clean_title(title, source=source, publisher=publisher),
            "summary": summarize_content(article_text),
            "article_text": article_text,
            "source": source,
            "publisher": publisher,
            "url": url,
            "original_url": original_url or url,
            "news_type": news_type,
        }

        if not start_date or not end_date or is_date_in_range(
            record.get("published_date", ""), start_date, end_date
        ):
            records.append(record)

        time.sleep(REQUEST_DELAY_SECONDS)

    return records


def enrich_existing_record(record: Dict[str, str]) -> Dict[str, str]:
    url_columns = {"url", "original_url"}
    record = {
        col: (
            html.unescape(str(record.get(col, ""))).strip()
            if col in url_columns
            else clean_text(record.get(col, ""))
        )
        for col in CSV_COLUMNS
    }

    original_url = record.get("original_url") or record.get("url")

    if "news.google.com" in original_url.lower():
        resolved_url = resolve_google_news_url(record.get("url") or original_url)
        if resolved_url:
            original_url = resolved_url
            record["original_url"] = resolved_url

    resolved_source = get_source_from_url(original_url)
    if resolved_source:
        record["source"] = resolved_source

    article_text = clean_text(record.get("article_text", ""))
    article = {"title": "", "content": "", "published_date": ""}

    if original_url and "news.google.com" not in original_url.lower():
        if len(article_text) < MIN_ARTICLE_TEXT_CHARS:
            article = extract_full_article(original_url)
            extracted_text = clean_text(article.get("content", ""))

            if len(extracted_text) > len(article_text):
                article_text = extracted_text
                record["article_text"] = article_text

    if not article_text:
        article_text = clean_text(record.get("summary", "")) or clean_text(
            record.get("title", "")
        )
        record["article_text"] = article_text

    if article.get("title"):
        record["title"] = clean_title(
            article.get("title", ""),
            source=record.get("source", ""),
            publisher=record.get("publisher", ""),
        )
    else:
        record["title"] = clean_title(
            record.get("title", ""),
            source=record.get("source", ""),
            publisher=record.get("publisher", ""),
        )

    if article.get("published_date") and not record.get("published_date"):
        record["published_date"] = article.get("published_date", "")

    record["summary"] = summarize_content(article_text)

    if is_market_wide_news(
        record.get("symbol", ""),
        record.get("company", ""),
        record.get("title", ""),
        article_text,
    ):
        record["symbol"] = "KSE100"
        record["company"] = "Market Index"
        record["sector"] = "Market"

    record["news_type"] = detect_news_type(
        symbol=record.get("symbol", ""),
        source=record.get("source", ""),
        title=record.get("title", ""),
        content=article_text,
    )
    record["record_id"] = make_record_id(
        record.get("source", ""),
        record.get("original_url") or record.get("url"),
        record.get("title", ""),
    )

    return record


def save_records(records: List[Dict[str, str]]):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if records:
        new_df = pd.DataFrame(records)
    else:
        new_df = pd.DataFrame(columns=CSV_COLUMNS)

    for col in CSV_COLUMNS:
        if col not in new_df.columns:
            new_df[col] = ""

    new_df = new_df[CSV_COLUMNS]

    if OUTPUT_FILE.exists() and OUTPUT_FILE.stat().st_size > 0:
        try:
            old_df = pd.read_csv(OUTPUT_FILE).fillna("")
        except pd.errors.EmptyDataError:
            old_df = pd.DataFrame(columns=CSV_COLUMNS)

        for col in CSV_COLUMNS:
            if col not in old_df.columns:
                old_df[col] = ""

        old_df["article_text"] = old_df["article_text"].astype(str).str.strip()
        old_df.loc[old_df["article_text"] == "", "article_text"] = old_df[
            "summary"
        ].astype(str)
        old_df.loc[old_df["article_text"] == "", "article_text"] = old_df[
            "title"
        ].astype(str)

        old_df["original_url"] = old_df["original_url"].astype(str).str.strip()
        old_df.loc[old_df["original_url"] == "", "original_url"] = old_df[
            "url"
        ].astype(str)

        old_df = old_df[CSV_COLUMNS]
    else:
        old_df = pd.DataFrame(columns=CSV_COLUMNS)

    final_df = pd.concat([old_df, new_df], ignore_index=True)

    unresolved_mask = final_df["original_url"].astype(str).str.contains(
        "news.google.com", case=False, na=False
    )
    unresolved_count = int(unresolved_mask.sum())

    if unresolved_count:
        print(f"Resolving {unresolved_count} existing Google News URLs...")
        enriched_records = []

        for _, row in final_df.iterrows():
            record = row[CSV_COLUMNS].to_dict()

            if "news.google.com" in str(record.get("original_url", "")).lower():
                record = enrich_existing_record(record)

            enriched_records.append(record)

        final_df = pd.DataFrame(enriched_records)

        for col in CSV_COLUMNS:
            if col not in final_df.columns:
                final_df[col] = ""

        final_df = final_df[CSV_COLUMNS]

    final_df["record_id"] = final_df["record_id"].astype(str).str.strip()
    final_df = final_df[final_df["record_id"] != ""]
    before_dedup = len(final_df)
    final_df = final_df.drop_duplicates(subset=["record_id"], keep="last")

    final_df["_dedupe_title"] = final_df.apply(
        lambda row: clean_title(
            row.get("title", ""),
            source=row.get("source", ""),
            publisher=row.get("publisher", ""),
        ).lower(),
        axis=1,
    )
    final_df["_dedupe_date"] = final_df["published_date"].astype(str).str[:10]
    final_df["_dedupe_source"] = final_df["source"].astype(str).str.lower().str.strip()
    final_df = final_df.drop_duplicates(
        subset=["_dedupe_source", "_dedupe_date", "_dedupe_title"],
        keep="last",
    )

    final_df = final_df[CSV_COLUMNS]

    final_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"\nSaved {len(final_df)} total records to: {OUTPUT_FILE}")
    dropped_count = before_dedup - len(final_df)
    if dropped_count:
        print(f"Dropped {dropped_count} duplicate records during merge.")
    if not records:
        print("No new records collected; existing CSV was preserved.")


def main():
    parser = argparse.ArgumentParser(description="PSX historical news collector")

    parser.add_argument("--start", required=True, help="Start date: YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date: YYYY-MM-DD")

    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Optional symbols e.g. HBL UBL OGDC. If not provided, all symbols from symbols_seed.csv are used.",
    )

    parser.add_argument(
        "--max-per-query",
        type=int,
        default=3,
        help="Max news results per query",
    )

    args = parser.parse_args()

    all_records = []

    # 1. Automatically collect from manual URLs if file exists
    manual_records = collect_from_manual_urls(
        manual_file=MANUAL_URL_FILE,
        start_date=args.start,
        end_date=args.end,
    )
    all_records.extend(manual_records)

    # 2. Always collect from Google News RSS
    rss_records = collect_from_google_news_rss(
        start_date=args.start,
        end_date=args.end,
        max_per_query=args.max_per_query,
        selected_symbols=args.symbols,
    )
    all_records.extend(rss_records)

    # 3. Save merged + deduplicated output
    save_records(all_records)


if __name__ == "__main__":
    main()
