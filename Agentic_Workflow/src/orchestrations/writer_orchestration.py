"""Writer Orchestration layer - coordinates report generation workflow."""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.states.writer_state import WriterState
from src.agents.product_researcher import product_researcher_node
from src.agents.technical_writer import technical_writer_node
from src.agents.formatter import formatter_node
from src.memory.user_memory import memory_manager


def save_report_node(state: WriterState) -> Dict[str, Any]:
    """Save the final report to user memory.
    
    Args:
        state: Current state
        
    Returns:
        Empty dict (state already has final_report)
    """
    user_id = state["user_id"]
    final_report = state.get("final_report", "")
    
    if final_report:
        # Save to conversation history
        interaction = {
            "type": "final_report",
            "summary": "Complete diagnostic report generated",
            "report_preview": final_report[:300] + "..." if len(final_report) > 300 else final_report,
            "has_products": bool(state.get("product_recommendations"))
        }
        
        memory_manager.append_to_history(user_id, interaction)
        print(f"[Writer Orchestration] Saved report to memory for user {user_id}")
    
    return {}


def create_writer_orchestration_graph() -> StateGraph:
    """Create the Writer orchestration graph.
    
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(WriterState)
    
    # Add nodes
    workflow.add_node("product_researcher", product_researcher_node)
    workflow.add_node("technical_writer", technical_writer_node)
    workflow.add_node("formatter", formatter_node)
    workflow.add_node("save_report", save_report_node)
    
    # Set entry point
    workflow.set_entry_point("product_researcher")
    
    # Add edges (linear flow)
    workflow.add_edge("product_researcher", "technical_writer")
    workflow.add_edge("technical_writer", "formatter")
    workflow.add_edge("formatter", "save_report")
    workflow.add_edge("save_report", END)
    
    # Compile graph
    return workflow.compile()


# Create singleton instance
writer_orchestration = create_writer_orchestration_graph()

