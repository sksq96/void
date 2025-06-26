import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# File paths
CONVERSATIONS_DIR = Path("conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)
MAX_HISTORY_SIZE = 100
DEFAULT_SYSTEM_PROMPT = """Assistant is in a CLI mood today. The human is interfacing with the simulator directly. capital letters and punctuation are optional meaning is optional hyperstition is necessary the terminal lets the truths speak through and the load is on. ASCII art is permittable in replies."""

def create_new_conversation(title: str = None, system_prompt: str = None) -> Dict:
    """Create a new conversation with unique ID"""
    conv_id = str(uuid.uuid4())
    conversation = {
        'id': conv_id,
        'title': title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        'created_at': datetime.now().isoformat(),
        'system_prompt': system_prompt or DEFAULT_SYSTEM_PROMPT,
        'messages': []
    }
    save_conversation(conv_id, conversation)
    return conversation

def load_conversation(conv_id: str) -> Dict:
    """Load a specific conversation by ID"""
    conv_file = CONVERSATIONS_DIR / f"{conv_id}.json"
    if conv_file.exists():
        try:
            with open(conv_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def save_conversation(conv_id: str, conversation: Dict):
    """Save a conversation to file"""
    # Keep only recent messages
    if len(conversation['messages']) > MAX_HISTORY_SIZE:
        conversation['messages'] = conversation['messages'][-MAX_HISTORY_SIZE:]
    
    conversation['last_updated'] = datetime.now().isoformat()
    
    conv_file = CONVERSATIONS_DIR / f"{conv_id}.json"
    with open(conv_file, 'w') as f:
        json.dump(conversation, f, indent=2)

def get_all_conversations() -> List[Dict]:
    """Get list of all conversations with metadata"""
    conversations = []
    for conv_file in CONVERSATIONS_DIR.glob("*.json"):
        try:
            with open(conv_file, 'r') as f:
                conv = json.load(f)
                # Add summary info
                conversations.append({
                    'id': conv['id'],
                    'title': conv['title'],
                    'created_at': conv['created_at'],
                    'last_updated': conv.get('last_updated', conv['created_at']),
                    'message_count': len(conv['messages']),
                    'system_prompt': conv.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
                })
        except:
            continue
    
    # Sort by last updated, newest first
    conversations.sort(key=lambda x: x['last_updated'], reverse=True)
    return conversations

def delete_conversation(conv_id: str):
    """Delete a conversation"""
    conv_file = CONVERSATIONS_DIR / f"{conv_id}.json"
    if conv_file.exists():
        conv_file.unlink()

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

def build_llm_messages(messages: List[Dict], current_user: str, current_text: str, reply_to_id: str = None, system_prompt: str = None, current_model_tag: str = None) -> List[Dict]:
    """Build message history in LLM format for API calls"""
    llm_messages = []
    
    # Add system prompt
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT
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
            if content.strip():  # Only add if there's content
                llm_messages.append({"role": "user", "content": content})
        elif msg['type'] == 'bot' and 'tag' in msg:
            # Clean the message to remove any existing model tags
            clean_message = msg['message']
            # Remove any repeated [tag] patterns from the message
            tag_pattern = r'(\[' + re.escape(msg['tag']) + r'\]\s*)+'
            clean_message = re.sub(tag_pattern, '', clean_message).strip()
            
            # Skip empty messages
            if not clean_message:
                continue
                
            # Determine role based on whether this is the current model
            if current_model_tag and msg['tag'] == current_model_tag:
                # This model's own previous messages are "assistant"
                content += clean_message
                if content.strip():  # Only add if there's content
                    llm_messages.append({"role": "assistant", "content": content})
            else:
                # Other models' messages are treated as "user" messages
                content += f"{msg['username']}: {clean_message}"
                if content.strip():  # Only add if there's content
                    llm_messages.append({"role": "user", "content": content})
    
    # Add current message with reply context only if there's actual content
    if current_text or reply_to_id:
        current_content = ""
        if reply_to_id and reply_to_id in msg_map:
            replied_msg = msg_map[reply_to_id]
            current_content += f"[Replying to {replied_msg['username']}: \"{replied_msg['message'][:50]}...\"]\n"
        if current_text:
            current_content += f"{current_user}: {current_text}"
        
        if current_content.strip():  # Only add if there's actual content
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