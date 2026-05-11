"""OBD2 Writer Agent with Retrieve-Reflect-Retry pattern."""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.states.obd2_state import OBD2State
from src.tools.rag_tool import retrieve_with_reflection
from src.tools.tavily_tool import search_technical_info
from src.tools.obd2_parser import format_obd2_summary, analyze_sensor_readings
import config


class OBD2WriterAgent:
    """Agent that writes technical analysis of OBD2 data using Retrieve-Reflect-Retry."""
    
    def __init__(self):
        """Initialize the OBD2 Writer agent."""
        agent_config = config.AGENT_MODELS["obd2_writer"]
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
        self.max_retry_cycles = config.MAX_RETRY_CYCLES
    
    def _retrieve_knowledge(self, query: str) -> Dict[str, Any]:
        """Retrieve knowledge with reflection (Retrieve-Reflect step).
        
        Args:
            query: Search query
            
        Returns:
            Dictionary with retrieval results and reflection
        """
        # StructuredTool requires invocation with named arguments
        return retrieve_with_reflection.invoke({"query": query, "top_k": config.RAG_TOP_K})
    
    def _search_web_fallback(self, query: str) -> str:
        """Search web when RAG is insufficient (Retry step).
        
        Args:
            query: Search query
            
        Returns:
            Web search results
        """
        return search_technical_info(query)
    
    def _build_analysis_prompt(
        self,
        obd2_summary: str,
        sensor_analysis: str,
        context: str,
        car_info: str,
        user_history: str
    ) -> str:
        """Build the prompt for analysis generation.
        
        Args:
            obd2_summary: Summary of OBD2 data
            sensor_analysis: Analysis of sensor readings
            context: Retrieved context from RAG/web
            car_info: Car metadata
            user_history: User conversation history
            
        Returns:
            Complete prompt
        """
        return f"""You are an expert automotive diagnostic technician. Analyze the following OBD2 diagnostic data and provide a comprehensive technical analysis.

CAR INFORMATION:
{car_info}

USER HISTORY:
{user_history}

OBD2 DIAGNOSTIC DATA:
{obd2_summary}

SENSOR ANALYSIS:
{sensor_analysis}

REFERENCE INFORMATION:
{context}

TASK:
Provide a detailed technical analysis that includes:
1. **Problem Identification**: Clearly identify all issues based on diagnostic codes
2. **Root Cause Analysis**: Explain the likely causes of each issue
3. **System Impact**: Describe how these issues affect vehicle systems
4. **Severity Assessment**: Rate the urgency (Critical, High, Medium, Low)
5. **Technical Details**: Include relevant technical information from the reference material
6. **Preliminary Recommendations**: Suggest diagnostic steps or repairs needed

Be specific, technical, and accurate. Reference the car's history if relevant. Use the provided reference information to support your analysis.

TECHNICAL ANALYSIS:"""
    
    def execute(self, state: OBD2State) -> Dict[str, Any]:
        """Execute the OBD2 Writer agent with Retrieve-Reflect-Retry pattern.
        
        Args:
            state: Current OBD2 state
            
        Returns:
            Updated state dictionary
        """
        # Extract data from state
        obd2_data = state["obd2_data"]
        car_metadata = state["car_metadata"]
        user_id = state["user_id"]
        reflection_count = state.get("reflection_count", 0)
        
        # Format OBD2 data
        obd2_summary = format_obd2_summary(obd2_data)
        # StructuredTool requires invocation with named arguments
        sensor_analysis = analyze_sensor_readings.invoke({"obd2_data": obd2_data})
        
        # Format car information
        car_info = f"{car_metadata.year} {car_metadata.car_name} {car_metadata.car_model}, {car_metadata.mileage:,} miles"
        
        # User history (simplified for now)
        user_history = f"User ID: {user_id}\nPrevious interactions: See memory system"
        
        # Build query for knowledge retrieval
        diagnostic_codes = obd2_data.get("diagnostic_codes", [])
        code_strings = [code.get("code", "") for code in diagnostic_codes]
        query = f"OBD2 diagnostic codes {' '.join(code_strings)} causes repair solutions"
        
        # RETRIEVE-REFLECT-RETRY PATTERN
        context_parts = []
        web_search_results = []
        
        # RETRIEVE: Get information from RAG
        print(f"[OBD2 Writer] Retrieving knowledge for: {query}")
        retrieval_result = self._retrieve_knowledge(query)
        
        # REFLECT: Check if retrieval is sufficient
        is_sufficient = retrieval_result.get("is_sufficient", False)
        reflection_score = retrieval_result.get("score", 0.0)
        reflection_message = retrieval_result.get("reflection", "")
        
        print(f"[OBD2 Writer] Reflection - Sufficient: {is_sufficient}, Score: {reflection_score:.2f}")
        print(f"[OBD2 Writer] Reflection message: {reflection_message}")
        
        context_parts.append(retrieval_result.get("content", ""))
        
        # RETRY: If insufficient and haven't exceeded retry limit, search web
        if not is_sufficient and reflection_count < self.max_retry_cycles:
            print(f"[OBD2 Writer] RAG insufficient, performing web search (attempt {reflection_count + 1}/{self.max_retry_cycles})")
            
            web_results = self._search_web_fallback(query)
            if web_results:
                context_parts.append("\n--- WEB SEARCH RESULTS ---\n" + web_results)
                web_search_results.append(web_results)
            
            reflection_count += 1
        
        # Combine all context
        combined_context = "\n\n".join(context_parts)
        if len(combined_context) > config.MAX_CONTEXT_CHARS:
            combined_context = combined_context[:config.MAX_CONTEXT_CHARS]
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(
            obd2_summary=obd2_summary,
            sensor_analysis=sensor_analysis,
            context=combined_context,
            car_info=car_info,
            user_history=user_history
        )
        
        # Generate analysis
        print("[OBD2 Writer] Generating technical analysis...")
        messages = [
            SystemMessage(content="You are an expert automotive diagnostic technician."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        analysis_draft = response.content

        # Debug output for tests: show writer agent analysis
        print("\n" + "-" * 60)
        print("OBD2 Writer Agent - Analysis Draft")
        print("-" * 60 + "\n")
        print(analysis_draft)
        print("\n" + "-" * 60 + "\n")
        
        # Return updated state
        return {
            "retrieved_context": context_parts,
            "web_search_results": web_search_results if web_search_results else None,
            "analysis_draft": analysis_draft,
            "reflection_count": reflection_count
        }


# Node function for LangGraph
def obd2_writer_node(state: OBD2State) -> Dict[str, Any]:
    """Node function for OBD2 Writer agent.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    agent = OBD2WriterAgent()
    return agent.execute(state)

