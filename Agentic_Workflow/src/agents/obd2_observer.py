"""OBD2 Observer Agent for review and quality control."""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.states.obd2_state import OBD2State
import config


class OBD2ObserverAgent:
    """Agent that reviews and validates OBD2 analysis quality."""
    
    def __init__(self):
        """Initialize the OBD2 Observer agent."""
        agent_config = config.AGENT_MODELS["obd2_observer"]
        llm_params = {
            "model": agent_config["model"],
            "temperature": agent_config["temperature"],
            "api_key": config.OPENAI_API_KEY
        }
        if config.base_url:
            llm_params["base_url"] = config.base_url
        self.llm = ChatOpenAI(**llm_params)
    
    def _build_review_prompt(
        self,
        analysis_draft: str,
        obd2_data: Dict[str, Any],
        context_used: list
    ) -> str:
        """Build the prompt for reviewing analysis.
        
        Args:
            analysis_draft: The analysis to review
            obd2_data: Original OBD2 data
            context_used: Context that was used for analysis
            
        Returns:
            Review prompt
        """
        diagnostic_codes = obd2_data.get("diagnostic_codes", [])
        codes_list = ", ".join([code.get("code", "") for code in diagnostic_codes])
        
        return f"""You are a senior automotive diagnostic supervisor reviewing a technician's analysis.

ORIGINAL DIAGNOSTIC CODES:
{codes_list}

TECHNICIAN'S ANALYSIS:
{analysis_draft}

REVIEW CRITERIA:
Evaluate the analysis on these dimensions:

1. **Completeness**: Are all diagnostic codes addressed?
2. **Technical Accuracy**: Is the technical information correct?
3. **Clarity**: Is the explanation clear and well-structured?
4. **Actionability**: Does it provide clear next steps?
5. **Use of Context**: Did the technician properly use reference materials?

TASK:
Provide a structured review in the following format:

APPROVAL STATUS: [APPROVED / NEEDS_REVISION]

STRENGTHS:
- [List strengths of the analysis]

ISSUES (if any):
- [List any problems or missing elements]

SPECIFIC REVISIONS NEEDED (if NEEDS_REVISION):
- [Specific, actionable feedback for improvement]

OVERALL ASSESSMENT:
[Brief summary of your evaluation]

Your review:"""
    
    def execute(self, state: OBD2State) -> Dict[str, Any]:
        """Execute the OBD2 Observer agent.
        
        Args:
            state: Current OBD2 state
            
        Returns:
            Updated state dictionary
        """
        # Extract data from state
        analysis_draft = state.get("analysis_draft", "")
        obd2_data = state["obd2_data"]
        context_used = state.get("retrieved_context", [])
        
        if not analysis_draft:
            return {
                "analysis_review": "ERROR: No analysis draft to review.",
                "final_analysis": None
            }
        
        # Build review prompt
        prompt = self._build_review_prompt(
            analysis_draft=analysis_draft,
            obd2_data=obd2_data,
            context_used=context_used
        )
        
        # Generate review
        print("[OBD2 Observer] Reviewing analysis...")
        messages = [
            SystemMessage(content="You are a senior automotive diagnostic supervisor."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        review = response.content

        # Debug output for tests: show observer review
        print("\n" + "-" * 60)
        print("OBD2 Observer Agent - Review")
        print("-" * 60 + "\n")
        print(review)
        print("\n" + "-" * 60 + "\n")
        
        # Determine if analysis is approved
        is_approved = "APPROVED" in review.split("\n")[0] and "NEEDS_REVISION" not in review.split("\n")[0]
        
        print(f"[OBD2 Observer] Review complete. Approved: {is_approved}")
        
        # If approved, set as final analysis
        final_analysis = analysis_draft if is_approved else None
        
        return {
            "analysis_review": review,
            "final_analysis": final_analysis
        }


def should_revise(state: OBD2State) -> str:
    """Conditional edge function to determine if revision is needed.
    
    Args:
        state: Current state
        
    Returns:
        'approved' or 'revise'
    """
    revision_count = state.get("revision_count", 0)
    final_analysis = state.get("final_analysis")
    
    # If we have final analysis, it's approved
    if final_analysis:
        return "approved"
    
    # If we've exceeded revision limit, force approval
    if revision_count >= 3:
        print(f"[OBD2 Observer] Max revisions ({revision_count}) reached, forcing approval")
        return "force_approve"
    
    # Otherwise, needs revision
    return "revise"


# Node function for LangGraph
def obd2_observer_node(state: OBD2State) -> Dict[str, Any]:
    """Node function for OBD2 Observer agent.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    agent = OBD2ObserverAgent()
    result = agent.execute(state)
    
    # Increment revision count if not approved
    if not result.get("final_analysis"):
        result["revision_count"] = state.get("revision_count", 0) + 1
    
    return result


def force_approve_node(state: OBD2State) -> Dict[str, Any]:
    """Force approve the current draft when max revisions reached.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    return {
        "final_analysis": state.get("analysis_draft", "Analysis completed with maximum revisions."),
        "analysis_review": "Force approved after maximum revision cycles."
    }

