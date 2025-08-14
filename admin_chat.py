"""
Admin Chat Module for AHeyeCare
Provides admin-specific chat functionality for communicating with users
"""

from flask import render_template, request, jsonify, session
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
from models import ChatMessage
from extensions import db

class AdminChat:
    """Admin chat functionality for AHeyeCare"""
    
    @staticmethod
    def get_admin_chat_messages():
        """Get all chat messages for admin view"""
        return ChatMessage.query.order_by(ChatMessage.timestamp.desc()).all()
    
    @staticmethod
    def send_admin_message(data):
        """Send message as admin"""
        chat_msg = ChatMessage(
            sender='Admin',
            message_text=data['message'],
            session_id='admin_chat',
            timestamp=datetime.utcnow()
        )
        db.session.add(chat_msg)
        db.session.commit()
        return chat_msg
    
    @staticmethod
    def broadcast_admin_message(message):
        """Broadcast admin message to all users"""
        emit('admin_message', {
            'sender': 'Admin',
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)

# Admin chat routes
@app.route('/admin/chat')
def admin_chat():
    """Admin chat interface"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    messages = AdminChat.get_admin_chat_messages()
    return render_template('admin_chat.html', messages=messages)

@app.route('/admin/send_message', methods=['POST'])
def admin_send_message():
    """Send message as admin"""
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400
    
    try:
        chat_msg = AdminChat.send_admin_message(data)
        AdminChat.broadcast_admin_message(data['message'])
        return jsonify({'success': True, 'message': 'Message sent'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# SocketIO events for admin
@socketio.on('admin_join')
def handle_admin_join(data):
    """Handle admin joining chat"""
    if not session.get('admin'):
        return
    
    join_room('admin_chat')
    emit('admin_status', {'status': 'online', 'admin': True}, room='admin_chat')

@socketio.on('admin_message')
def handle_admin_message(data):
    """Handle admin sending message"""
    if not session.get('admin'):
        return
    
    try:
        chat_msg = AdminChat.send_admin_message(data)
        emit('new_admin_message', {
            'sender': 'Admin',
            'message': data['message'],
            'timestamp': datetime.utcnow().isoformat()
        }, room='admin_chat', broadcast=True)
    except Exception as e:
        emit('error', {'message': str(e)}, room=request.sid)
