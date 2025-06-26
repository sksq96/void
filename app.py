from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import anthropic
import os
import random
from datetime import datetime
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from utils import (
    create_new_conversation, load_conversation, save_conversation,
    get_all_conversations, delete_conversation, find_model_mentions, 
    extract_model_context, build_llm_messages, create_message
)
from models import AVAILABLE_MODELS, MODEL_DESCRIPTIONS

load_dotenv()

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Store current conversation in memory
current_conversation = None
# Create or load initial conversation
conversations = get_all_conversations()
if conversations:
    current_conversation = load_conversation(conversations[0]['id'])
else:
    current_conversation = create_new_conversation()

# Store active streams for cancellation
active_streams = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models')
def get_models():
    # Convert list to dict format expected by frontend
    models_dict = {item['tag']: item['desc'] for item in MODEL_DESCRIPTIONS}
    return jsonify(models_dict)

@app.route('/api/conversations')
def get_conversations():
    return jsonify(get_all_conversations())

@app.route('/api/conversation/<conv_id>')
def get_conversation(conv_id):
    conv = load_conversation(conv_id)
    if conv:
        return jsonify(conv)
    return jsonify({'error': 'Conversation not found'}), 404

@socketio.on('new_conversation')
def handle_new_conversation(data):
    global current_conversation
    title = data.get('title')
    system_prompt = data.get('system_prompt')
    current_conversation = create_new_conversation(title, system_prompt)
    emit('conversation_created', current_conversation, broadcast=True)
    emit('clear_messages', broadcast=True)

@socketio.on('load_conversation') 
def handle_load_conversation(conv_id):
    global current_conversation
    conv = load_conversation(conv_id)
    if conv:
        current_conversation = conv
        emit('clear_messages', broadcast=True)
        # Send all messages from loaded conversation
        for msg in conv['messages']:
            emit('message', msg)
        emit('conversation_loaded', {
            'id': conv['id'],
            'title': conv['title'],
            'system_prompt': conv['system_prompt']
        })

@socketio.on('update_system_prompt')
def handle_update_system_prompt(data):
    global current_conversation
    if current_conversation:
        current_conversation['system_prompt'] = data.get('system_prompt', '')
        save_conversation(current_conversation['id'], current_conversation)
        emit('system_prompt_updated', {'system_prompt': current_conversation['system_prompt']})

@socketio.on('delete_conversation')
def handle_delete_conversation(conv_id):
    global current_conversation
    delete_conversation(conv_id)
    # If deleting current conversation, create new one
    if current_conversation and current_conversation['id'] == conv_id:
        current_conversation = create_new_conversation()
        emit('conversation_created', current_conversation, broadcast=True)
        emit('clear_messages', broadcast=True)
    emit('conversation_deleted', {'id': conv_id}, broadcast=True)

@socketio.on('trigger_llm_response')
def handle_trigger_llm_response(data):
    model_tag = data.get('model_tag')
    reply_to = data.get('reply_to')
    
    if not model_tag or model_tag not in AVAILABLE_MODELS:
        return
    
    model = AVAILABLE_MODELS[model_tag]
    
    # Use "System" as the username when triggering LLM directly
    handle_model_response(model_tag, model, "System", "", reply_to)

@socketio.on('stop_streaming')
def handle_stop_streaming(data):
    message_id = data.get('message_id')
    if message_id and message_id in active_streams:
        # Cancel the stream
        stream = active_streams[message_id]
        if hasattr(stream, 'close'):
            stream.close()
        del active_streams[message_id]
        
        # Just emit a simple completion signal
        # The frontend already has the message data
        emit('stream_complete', {
            'id': message_id
        }, broadcast=True)

@socketio.on('connect')
def handle_connect():
    # Send current conversation info
    if current_conversation:
        emit('conversation_loaded', {
            'id': current_conversation['id'],
            'title': current_conversation['title'],
            'system_prompt': current_conversation['system_prompt']
        })
        # Send last 50 messages to new user
        for msg in current_conversation['messages'][-50:]:
            emit('message', msg)

