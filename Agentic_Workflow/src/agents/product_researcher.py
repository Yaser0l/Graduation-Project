"""Product Research Agent for finding compatible parts and products."""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.states.writer_state import WriterState
from src.tools.tavily_tool import search_products
import config
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


class ProductResearchAgent:
    """Agent that researches and recommends automotive products."""
    
    def __init__(self):
        """Initialize the Product Research agent."""
        agent_config = config.AGENT_MODELS["product_researcher"]
        llm_params = {
            "model": agent_config["model"],
            "temperature": agent_config["temperature"],
            "api_key": config.OPENAI_API_KEY,
            "timeout": config.AGENT_LLM_TIMEOUT_SEC,
            "max_retries": config.AGENT_LLM_MAX_RETRIES,
        }
        if config.base_url:
            llm_params["base_url"] = config.base_url
        self.llm = ChatOpenAI(**llm_params)
    
    def _extract_product_needs(self, obd2_analysis: str) -> List[str]:
        """Extract product types needed from OBD2 analysis.
        
        Args:
            obd2_analysis: The OBD2 technical analysis
            
        Returns:
            List of product types needed
        """
        # Build prompt to extract product needs
        prompt = f"""Based on the following automotive diagnostic analysis, identify what parts or products the customer needs to purchase.

DIAGNOSTIC ANALYSIS:
{obd2_analysis}

List only the specific product types needed (e.g., "TPMS sensor", "tires", "brake pads", "spark plugs").
Provide a simple comma-separated list, nothing else.

Product types needed:"""
        
        messages = [
            SystemMessage(content="You are an automotive parts specialist."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        products_text = response.content.strip()
        
        # Parse the response
        products = [p.strip() for p in products_text.split(",") if p.strip()]
        
        return products
    
    def _search_for_products(
        self,
        product_type: str,
        car_info: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for specific products.
        
        Args:
            product_type: Type of product to search for
            car_info: Car information for compatibility
            max_results: Maximum number of results
            
        Returns:
            List of product recommendations
        """
        # StructuredTool requires invocation with named arguments
        return search_products.invoke({
            "product_type": product_type,
            "car_info": car_info,
            "max_results": max_results
        })
    
    def execute(self, state: WriterState) -> Dict[str, Any]:
        """Execute the Product Research agent.
        
        Args:
            state: Current writer state
            
        Returns:
            Updated state dictionary
        """
        # Extract data from state
        obd2_analysis = state["obd2_analysis"]
        car_metadata = state["car_metadata"]
        
        # Format car information
        car_info = f"{car_metadata.year} {car_metadata.car_name} {car_metadata.car_model}"
        
        # Extract product needs from analysis
        print("[Product Researcher] Extracting product needs from analysis...")
        product_types = self._extract_product_needs(
            (obd2_analysis or "")[:config.PRODUCT_NEEDS_ANALYSIS_CHARS]
        )
        
        print(f"[Product Researcher] Identified product needs: {product_types}")
        
        # Search for each product type
        all_recommendations = []
        
        selected_types = product_types[:max(1, config.PRODUCT_SEARCH_MAX_TYPES)]
        if selected_types:
            with ThreadPoolExecutor(max_workers=min(3, len(selected_types))) as ex:
                future_map = {
                    ex.submit(
                        self._search_for_products,
                        product_type,
                        car_info,
                        max(1, config.PRODUCT_SEARCH_RESULTS_PER_TYPE),
                    ): product_type
                    for product_type in selected_types
                }

                for future in as_completed(future_map):
                    product_type = future_map[future]
                    print(f"[Product Researcher] Searching for: {product_type}")
                    try:
                        products = future.result()
                    except Exception as e:
                        print(f"[Product Researcher] Search failed for {product_type}: {e}")
                        products = []

                    if products:
                        all_recommendations.extend(products)
        
        print(f"[Product Researcher] Found {len(all_recommendations)} product recommendations")

        # Debug output for tests: show product recommendations
        if all_recommendations:
            print("\n" + "-" * 60)
            print("Product Researcher Agent - Recommendations")
            print("-" * 60 + "\n")
            for i, p in enumerate(all_recommendations, 1):
                print(f"{i}. {p.get('product_name', 'Unknown')}")
                print(f"   Type: {p.get('product_type', '')}")
                if p.get('url'):
                    print(f"   URL: {p.get('url')}")
                if p.get('description'):
                    preview = p['description'][:200].replace("\n", " ")
                    print(f"   Desc: {preview}{'...' if len(p['description']) > 200 else ''}")
                print()
            print("-" * 60 + "\n")
        
        return {
            "product_recommendations": all_recommendations if all_recommendations else None
        }


# Node function for LangGraph
def product_researcher_node(state: WriterState) -> Dict[str, Any]:
    """Node function for Product Research agent.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    agent = ProductResearchAgent()
    return agent.execute(state)

