"""Memory management tools."""
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from src.memory.user_memory import memory_manager
from src.states.obd2_state import CarMetadata


@tool
def load_user_profile(user_id: str) -> str:
    """Load user profile and car information.
    
    Args:
        user_id: User identifier
        
    Returns:
        Formatted user profile information
    """
    profile = memory_manager.load_user_profile(user_id)
    
    if profile:
        return (
            f"User Profile for {user_id}:\n"
            f"Car: {profile.car_name} {profile.car_model}\n"
            f"Year: {profile.year}\n"
            f"Mileage: {profile.mileage:,} miles\n"
            f"VIN: {profile.vin or 'Not provided'}"
        )
    else:
        return f"No profile found for user {user_id}."


@tool
def save_user_profile_tool(user_id: str, car_data: Dict[str, Any]) -> str:
    """Save or update user profile.
    
    Args:
        user_id: User identifier
        car_data: Dictionary with car metadata
        
    Returns:
        Success message
    """
    try:
        metadata = CarMetadata(**car_data)
        success = memory_manager.save_user_profile(user_id, metadata)
        
        if success:
            return f"Profile saved successfully for user {user_id}."
        else:
            return f"Failed to save profile for user {user_id}."
    except Exception as e:
        return f"Error saving profile: {str(e)}"


@tool
def get_conversation_history(user_id: str, limit: int = 5) -> str:
    """Get recent conversation history for a user.
    
    Args:
        user_id: User identifier
        limit: Number of recent interactions to retrieve
        
    Returns:
        Formatted conversation history
    """
    history = memory_manager.load_conversation_history(user_id, limit=limit)
    
    if not history:
        return f"No conversation history found for user {user_id}."
    
    formatted = [f"Recent conversation history for {user_id}:"]
    
    for i, interaction in enumerate(history, 1):
        timestamp = interaction.get('timestamp', 'Unknown time')
        summary = interaction.get('summary', 'No summary')
        formatted.append(f"\n[Interaction {i}] {timestamp}\n{summary}")
    
    return "\n".join(formatted)


def save_interaction(user_id: str, interaction_data: Dict[str, Any]) -> bool:
    """Save an interaction to user history.
    
    Args:
        user_id: User identifier
        interaction_data: Dictionary with interaction details
        
    Returns:
        True if successful, False otherwise
    """
    return memory_manager.append_to_history(user_id, interaction_data)


def get_user_context(user_id: str) -> Dict[str, Any]:
    """Get complete user context (profile + recent history).
    
    Args:
        user_id: User identifier
        
    Returns:
        Dictionary with user context
    """
    profile = memory_manager.load_user_profile(user_id)
    history = memory_manager.load_conversation_history(user_id, limit=3)
    
    return {
        "user_id": user_id,
        "profile": profile.model_dump() if profile else None,
        "recent_history": history,
        "has_profile": profile is not None,
        "interaction_count": len(history)
    }

