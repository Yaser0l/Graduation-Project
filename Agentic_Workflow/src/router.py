"""Router for the multi-agent workflow."""
from typing import Dict, Any, Literal
from src.states.obd2_state import OBD2State


def route_request(state: Dict[str, Any]) -> Literal["obd2_orchestration", "error"]:
    """Route incoming requests to appropriate orchestration.
    
    Args:
        state: Current state
        
    Returns:
        Name of the next node to execute
    """
    # Check if we have OBD2 data
    if "obd2_data" in state and state["obd2_data"]:
        print("[Router] Routing to OBD2 orchestration")
        return "obd2_orchestration"
    
    # If we have an existing analysis, we could route to writer
    # (but in our flow, OBD2 always comes first)
    
    print("[Router] Invalid request - no OBD2 data found")
    return "error"


def validate_input(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input data.
    
    Args:
        state: Input state
        
    Returns:
        Updated state with validation results
    """
    errors = []
    
    # Check required fields
    if "user_id" not in state or not state["user_id"]:
        errors.append("Missing required field: user_id")
    
    if "car_metadata" not in state or not state["car_metadata"]:
        errors.append("Missing required field: car_metadata")
    
    if "obd2_data" not in state or not state["obd2_data"]:
        errors.append("Missing required field: obd2_data")
    
    # Check OBD2 data structure
    if "obd2_data" in state:
        obd2_data = state["obd2_data"]
        if "diagnostic_codes" not in obd2_data:
            errors.append("OBD2 data missing diagnostic_codes")
        elif not isinstance(obd2_data["diagnostic_codes"], list):
            errors.append("diagnostic_codes must be a list")
        elif len(obd2_data["diagnostic_codes"]) == 0:
            errors.append("No diagnostic codes provided")
    
    if errors:
        print(f"[Router] Validation errors: {errors}")
        return {"validation_errors": errors, "is_valid": False}
    
    print("[Router] Input validation passed")
    return {"is_valid": True}