@socketio.on('send_message')
def handle_message(data):
    username = data.get('username', 'Anonymous')
    message_text = data.get('message', '')
    reply_to = data.get('replyTo', None)
    
    # Create and broadcast user message
    user_message = create_message(username, message_text, 'user')
    
    # Add reply information if replying
    if reply_to:
        user_message['replyTo'] = reply_to
    
    if current_conversation:
        current_conversation['messages'].append(user_message)
        save_conversation(current_conversation['id'], current_conversation)
    emit('message', user_message, broadcast=True)
    
    # Find and call mentioned models
    mentioned_models = find_model_mentions(message_text, AVAILABLE_MODELS)
    
    # If no models mentioned, randomly select a model to respond
    if not mentioned_models:
        # Randomly select a model from available models
        random_tag, random_model = random.choice(list(AVAILABLE_MODELS.items()))
        mentioned_models = [(random_tag, random_model)]
        print(f"[DEBUG] Randomly selected {random_tag} to respond")
    
    for tag, model in mentioned_models:
        handle_model_response(tag, model, username, message_text, reply_to)

@observe()
def handle_model_response(tag: str, model: str, username: str, message_text: str, reply_to: str = None):
    """Handle calling an LLM and streaming its response"""
    if not current_conversation:
        return
        
    try:
        # Extract context and build messages
        # Pass all messages except the last one (which is the current message we just added)
        context = extract_model_context(message_text, tag)
        system_prompt = current_conversation.get('system_prompt')
        llm_messages = build_llm_messages(
            current_conversation['messages'][:-1], 
            username, 
            context, 
            reply_to,
            system_prompt,
            tag  # Pass the current model tag
        )
        
        # Create bot message ID
        bot_id = f"bot_{tag}_{datetime.now().timestamp()}"
        bot_username = tag[1:].upper()
        
        # Send initial streaming message
        emit('message', {
            'id': bot_id,
            'username': bot_username,
            'message': '',
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': 'bot',
            'streaming': True
        }, broadcast=True)
        
        # Create a Langfuse generation for tracing
        generation = langfuse.generation(
            name="chat-completion",
            model=model,
            model_parameters={
                "max_tokens": 4096,
                "temperature": 1.0
            },
            metadata={
                "conversation_id": current_conversation['id'] if current_conversation else None,
                "user": username,
                "model_tag": tag,
                "reply_to": reply_to,
                "app": "retro-irc-chat"
            }
        )
        
        # Convert messages to Anthropic format
        system_message = llm_messages[0]['content'] if llm_messages and llm_messages[0]['role'] == 'system' else None
        messages = []
        for msg in llm_messages[1:] if system_message else llm_messages:
            messages.append({
                "role": msg['role'] if msg['role'] in ['user', 'assistant'] else 'user',
                "content": msg['content']
            })
        
        # Log input to Langfuse
        generation.update(input=messages)
        
        # Stream response from Anthropic
        full_response = ""
        stream = anthropic_client.messages.stream(
            model=model.replace('anthropic/', ''),  # Remove provider prefix
            messages=messages,
            system=system_message,
            max_tokens=4096
        )
        
        # Store stream for potential cancellation
        active_streams[bot_id] = stream
        
        try:
            with stream as stream_manager:
                for text in stream_manager.text_stream:
                    # Check if stream was cancelled
                    if bot_id not in active_streams:
                        break
                    
                    full_response += text
                    emit('stream_chunk', {
                        'id': bot_id,
                        'content': text
                    }, broadcast=True)
        finally:
            # Clean up stream reference
            if bot_id in active_streams:
                del active_streams[bot_id]
        
        # Log output to Langfuse
        generation.update(output=full_response)
        generation.end()
        
        # Save bot message with the same ID used for streaming
        bot_message = create_message(bot_username, full_response, 'bot', model=model, tag=tag, id=bot_id)
        if current_conversation:
            current_conversation['messages'].append(bot_message)
            save_conversation(current_conversation['id'], current_conversation)
        
        # Complete streaming and send full message data
        emit('stream_complete', {
            'id': bot_id,
            'message': bot_message
        }, broadcast=True)
        
    except Exception as e:
        # Send error message
        error_msg = create_message('SYSTEM', f'Error calling {tag}: {str(e)}', 'system')
        if current_conversation:
            current_conversation['messages'].append(error_msg)
            save_conversation(current_conversation['id'], current_conversation)
        emit('message', error_msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)