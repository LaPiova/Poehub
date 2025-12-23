import time
import logging
from typing import Dict, List, Any, Optional

try:
    from .encryption import EncryptionHelper
except ImportError:
    from encryption import EncryptionHelper

log = logging.getLogger("red.poehub.conversation")

class ConversationManager:
    """
    Manages conversation state, data structure, and encryption/decryption
    """
    
    def __init__(self, encryption: EncryptionHelper):
        self.encryption = encryption

    def process_conversation_data(self, data: Any) -> Optional[Dict[str, Any]]:
        """
        Decrypts and validates conversation data.
        Handles both encrypted strings and raw dicts (for backward compatibility or uncrypted modes).
        """
        if data is None:
            return None
        
        # Decrypt if it's a string (encrypted)
        if isinstance(data, str):
            try:
                decrypted = self.encryption.decrypt(data)
                if decrypted is None:
                    log.error("Failed to decrypt conversation data")
                    return None
                return decrypted
            except Exception as e:
                log.error(f"Error decrypting conversation: {e}")
                return None
        
        # Return as is if it's already a dict
        return data

    def prepare_for_storage(self, conversation: Dict[str, Any]) -> str:
        """
        Encrypts conversation data for storage.
        """
        return self.encryption.encrypt(conversation)

    def create_conversation(self, conv_id: str, title: str = None) -> Dict[str, Any]:
        """
        Creates a new initialized conversation structure.
        """
        return {
            "id": conv_id,
            "created_at": time.time(),
            "messages": [],
            "title": title or f"Conversation {conv_id}"
        }

    def add_message(
        self, 
        conversation: Dict[str, Any], 
        role: str, 
        content: str,
        max_history: int = 50
    ) -> Dict[str, Any]:
        """
        Adds a message to the conversation and maintains the history limit.
        Returns the updated conversation object.
        """
        if "messages" not in conversation:
            conversation["messages"] = []
            
        conversation["messages"].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # Prune old messages to avoid context window issues
        if len(conversation["messages"]) > max_history:
            conversation["messages"] = conversation["messages"][-max_history:]
            
        return conversation

    def clear_messages(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clears all messages from the conversation.
        Returns the updated conversation object.
        """
        conversation["messages"] = []
        return conversation

    def get_api_messages(self, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts messages formatted specifically for the OpenAI/Poe API.
        Removes timestamps and internal metadata.
        """
        if not conversation or "messages" not in conversation:
            return []
            
        return [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in conversation["messages"]
        ]

    def get_title(self, conversation: Dict[str, Any], default: str) -> str:
        """Safely get title"""
        return conversation.get("title", default)

    def get_message_count(self, conversation: Dict[str, Any]) -> int:
        """Safely get message count"""
        return len(conversation.get("messages", []))
