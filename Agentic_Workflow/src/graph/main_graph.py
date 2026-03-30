"""Main LangGraph workflow integrating all components."""
from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from src.states.obd2_state import OBD2State, CarMetadata
from src.states.writer_state import WriterState
from src.orchestrations.obd2_orchestration import obd2_orchestration
from src.orchestrations.writer_orchestration import writer_orchestration
from src.router import validate_input
from src.memory.user_memory import memory_manager


class MainState(TypedDict):
    """Main state for the entire workflow."""
    # Input fields
    user_id: str
    car_metadata: CarMetadata
    obd2_data: Dict[str, Any]
    
    # Validation
    is_valid: bool
    validation_errors: list
    
    # OBD2 orchestration results
    obd2_analysis: str
    
    # Writer orchestration results
    final_report: str
    
    # Messages
    messages: Annotated[list[BaseMessage], add_messages]


def initialize_node(state: MainState) -> Dict[str, Any]:
    """Initialize the workflow.
    
    Args:
        state: Input state
        
    Returns:
        Initialized state
    """
    print("=" * 60)
    print("MULTI-AGENT MECHANIC WORKFLOW STARTING")
    print("=" * 60)
    print(f"User ID: {state.get('user_id', 'Unknown')}")
    car_meta = state.get("car_metadata")
    car_name = getattr(car_meta, "car_name", car_meta.get("car_name") if isinstance(car_meta, dict) else "Unknown")
    print(f"Vehicle: {car_name}")
    print("=" * 60)
    
    # Validate input
    validation_result = validate_input(state)
    
    # Initialize message history if not present
    if "messages" not in state:
        return {**validation_result, "messages": []}
    
    return validation_result


def should_continue_to_obd2(state: MainState) -> str:
    """Conditional edge to check if we should continue to OBD2 orchestration.
    
    Args:
        state: Current state
        
    Returns:
        Next node name
    """
    if not state.get("is_valid", False):
        return "error"
    return "obd2_orchestration"


def obd2_orchestration_node(state: MainState) -> Dict[str, Any]:
    """Execute OBD2 orchestration.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    print("\n" + "=" * 60)
    print("OBD2 ORCHESTRATION LAYER")
    print("=" * 60)
    
    # Prepare OBD2 state
    obd2_state: OBD2State = {
        "user_id": state["user_id"],
        "car_metadata": state["car_metadata"],
        "obd2_data": state["obd2_data"],
        "retrieved_context": [],
        "web_search_results": None,
        "analysis_draft": None,
        "analysis_review": None,
        "final_analysis": None,
        "reflection_count": 0,
        "revision_count": 0,
        "messages": state.get("messages", [])
    }
    
    # Run OBD2 orchestration
    result = obd2_orchestration.invoke(obd2_state)
    
    # Extract final analysis
    final_analysis = result.get("final_analysis", "")
    
    if not final_analysis:
        final_analysis = result.get("analysis_draft", "Error: No analysis generated")
    
    print(f"\nOBD2 Analysis Complete ({len(final_analysis)} characters)")
    
    return {
        "obd2_analysis": final_analysis,
        "messages": result.get("messages", [])
    }


def writer_orchestration_node(state: MainState) -> Dict[str, Any]:
    """Execute Writer orchestration.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    print("\n" + "=" * 60)
    print("WRITER ORCHESTRATION LAYER")
    print("=" * 60)
    
    # Prepare Writer state
    writer_state: WriterState = {
        "user_id": state["user_id"],
        "car_metadata": state["car_metadata"],
        "obd2_analysis": state["obd2_analysis"],
        "product_recommendations": None,
        "draft_report": None,
        "technical_review": None,
        "user_friendly_report": None,
        "final_report": "",
        "messages": state.get("messages", [])
    }
    
    # Run Writer orchestration
    result = writer_orchestration.invoke(writer_state)
    
    # Extract final report
    final_report = result.get("final_report", "Error: No report generated")
    
    print(f"\nFinal Report Complete ({len(final_report)} characters)")
    
    return {
        "final_report": final_report,
        "messages": result.get("messages", [])
    }


def finalize_node(state: MainState) -> Dict[str, Any]:
    """Finalize the workflow.
    
    Args:
        state: Current state
        
    Returns:
        Final state
    """
    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETE")
    print("=" * 60)
    print(f"User ID: {state['user_id']}")
    print(f"Report Length: {len(state.get('final_report', ''))} characters")
    print("=" * 60)
    
    # Save user profile if new
    user_id = state["user_id"]
    car_metadata = state["car_metadata"]
    
    existing_profile = memory_manager.load_user_profile(user_id)
    if not existing_profile:
        memory_manager.save_user_profile(user_id, car_metadata)
        print(f"Saved new profile for user {user_id}")
    
    return {}


def error_node(state: MainState) -> Dict[str, Any]:
    """Handle errors.
    
    Args:
        state: Current state
        
    Returns:
        Error state
    """
    errors = state.get("validation_errors", ["Unknown error"])
    error_message = "ERROR: " + "; ".join(errors)
    
    print("\n" + "=" * 60)
    print("WORKFLOW ERROR")
    print("=" * 60)
    print(error_message)
    print("=" * 60)
    
    return {
        "final_report": error_message
    }


def create_main_graph() -> StateGraph:
    """Create the main workflow graph.
    
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(MainState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("obd2_orchestration", obd2_orchestration_node)
    workflow.add_node("writer_orchestration", writer_orchestration_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("error", error_node)
    
    # Set entry point
    workflow.set_entry_point("initialize")
    
    # Add edges
    workflow.add_conditional_edges(
        "initialize",
        should_continue_to_obd2,
        {
            "obd2_orchestration": "obd2_orchestration",
            "error": "error"
        }
    )
    
    workflow.add_edge("obd2_orchestration", "writer_orchestration")
    workflow.add_edge("writer_orchestration", "finalize")
    workflow.add_edge("finalize", END)
    workflow.add_edge("error", END)
    
    # Compile graph
    return workflow.compile()


# Create singleton instance
main_workflow = create_main_graph()

