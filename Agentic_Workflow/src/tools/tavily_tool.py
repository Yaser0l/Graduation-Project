"""Tavily web search tool."""
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from tavily import TavilyClient
import config


# Initialize Tavily client
tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)


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
        # Perform search
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )
        
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
        
        return "\n".join(formatted_results)
        
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
        query = f"buy {product_type} for {car_info} price online"
        
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )
        
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
        
        return products
        
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
        response = tavily_client.search(
            query=query,
            max_results=3,
            search_depth="advanced",
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
        
        return "\n---\n".join(formatted)
        
    except Exception as e:
        return f"Error searching technical information: {str(e)}"

