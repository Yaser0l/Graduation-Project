"""Tavily web search tool."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from langchain_core.tools import tool
from tavily import TavilyClient
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import time

import config

tavily_client = None
if getattr(config, "TAVILY_API_KEY", None):
    try:
        tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize Tavily client: {e}")

_cache: Dict[str, Any] = {}

# Category/listing pages — not a buyable SKU
_BAD_URL_PATTERNS = re.compile(
    r"/(c/|category/|search|find/|shop/|collections/|browse|"
    r"results\?|s\?|list\.|catalog\?|/auto/[^/]+-[^/]+-tpms-sensor$)",
    re.IGNORECASE,
)

# Product detail heuristics (path depth, part numbers, /p/, /dp/, /itm/)
_GOOD_URL_PATTERNS = re.compile(
    r"(/dp/|/gp/product/|/itm/|/p/|/product[_-]?|/parts/|"
    r"/\d{5,}|[A-Z0-9]{2,}-[A-Z0-9]{2,}|\d{8,})",
    re.IGNORECASE,
)


def _cache_get(key: str):
    item = _cache.get(key)
    if not item:
        return None
    expires_at, value = item
    if time.time() >= expires_at:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any):
    _cache[key] = (time.time() + max(30, int(config.TAVILY_CACHE_TTL_SEC)), value)


def _product_domains() -> List[str]:
    raw = getattr(config, "PRODUCT_SEARCH_DOMAINS", None) or []
    return [d.strip() for d in raw if d.strip()]


def _is_product_page_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    if _BAD_URL_PATTERNS.search(url):
        return False
    path = urlparse(url).path or ""
    if len(path) < 12:
        return False
    if _GOOD_URL_PATTERNS.search(url):
        return True
    # Long path with alphanumeric tail often = PDP
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 3 and any(len(s) >= 6 for s in segments[-2:]):
        return True
    return False


def _score_product_result(result: Dict[str, Any]) -> float:
    url = result.get("url") or ""
    title = (result.get("title") or "").lower()
    score = 0.0
    if _is_product_page_url(url):
        score += 2.0
    else:
        score -= 1.5
    if any(w in title for w in ("buy", "oem", "genuine", "replacement", "sensor", "part")):
        score += 0.5
    if any(w in url.lower() for w in ("walmart.com/c/", "ebay.com/sch", "ebay.com/b/")):
        score -= 2.0
    return score


def _run_tavily_search(
    query: str,
    max_results: int,
    include_domains: Optional[List[str]] = None,
    search_depth: Optional[str] = None,
):
    if not tavily_client:
        return None

    depth = (search_depth or config.TAVILY_SEARCH_DEPTH or "basic").lower()
    if depth not in {"basic", "advanced"}:
        depth = "basic"

    args = {
        "query": query,
        "max_results": max(1, min(int(max_results), 10)),
        "search_depth": depth,
    }
    if include_domains:
        args["include_domains"] = include_domains

    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(tavily_client.search, **args)
        return future.result(timeout=max(3, int(config.TAVILY_TIMEOUT_SEC)))


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information using Tavily."""
    try:
        if not tavily_client:
            return "Web search is currently disabled (no API key configured)."

        max_results = min(max_results, config.TAVILY_MAX_RESULTS_DEFAULT)
        cache_key = f"search_web::{query.strip().lower()}::{max_results}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        response = _run_tavily_search(query=query, max_results=max_results)

        if not response or "results" not in response:
            return "No search results found."

        results = response["results"]
        if not results:
            return "No search results found."

        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"[Result {i}]\n"
                f"Title: {result.get('title', 'No title')}\n"
                f"Content: {result.get('content', 'No content')}\n"
                f"URL: {result.get('url', 'No URL')}\n"
            )

        output = "\n".join(formatted_results)
        _cache_set(cache_key, output)
        return output

    except FuturesTimeoutError:
        return "Web search timed out. Proceeding with available diagnostic knowledge."
    except Exception as e:
        return f"Error performing web search: {str(e)}"


@tool
def search_products(product_type: str, car_info: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search for specific automotive product pages (PDP URLs, not category listings)."""
    try:
        if not tavily_client:
            return []

        max_results = min(max_results, config.TAVILY_MAX_RESULTS_DEFAULT)
        cache_key = f"search_products::{product_type.strip().lower()}::{car_info.strip().lower()}::{max_results}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        domains = _product_domains()
        # Target product detail pages with part-oriented queries
        query = (
            f'"{car_info}" {product_type} OEM replacement part number '
            f"buy in stock -category -search results"
        )

        response = _run_tavily_search(
            query=query,
            max_results=max(5, max_results * 3),
            include_domains=domains if domains else None,
            search_depth="advanced",
        )

        if not response or "results" not in response:
            return []

        ranked = sorted(
            response["results"],
            key=_score_product_result,
            reverse=True,
        )

        products: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()
        for result in ranked:
            url = (result.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            if not _is_product_page_url(url):
                continue
            seen_urls.add(url)
            products.append(
                {
                    "product_name": result.get("title", "Unknown Product"),
                    "product_type": product_type,
                    "description": result.get("content", ""),
                    "url": url,
                    "source": urlparse(url).netloc,
                    "page_type": "product_detail",
                }
            )
            if len(products) >= max_results:
                break

        # Fallback: relax URL filter but still reject obvious category pages
        if len(products) < max_results:
            for result in ranked:
                url = (result.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                if _BAD_URL_PATTERNS.search(url):
                    continue
                seen_urls.add(url)
                products.append(
                    {
                        "product_name": result.get("title", "Unknown Product"),
                        "product_type": product_type,
                        "description": result.get("content", ""),
                        "url": url,
                        "source": urlparse(url).netloc,
                        "page_type": "fallback",
                    }
                )
                if len(products) >= max_results:
                    break

        _cache_set(cache_key, products)
        return products

    except FuturesTimeoutError:
        print("Product search timed out, continuing without product hits")
        return []
    except Exception as e:
        print(f"Error searching for products: {str(e)}")
        return []


def search_technical_info(query: str) -> str:
    """Search for technical automotive information."""
    try:
        if not tavily_client:
            return "Technical web search is disabled. Please rely on standard knowledge base."

        max_results = min(3, config.TAVILY_MAX_RESULTS_DEFAULT)
        cache_key = f"search_technical::{query.strip().lower()}::{max_results}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        response = _run_tavily_search(
            query=query,
            max_results=3,
            include_domains=["repairpal.com", "yourmechanic.com", "carcomplaints.com", "obd-codes.com"],
        )

        if not response or "results" not in response:
            return "No technical information found."

        results = response["results"]
        formatted = []
        for result in results:
            formatted.append(
                f"Source: {result.get('title', 'Unknown')}\n"
                f"{result.get('content', '')}\n"
                f"Reference: {result.get('url', '')}\n"
            )

        output = "\n---\n".join(formatted)
        _cache_set(cache_key, output)
        return output

    except FuturesTimeoutError:
        return "Technical web search timed out. Proceeding with RAG context only."
    except Exception as e:
        return f"Error searching technical information: {str(e)}"
