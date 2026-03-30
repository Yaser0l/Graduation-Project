"""User memory management system."""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.states.obd2_state import CarMetadata
import config


class UserMemoryManager:
    """Manages user profiles and conversation history."""

    def __init__(self, base_path: Optional[str] = None):
        """Initialize the memory manager.
        
        Args:
            base_path: Base path for storing user data. Defaults to config.USER_DATA_PATH
        """
        self.base_path = Path(base_path or config.USER_DATA_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: str) -> Path:
        """Get the directory for a specific user."""
        user_dir = self.base_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_profile_path(self, user_id: str) -> Path:
        """Get the path to user's profile file."""
        return self._get_user_dir(user_id) / "profile.json"

    def _get_history_path(self, user_id: str) -> Path:
        """Get the path to user's history file."""
        return self._get_user_dir(user_id) / "history.json"

    def load_user_profile(self, user_id: str) -> Optional[CarMetadata]:
        """Load user profile from storage.
        
        Args:
            user_id: User identifier
            
        Returns:
            CarMetadata if profile exists, None otherwise
        """
        profile_path = self._get_profile_path(user_id)
        
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return CarMetadata(**data)
        except Exception as e:
            print(f"Error loading user profile: {e}")
            return None

    def save_user_profile(self, user_id: str, metadata: CarMetadata) -> bool:
        """Save user profile to storage.
        
        Args:
            user_id: User identifier
            metadata: Car metadata to save
            
        Returns:
            True if successful, False otherwise
        """
        profile_path = self._get_profile_path(user_id)
        
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.model_dump(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving user profile: {e}")
            return False

    def load_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Load conversation history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of interactions to return
            
        Returns:
            List of conversation interactions
        """
        history_path = self._get_history_path(user_id)
        
        if not history_path.exists():
            return []
        
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
                # Return the most recent interactions
                return history[-limit:] if len(history) > limit else history
        except Exception as e:
            print(f"Error loading conversation history: {e}")
            return []

    def append_to_history(self, user_id: str, interaction: Dict[str, Any]) -> bool:
        """Append an interaction to user's conversation history.
        
        Args:
            user_id: User identifier
            interaction: Dictionary containing interaction data
            
        Returns:
            True if successful, False otherwise
        """
        history_path = self._get_history_path(user_id)
        
        # Add timestamp if not present
        if 'timestamp' not in interaction:
            interaction['timestamp'] = datetime.now().isoformat()
        
        try:
            # Load existing history
            history = []
            if history_path.exists():
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # Append new interaction
            history.append(interaction)
            
            # Save updated history
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error appending to conversation history: {e}")
            return False

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's interaction history.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with user statistics
        """
        history = self.load_conversation_history(user_id, limit=None)
        profile = self.load_user_profile(user_id)
        
        return {
            "user_id": user_id,
            "total_interactions": len(history),
            "has_profile": profile is not None,
            "car_info": profile.model_dump() if profile else None,
            "last_interaction": history[-1]['timestamp'] if history else None
        }

    def clear_user_history(self, user_id: str) -> bool:
        """Clear conversation history for a user (keeps profile).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        history_path = self._get_history_path(user_id)
        
        try:
            if history_path.exists():
                history_path.unlink()
            return True
        except Exception as e:
            print(f"Error clearing conversation history: {e}")
            return False


# Global instance
memory_manager = UserMemoryManager()

