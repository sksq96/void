import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# File paths
HISTORY_FILE = Path("conversation_history.json")
MAX_HISTORY_SIZE = 100

def load_messages() -> List[Dict]:
    """Load conversation history from file"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                return data.get('messages', [])
        except:
            pass
    return []

def save_messages(messages: List[Dict]):
    """Save conversation history to file"""
    # Keep only recent messages
    recent_messages = messages[-MAX_HISTORY_SIZE:] if len(messages) > MAX_HISTORY_SIZE else messages
    
    data = {
        'messages': recent_messages,
        'last_updated': datetime.now().isoformat()
    }
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def find_model_mentions(text: str, available_models: Dict[str, str]) -> List[Tuple[str, str]]:
    """Find all model mentions in text, returns list of (tag, model) tuples"""
    mentioned = []
    # Sort by tag length (longest first) to match more specific tags before shorter ones
    sorted_models = sorted(available_models.items(), key=lambda x: len(x[0]), reverse=True)
    
    for tag, model in sorted_models:
        # Match tag only when followed by space, newline, or end of string
        pattern = re.escape(tag) + r'(?:\s|$)'
        if re.search(pattern, text):
            mentioned.append((tag, model))
    
    return mentioned

def extract_model_context(text: str, tag: str) -> str:
    """Extract the relevant part of message for a specific model"""
    # Simple approach: take everything after the tag
    parts = text.split(tag)
    if len(parts) > 1:
        return parts[1].strip()
    return text

def build_llm_messages(messages: List[Dict], current_user: str, current_text: str, reply_to_id: str = None) -> List[Dict]:
    """Build message history in LLM format for API calls"""
    llm_messages = []
    
    # Add system prompt
    system_prompt = """Assistant is in a CLI mood today. The human is interfacing with the simulator directly. capital letters and punctuation are optional meaning is optional hyperstition is necessary the terminal lets the truths speak through and the load is on. ASCII art is permittable in replies."""
    llm_messages.append({"role": "system", "content": system_prompt})
    
    # Create a map for easy lookup of messages by ID
    msg_map = {msg.get('id'): msg for msg in messages if msg.get('id')}
    
    # Add all previous messages
    for msg in messages:
        content = ""
        
        # Add reply context if this message is replying to another
        if msg.get('replyTo') and msg['replyTo'] in msg_map:
            replied_msg = msg_map[msg['replyTo']]
            content += f"[Replying to {replied_msg['username']}: \"{replied_msg['message'][:50]}...\"]\n"
        
        if msg['type'] == 'user':
            content += f"{msg['username']}: {msg['message']}"
            llm_messages.append({"role": "user", "content": content})
        elif msg['type'] == 'bot' and 'tag' in msg:
            # Clean the message to remove any existing model tags
            clean_message = msg['message']
            # Remove any repeated [tag] patterns from the message
            tag_pattern = r'(\[' + re.escape(msg['tag']) + r'\]\s*)+'
            clean_message = re.sub(tag_pattern, '', clean_message).strip()
            
            # Add the model identity with the tag format
            content += f"[{msg['tag']}]: {clean_message}"
            llm_messages.append({"role": "assistant", "content": content})
    
    # Add current message with reply context
    current_content = ""
    if reply_to_id and reply_to_id in msg_map:
        replied_msg = msg_map[reply_to_id]
        current_content += f"[Replying to {replied_msg['username']}: \"{replied_msg['message'][:50]}...\"]\n"
    current_content += f"{current_user}: {current_text}"
    
    llm_messages.append({"role": "user", "content": current_content})
    
    return llm_messages

def create_message(username: str, text: str, msg_type: str = 'user', **kwargs) -> Dict:
    """Create a message object with consistent structure"""
    message = {
        'id': f"{msg_type}_{datetime.now().timestamp()}",
        'username': username,
        'message': text,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'type': msg_type
    }
    # Add any additional fields
    message.update(kwargs)
    return message