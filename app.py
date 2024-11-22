from flask import Flask, redirect, url_for, render_template, session, request, abort
from flask_mysqldb import MySQL
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import yaml

app = Flask(__name__)

app.config['SECRET_KEY'] = 'dd13289683eff386c252ccae8292c781ed8c728f5dc6e8b8c13c471cba57ed39' # $ python -c 'import secrets; print(secrets.token_hex())'

# Open and read the config file
with open('db.yaml', 'r') as config_file:
    db_config = yaml.safe_load(config_file)

mysql_user = db_config['mysql']['user']
mysql_password = db_config['mysql']['password']
mysql_host = db_config['mysql']['host']
mysql_db = db_config['mysql']['db']

# MySQL config
app.config['MYSQL_HOST'] = mysql_host
app.config['MYSQL_USER'] = mysql_user
app.config['MYSQL_PASSWORD'] = mysql_password
app.config['MYSQL_DB'] = mysql_db
mysql = MySQL(app)

#  Session config
app.config['SESSION_PERMANENT'] = False
# app.config['PERMANENT_SESSION_LIFETIME'] = 3600 # 1 hour
# app.config['SESSION_USE_SIGNER'] = True # deprecated since 0.7
app.config['SESSION_TYPE'] = 'filesystem' 
app.config['SESSION_FILE_DIR'] = './sessions' 

Session(app)
# set socketio session same as flask session
socketio = SocketIO(app, manage_session=False)

# match user_id with sid
user_id_sid = {}

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('chatroom.html', client_id=session['user_id'], username=session['username'])
    return redirect(url_for('login'))

# temporary login, need to get session id, username for send_message
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print('login post')
        userLoginInfo = request.form
        username = userLoginInfo['username']
        password = userLoginInfo['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/users')
def users():
    if 'user_id' not in session:
        abort(403)
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, username FROM users")
    user_data = cur.fetchall()
    cur.close()
    other_users = [[user[0], user[1]] for user in user_data if user[0] != session['user_id']]
    return ({'users': other_users})

# handled by socketio, don't need to emit to this event
@socketio.on('connect')
def handle_connect():
    client_id = session.get('user_id')
    if client_id:
        user_id_sid[client_id] = request.sid
    print("Client connected! client's user_id:", client_id, " sid:", request.sid)

# handled by socketio, don't need to emit to this event
@socketio.on('disconnect')
def handle_disconnect():
    client_id = session.get('user_id')
    if client_id:
        del user_id_sid[client_id]
    print("Client disconnected! client's user_id:", client_id, " sid:", request.sid)

@socketio.on('handshake')
def handle_handshake(data):
    client_id = data
    if client_id:
        user_id_sid[int(client_id)]
    print("Client handshake! client's user_id:", client_id, " sid:", request.sid)

@socketio.on('send_public_key')
def handle_send_publicKey(data):
    receiver_id = data['receiver_id']
    receiver_sid = user_id_sid.get(int(receiver_id))
    if receiver_sid:
        emit('receive_public_key', data['publicKey'], to=receiver_sid)
    else:
        print(f"Receiver {receiver_id} is not connected.")
    

# handle sent mesaage from clients
@socketio.on('send_message')
def handle_send_message(data):
    print('Received message:', data)
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    message_text = data['message']
    time = data['time']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (sender_id, receiver_id, message_content, created_time) VALUES (%s, %s, %s, %s)", (sender_id, receiver_id, message_text, time))
    mysql.connection.commit()
    cur.close()
    receiver_sid = user_id_sid.get(int(receiver_id))
    if receiver_sid:
        emit('receive_message', data, to=receiver_sid)
    else:
        print(f"Receiver {receiver_id} is not connected.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
