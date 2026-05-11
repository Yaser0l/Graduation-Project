"""Technical Writer Agent for creating detailed reports."""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.states.writer_state import WriterState
import config


class TechnicalWriterAgent:
    """Agent that writes comprehensive technical reports."""
    
    def __init__(self):
        """Initialize the Technical Writer agent."""
        agent_config = config.AGENT_MODELS["technical_writer"]
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
    
    def _format_products(self, products: list) -> str:
        """Format product recommendations for the report.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            Formatted product section
        """
        if not products:
            return "No specific products recommended at this time."
        
        formatted = ["RECOMMENDED PRODUCTS:\n"]
        
        for i, product in enumerate(products, 1):
            formatted.append(f"{i}. {product.get('product_name', 'Unknown Product')}")
            formatted.append(f"   Type: {product.get('product_type', 'N/A')}")
            if product.get('description'):
                formatted.append(f"   Description: {product.get('description', '')[:200]}...")
            if product.get('url'):
                formatted.append(f"   Link: {product.get('url', '')}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _build_report_prompt(
        self,
        obd2_analysis: str,
        car_info: str,
        products_section: str
    ) -> str:
        """Build the prompt for report generation.
        
        Args:
            obd2_analysis: Technical analysis from OBD2 orchestration
            car_info: Car metadata
            products_section: Formatted product recommendations
            
        Returns:
            Complete prompt
        """
        return f"""You are writing a comprehensive automotive diagnostic report for a customer.

VEHICLE INFORMATION:
{car_info}

TECHNICAL ANALYSIS:
{obd2_analysis}

{products_section}

TASK:
Create a well-structured, detailed report that combines the technical analysis with product recommendations. The report should include:

1. **Executive Summary**
   - Brief overview of findings
   - Severity level

2. **Detailed Findings**
   - Comprehensive explanation of all issues
   - Technical details and diagnostic codes
   - Impact on vehicle performance and safety

3. **Root Cause Analysis**
   - What caused these issues
   - Related factors

4. **Recommended Actions**
   - Immediate actions needed
   - Long-term maintenance recommendations
   - Priority order

5. **Product Recommendations**
   - Compatible parts and products
   - Why these specific products are recommended
   - Installation considerations

6. **Cost Considerations**
   - Estimated parts costs (if available)
   - Estimated labor complexity

7. **Safety Notes**
   - Any safety-critical issues
   - Driving restrictions if any

Write in a professional, clear, and comprehensive manner. Include all technical details but explain them clearly.

COMPREHENSIVE REPORT:"""
    
    def execute(self, state: WriterState) -> Dict[str, Any]:
        """Execute the Technical Writer agent.
        
        Args:
            state: Current writer state
            
        Returns:
            Updated state dictionary
        """
        # Extract data from state
        obd2_analysis = (state["obd2_analysis"] or "")[:config.TECH_WRITER_ANALYSIS_CHARS]
        car_metadata = state["car_metadata"]
        products = state.get("product_recommendations", [])
        
        # Format car information
        car_info = (
            f"{car_metadata.year} {car_metadata.car_name} {car_metadata.car_model}\n"
            f"Mileage: {car_metadata.mileage:,} miles\n"
            f"VIN: {car_metadata.vin or 'Not provided'}"
        )
        
        # Format products
        products_section = self._format_products(products)
        
        # Build report prompt
        prompt = self._build_report_prompt(
            obd2_analysis=obd2_analysis,
            car_info=car_info,
            products_section=products_section
        )
        
        # Generate report
        print("[Technical Writer] Generating comprehensive report...")
        messages = [
            SystemMessage(content="You are a professional automotive technical writer."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        draft_report = response.content

        # Debug output for tests: show technical writer draft
        print("\n" + "-" * 60)
        print("Technical Writer Agent - Draft Report")
        print("-" * 60 + "\n")
        print(draft_report)
        print("\n" + "-" * 60 + "\n")
        
        return {
            "draft_report": draft_report
        }


# Node function for LangGraph
def technical_writer_node(state: WriterState) -> Dict[str, Any]:
    """Node function for Technical Writer agent.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    agent = TechnicalWriterAgent()
    return agent.execute(state)

