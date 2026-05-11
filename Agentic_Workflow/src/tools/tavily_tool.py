"""Tavily web search tool."""
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from tavily import TavilyClient
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import time
import config


# Initialize Tavily client safely
tavily_client = None
if getattr(config, 'TAVILY_API_KEY', None):
    try:
        tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize Tavily client: {e}")


_cache: Dict[str, Any] = {}


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


def _run_tavily_search(query: str, max_results: int, include_domains: Optional[List[str]] = None):
    if not tavily_client:
        return None

    depth = (config.TAVILY_SEARCH_DEPTH or "basic").lower()
    if depth not in {"basic", "advanced"}:
        depth = "basic"

    args = {
        "query": query,
        "max_results": max(1, min(int(max_results), 8)),
        "search_depth": depth,
    }
    if include_domains:
        args["include_domains"] = include_domains

    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(tavily_client.search, **args)
        return future.result(timeout=max(3, int(config.TAVILY_TIMEOUT_SEC)))

@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information using Tavily.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        Formatted search results
    """
    try:
        if not tavily_client:
            return "Web search is currently disabled (no API key configured)."

        max_results = min(max_results, config.TAVILY_MAX_RESULTS_DEFAULT)
        cache_key = f"search_web::{query.strip().lower()}::{max_results}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
            
        # Perform search
        response = _run_tavily_search(query=query, max_results=max_results)
        
        if not response or 'results' not in response:
            return "No search results found."
        
        results = response['results']
        
        if not results:
            return "No search results found."
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            content = result.get('content', 'No content')
            url = result.get('url', 'No URL')
            
            formatted_results.append(
                f"[Result {i}]\n"
                f"Title: {title}\n"
                f"Content: {content}\n"
                f"URL: {url}\n"
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
    """Search for automotive products and parts.
    
    Args:
        product_type: Type of product (e.g., 'tires', 'TPMS sensor', 'brake pads')
        car_info: Car information for compatibility (e.g., '2020 Toyota Camry')
        max_results: Maximum number of results
        
    Returns:
        List of product recommendations with details
    """
    try:
        if not tavily_client:
            return []

        max_results = min(max_results, config.TAVILY_MAX_RESULTS_DEFAULT)
        cache_key = f"search_products::{product_type.strip().lower()}::{car_info.strip().lower()}::{max_results}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
            
        query = f"buy {product_type} for {car_info} price online"

        response = _run_tavily_search(query=query, max_results=max_results)
        
        if not response or 'results' not in response:
            return []
        
        results = response['results']
        
        # Parse and structure product information
        products = []
        for result in results:
            product = {
                "product_name": result.get('title', 'Unknown Product'),
                "product_type": product_type,
                "description": result.get('content', ''),
                "url": result.get('url', ''),
                "source": result.get('url', '').split('/')[2] if result.get('url') else 'Unknown'
            }
            products.append(product)
        
        _cache_set(cache_key, products)
        return products
        
    except FuturesTimeoutError:
        print("Product search timed out, continuing without product hits")
        return []
    except Exception as e:
        print(f"Error searching for products: {str(e)}")
        return []


def search_technical_info(query: str) -> str:
    """Search for technical automotive information.
    
    Args:
        query: Technical query
        
    Returns:
        Formatted technical information
    """
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
            include_domains=["repairpal.com", "yourmechanic.com", "carcomplaints.com", "obd-codes.com"]
        )
        
        if not response or 'results' not in response:
            return "No technical information found."
        
        results = response['results']
        
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

