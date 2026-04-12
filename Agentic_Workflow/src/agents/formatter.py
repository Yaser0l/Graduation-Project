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
    
    def _normalize_language(self, value: str) -> str:
        """Normalize incoming language preference to supported values."""
        if not value:
            return "en"
        lowered = str(value).strip().lower()
        return "ar" if lowered.startswith("ar") else "en"

    def _build_format_prompt(self, draft_report: str, car_info: str, report_language: str) -> str:
        """Build the prompt for formatting.
        
        Args:
            draft_report: Technical draft report
            car_info: Car information
            report_language: Target report language (en/ar)
            
        Returns:
            Formatting prompt
        """
        is_arabic = report_language == "ar"
        output_language_label = "Arabic" if is_arabic else "English"
        header_title = "تقرير التشخيص" if is_arabic else "DIAGNOSTIC REPORT"
        section_found = "ما الذي وجدناه" if is_arabic else "WHAT WE FOUND"
        section_urgency = "مستوى الخطورة" if is_arabic else "URGENCY LEVEL"
        section_findings = "النتائج التفصيلية" if is_arabic else "DETAILED FINDINGS"
        section_actions = "الإجراءات الموصى بها" if is_arabic else "RECOMMENDED ACTIONS"
        section_products = "المنتجات الموصى بها" if is_arabic else "RECOMMENDED PRODUCTS"
        section_cost = "تقدير التكلفة" if is_arabic else "COST ESTIMATE"
        section_safety = "معلومات السلامة" if is_arabic else "SAFETY INFORMATION"
        section_next = "الخطوات التالية" if is_arabic else "NEXT STEPS"
        vehicle_label = "المركبة" if is_arabic else "Vehicle"
        date_label = "تاريخ التقرير" if is_arabic else "Report Date"
        p1_label = "الأولوية 1 (نفذ أولاً)" if is_arabic else "Priority 1 (Do First)"
        p2_label = "الأولوية 2 (نفذ قريباً)" if is_arabic else "Priority 2 (Do Soon)"
        tips_label = "نصائح صيانة" if is_arabic else "Maintenance Tips"

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

LANGUAGE REQUIREMENTS:
- Output the entire report in {output_language_label}.
- Translate all section titles, labels, and bullet text into {output_language_label}.
- Keep diagnostic codes, VIN values, product names, and URLs unchanged.
- Keep the exact section order and separator style shown below.

FORMAT YOUR RESPONSE AS:

━━━━━━━━━━━━━
{header_title}
━━━━━━━━━━━━━

{vehicle_label}: [car info]
{date_label}: [current date]

━━━━━━━━━━━━━
{section_found}
━━━━━━━━━━━━━

[Brief, clear summary of issues in plain language]

━━━━━━━━━━━━━
{section_urgency}
━━━━━━━━━━━━━

[Critical/High/Medium/Low with explanation]

━━━━━━━━━━━━
{section_findings}
━━━━━━━━━━━━

[Clear explanation of each issue with:
 • What it is (in plain language)
 • Why it happened
 • What it affects
 • What needs to be done]

━━━━━━━━━━━━
{section_actions}
━━━━━━━━━━━━

{p1_label}:
• [action items]

{p2_label}:
• [action items]

{tips_label}:
• [preventive recommendations]

━━━━━━━━━━━━━
{section_products}
━━━━━━━━━━━━━

[List products with links and brief explanations]

━━━━━━━━━━━━━
{section_cost}
━━━━━━━━━━━━━

[Estimated costs if available]

━━━━━━━━━━━━━
{section_safety}
━━━━━━━━━━━━━

[Any safety concerns or driving restrictions]

━━━━━━━━━━━━━
{section_next}
━━━━━━━━━━━━━

1. [First step]
2. [Second step]
3. [Third step]

━━━━━━━━━━━━━

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
        report_language = self._normalize_language(state.get("language", "en"))
        
        if not draft_report:
            return {
                "user_friendly_report": "Error: No draft report to format.",
                "final_report": "Error: No draft report available."
            }
        
        # Format car information
        car_info = f"{car_metadata.year} {car_metadata.car_name} {car_metadata.car_model}"
        
        # Build format prompt
        prompt = self._build_format_prompt(draft_report, car_info, report_language)
        
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

