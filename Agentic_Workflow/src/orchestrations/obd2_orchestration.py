"""OBD2 Orchestration layer - coordinates OBD2 analysis workflow."""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.states.obd2_state import OBD2State
from src.agents.obd2_writer import obd2_writer_node
from src.agents.obd2_observer import obd2_observer_node, should_revise, force_approve_node
from src.memory.user_memory import memory_manager
from src.tools.memory_tools import get_user_context


def load_user_memory_node(state: OBD2State) -> Dict[str, Any]:
    """Load user memory and context.
    
    Args:
        state: Current state
        
    Returns:
        Updated state with user context
    """
    user_id = state["user_id"]
    print(f"[OBD2 Orchestration] Loading memory for user: {user_id}")
    
    # Get user context
    context = get_user_context(user_id)
    
    # If profile exists, update car metadata
    if context.get("profile"):
        print(f"[OBD2 Orchestration] Found existing profile for user {user_id}")
    else:
        print(f"[OBD2 Orchestration] No existing profile for user {user_id}")
    
    return {}


def save_analysis_node(state: OBD2State) -> Dict[str, Any]:
    """Save the final analysis to user memory.
    
    Args:
        state: Current state
        
    Returns:
        Empty dict (state already has final_analysis)
    """
    user_id = state["user_id"]
    final_analysis = state.get("final_analysis", "")
    
    if final_analysis:
        # Save to conversation history
        interaction = {
            "type": "obd2_analysis",
            "summary": "OBD2 diagnostic analysis completed",
            "analysis": final_analysis[:500] + "..." if len(final_analysis) > 500 else final_analysis,
            "codes": [code.get("code", "") for code in state["obd2_data"].get("diagnostic_codes", [])]
        }
        
        memory_manager.append_to_history(user_id, interaction)
        print(f"[OBD2 Orchestration] Saved analysis to memory for user {user_id}")
    
    return {}


def create_obd2_orchestration_graph() -> StateGraph:
    """Create the OBD2 orchestration graph.
    
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(OBD2State)
    
    # Add nodes
    workflow.add_node("load_memory", load_user_memory_node)
    workflow.add_node("writer", obd2_writer_node)
    workflow.add_node("observer", obd2_observer_node)
    workflow.add_node("force_approve", force_approve_node)
    workflow.add_node("save_analysis", save_analysis_node)
    
    # Set entry point
    workflow.set_entry_point("load_memory")
    
    # Add edges
    workflow.add_edge("load_memory", "writer")
    workflow.add_edge("writer", "observer")
    
    # Conditional edge from observer
    workflow.add_conditional_edges(
        "observer",
        should_revise,
        {
            "approved": "save_analysis",
            "revise": "writer",  # Loop back to writer for revision
            "force_approve": "force_approve"
        }
    )
    
    workflow.add_edge("force_approve", "save_analysis")
    workflow.add_edge("save_analysis", END)
    
    # Compile graph
    return workflow.compile()


# Create singleton instance
obd2_orchestration = create_obd2_orchestration_graph()

