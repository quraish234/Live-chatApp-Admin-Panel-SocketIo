from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from flask_cors import CORS
import os
import mysql.connector
#import eventlet  # or 
#import gevent
SECRET_KEY = os.urandom(32)

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = SECRET_KEY

socketio = SocketIO(app, cors_allowed_origins="*")

# Establish a connection to the MySQL database
db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="Qwerty123!@#",
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

@app.route('/chatbot')
def chatbot():  
    # Fetch user chats from the database
    chats = get_user_chats()
    return render_template('chatbot.html', chats=chats)

def get_user_chats():
    # Connect to the MySQL database
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Qwerty123!@#",
        database="rasa"
    )
    cursor = conn.cursor(dictionary=True)

    # Fetch user chats
    select_query = "SELECT * FROM it_chat_history"
    cursor.execute(select_query)
    chats = cursor.fetchall()

    cursor.close()
    conn.close()

    return chats

@socketio.on('mark_read')
def handle_mark_read(data):
    marked_as_read = data['read']

    # Update the database to mark selected chats as read
    update_query = "UPDATE it_chat_history SET is_read = 1 WHERE user_id IN ('{}')".format("','".join(marked_as_read))

    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Qwerty123!@#",
        database="rasa"
    )
    cursor = conn.cursor()
    cursor.execute(update_query)
    conn.commit()  # Commit the changes to the database
    cursor.close()
    conn.close()

    # Update the database with the selected status for each user
    for user_id, status in data.get('status', {}).items():
        status_update_query = f"UPDATE it_chat_history SET status = '{status}' WHERE user_id = '{user_id}'"

        conn = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="Qwerty123!@#",
            database="rasa"
        )
        cursor = conn.cursor()
        cursor.execute(status_update_query)
        conn.commit()
        cursor.close()
        conn.close()

    # Emit the update to all connected clients
    socketio.emit('update_chats', {'message': 'Chats marked as read and status updated'})

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

