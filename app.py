from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from flask_cors import CORS
import os
import mysql.connector

SECRET_KEY = os.urandom(32)

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = SECRET_KEY

socketio = SocketIO(app, cors_allowed_origins="*")

# Establish a connection to the MySQL database
db = mysql.connector.connect(
    host="192.168.19.160",
    user="usher",
    password="Um@ir65048420",
    database="rasa"
)
cursor = db.cursor()

users = {}
chats = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    # Load user information from the database
    cursor.execute("SELECT room, username FROM live_chat_users")
    user_data = cursor.fetchall()
    users.update(dict(user_data))
    
    return render_template('admin.html', users=users, chats=chats)

# Get username
@socketio.on('username', namespace='/message')
def receive_username(username):
    room = request.sid
    users[room] = username
    chats[room] = ''
    
    # Insert user information into the database
    cursor.execute("INSERT INTO live_chat_users (room, username) VALUES (%s, %s) ON DUPLICATE KEY UPDATE username=%s",
                   (room, username, username))
    db.commit()
    
    send(username + ' has entered the room.')
    emit('creat_room', room)

# Send user messages
@socketio.on('user_message', namespace='/message')
def user_message(data):
    username = data['username']
    message = data['message']
    room = data['room']
    msg = f'{username}: {message}'
    chats[room] += msg + '<br>'
    emit('print_message', msg, room=room)

    # Insert the message into the database
    cursor.execute("INSERT INTO live_chat_messages (room, sender, message) VALUES (%s, %s, %s)",
                   (room, username, message))
    db.commit()

# Send admin messages
@socketio.on('admin_message', namespace='/message')
def admin_message(data):
    room = data['room']
    message = data['message']
    msg = f'Agent: {message}'
    chats[room] += msg + '<br>'
    emit('print_message', msg, room=room)

    # Insert the message into the database
    cursor.execute("INSERT INTO live_chat_messages (room, sender, message) VALUES (%s, %s, %s)",
                   (room, 'Agent', message))
    db.commit()

# Open one of chat in admin dashboard
@socketio.on('chat_menu', namespace='/message')
def chat_chat(data):
    room = data['room']
    join_room(room)

    # Load past messages from the database for the selected room
    cursor.execute("SELECT sender, message FROM live_chat_messages WHERE room = %s", (room,))
    past_messages = cursor.fetchall()
    formatted_messages = '<br>'.join(f"{sender}: {message}" for sender, message in past_messages)
    emit('show_past_messages', formatted_messages)

# Live typing indicator
@socketio.on('typing', namespace='/message')
def live_typing(data):
    room = data['room']
    emit('display', data, room=room)


@socketio.on_error(namespace='/message')
def chat_error_handler(e):
    print('An error has occurred: ' + str(e))


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5009, debug=True)

# TRŪKSTA:
# TO DO: Live typing indication - 50 % (left to make indication for users typo too)
# TO DO: Sent/Delivered/Seen statuses
# TO DO: Per session chat history (save as output?)
# TO DO: Load chat history for user too (after refresh keep in same old room?)
# TO DO: Alert new user, new messages for admin (+autoadd new user to chat menu)
# TO DO: Break words if they are tooooooo long to fit chatbox window
# TO DO: Doesn't work input required
# TO DO: If user message room != current admin room change chat menu button color
# TO DO: Add log out/disconnected

# @socketio.on('leave')
# def on_leave(data):
#     username = data['username']
#     room = data['room']
#     leave_room(room)
#     send(username + ' has left the room.', room=room)
#
# @socketio.on('connect')
# def test_connect():
#     emit('my response', {'data': 'Connected'})
#
# @socketio.on('disconnect')
# def test_disconnect():
#     print('Client disconnected')
