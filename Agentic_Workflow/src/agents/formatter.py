"""Formatter Agent for creating user-friendly reports."""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.states.writer_state import WriterState
import config


class FormatterAgent:
    """Agent that formats technical reports into user-friendly language."""
    
    def __init__(self):
        """Initialize the Formatter agent."""
        agent_config = config.AGENT_MODELS["formatter"]
        llm_params = {
            "model": agent_config["model"],
            "temperature": agent_config["temperature"],
            "api_key": config.OPENAI_API_KEY
        }
        if config.base_url:
            llm_params["base_url"] = config.base_url
        self.llm = ChatOpenAI(**llm_params)
    
    def _build_format_prompt(self, draft_report: str, car_info: str) -> str:
        """Build the prompt for formatting.
        
        Args:
            draft_report: Technical draft report
            car_info: Car information
            
        Returns:
            Formatting prompt
        """
        return f"""You are formatting a technical automotive report for a customer who may not have technical expertise.

VEHICLE:
{car_info}

TECHNICAL REPORT:
{draft_report}

TASK:
Transform this technical report into a user-friendly format that:

1. Uses plain language instead of jargon (explain technical terms when needed)
2. Is easy to scan with clear headers and bullet points
3. Highlights important information (safety issues, costs, urgency)
4. Is empathetic and helpful in tone
5. Provides clear next steps

FORMAT YOUR RESPONSE AS:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIAGNOSTIC REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vehicle: [car info]
Report Date: [current date]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT WE FOUND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Brief, clear summary of issues in plain language]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URGENCY LEVEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Critical/High/Medium/Low with explanation]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETAILED FINDINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Clear explanation of each issue with:
 • What it is (in plain language)
 • Why it happened
 • What it affects
 • What needs to be done]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDED ACTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Priority 1 (Do First):
• [action items]

Priority 2 (Do Soon):
• [action items]

Maintenance Tips:
• [preventive recommendations]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDED PRODUCTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[List products with links and brief explanations]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COST ESTIMATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Estimated costs if available]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SAFETY INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Any safety concerns or driving restrictions]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [First step]
2. [Second step]
3. [Third step]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Make it friendly, clear, and actionable!

USER-FRIENDLY REPORT:"""
    
    def execute(self, state: WriterState) -> Dict[str, Any]:
        """Execute the Formatter agent.
        
        Args:
            state: Current writer state
            
        Returns:
            Updated state dictionary
        """
        # Extract data from state
        draft_report = state.get("draft_report", "")
        car_metadata = state["car_metadata"]
        
        if not draft_report:
            return {
                "user_friendly_report": "Error: No draft report to format.",
                "final_report": "Error: No draft report available."
            }
        
        # Format car information
        car_info = f"{car_metadata.year} {car_metadata.car_name} {car_metadata.car_model}"
        
        # Build format prompt
        prompt = self._build_format_prompt(draft_report, car_info)
        
        # Generate formatted report
        print("[Formatter] Creating user-friendly report...")
        messages = [
            SystemMessage(content="You are an expert at making technical information accessible to everyone."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        user_friendly_report = response.content

        # Debug output for tests: show formatter final user-friendly report
        print("\n" + "-" * 60)
        print("Formatter Agent - User-Friendly Report")
        print("-" * 60 + "\n")
        print(user_friendly_report)
        print("\n" + "-" * 60 + "\n")
        
        return {
            "user_friendly_report": user_friendly_report,
            "final_report": user_friendly_report
        }


# Node function for LangGraph
def formatter_node(state: WriterState) -> Dict[str, Any]:
    """Node function for Formatter agent.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    agent = FormatterAgent()
    return agent.execute(state)

