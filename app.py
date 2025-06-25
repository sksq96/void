from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from litellm import completion
import os
from datetime import datetime
from dotenv import load_dotenv
from utils import (
    load_messages, save_messages, find_model_mentions, 
    extract_model_context, build_llm_messages, create_message
)
from models import AVAILABLE_MODELS, MODEL_DESCRIPTIONS

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Store messages in memory
messages = load_messages()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models')
def get_models():
    return jsonify(MODEL_DESCRIPTIONS)

@socketio.on('connect')
def handle_connect():
    # Send last 50 messages to new user
    for msg in messages[-50:]:
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
    
    messages.append(user_message)
    emit('message', user_message, broadcast=True)
    save_messages(messages)
    
    # Find and call mentioned models
    mentioned_models = find_model_mentions(message_text, AVAILABLE_MODELS)
    
    # If replying to a bot message and no models mentioned, auto-trigger the same model
    if reply_to and not mentioned_models:
        # Find the message being replied to
        replied_message = next((msg for msg in messages if msg.get('id') == reply_to), None)
        if replied_message and replied_message.get('type') == 'bot' and replied_message.get('tag'):
            # Auto-trigger the same model that was replied to
            tag = replied_message.get('tag')
            model = replied_message.get('model')
            if tag and model:
                mentioned_models = [(tag, model)]
    
    for tag, model in mentioned_models:
        handle_model_response(tag, model, username, message_text, reply_to)

def handle_model_response(tag: str, model: str, username: str, message_text: str, reply_to: str = None):
    """Handle calling an LLM and streaming its response"""
    try:
        # Extract context and build messages
        # Pass all messages except the last one (which is the current message we just added)
        context = extract_model_context(message_text, tag)
        llm_messages = build_llm_messages(messages[:-1], username, context, reply_to)
        
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
        
        # Stream response
        response = completion(
            model=model,
            messages=llm_messages,
            max_tokens=4096,  # Increased from 150
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                emit('stream_chunk', {
                    'id': bot_id,
                    'content': content
                }, broadcast=True)
        
        # Save bot message with the same ID used for streaming
        bot_message = create_message(bot_username, full_response, 'bot', model=model, tag=tag, id=bot_id)
        messages.append(bot_message)
        save_messages(messages)
        
        # Complete streaming and send full message data
        emit('stream_complete', {
            'id': bot_id,
            'message': bot_message
        }, broadcast=True)
        
    except Exception as e:
        # Send error message
        error_msg = create_message('SYSTEM', f'Error calling {tag}: {str(e)}', 'system')
        messages.append(error_msg)
        emit('message', error_msg, broadcast=True)
        save_messages(messages)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)