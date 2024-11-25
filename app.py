from flask import Flask, redirect, url_for, render_template, session, request, abort, jsonify
from flask_mysqldb import MySQL
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import yaml, base64

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        print('register post')
        userLoginInfo = request.form
        username = userLoginInfo['username']
        password = userLoginInfo['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user:
            return 'Same username already exists'
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        mysql.connection.commit()
        cur.close()
        return render_template('login.html')
    return render_template('register.html')

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
            #return 'Invalid credentials'
            return render_template('login.html')
    return render_template('login.html')

@app.route('/users')
def users():
    if 'user_id' not in session:
        abort(403)
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, username FROM users ORDER BY user_id")
    user_data = cur.fetchall()
    cur.close()
    other_users = [[user[0], user[1]] for user in user_data if user[0] != session['user_id']]
    return ({'users': other_users})

@app.route('/usersCommunicated')
def usersCommunicated():
    if 'user_id' not in session:
        abort(403)

    cur = mysql.connection.cursor()
    cur.execute("SELECT DISTINCT receiver_id FROM messages WHERE sender_id = %s", (session['user_id'],))
    receiverIds = cur.fetchall()

    receivers = []
    for receiverId in receiverIds:
        cur.execute("SELECT username FROM users WHERE user_id = %s", (receiverId[0],))
        username = cur.fetchall()
        receivers.append([receiverId[0], username[0]])
    cur.close()
    return ({'receivers': receivers})

@app.route('/logout')
def logout():
    client_id = session.get('user_id')
    if client_id:
        del user_id_sid[client_id]
    session.clear()
    return redirect(url_for('login'))

@socketio.on('handshake')
def handle_handshake(data):
    client_id = data
    if client_id:
        user_id_sid[int(client_id)] = request.sid
    print("Client handshake! client's user_id:", client_id, " sid:", request.sid)

@socketio.on('send_public_key')
def handle_send_publicKey(data):
    receiver_id = data['receiver_id']
    receiver_sid = user_id_sid.get(int(receiver_id))
    if receiver_sid:
        emit('receive_public_key', data, to=receiver_sid)
    else:
        print(f"Receiver {receiver_id} is not connected.")
    
# handle request for history messages
@socketio.on('request_history_message')
def handle_request_history_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    cur = mysql.connection.cursor()
    query = """SELECT sender_id, receiver_id, message_content, iv, sign, created_time, keyID FROM messages 
               WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
               ORDER BY created_time ASC"""
    cur.execute(query, (sender_id, receiver_id, receiver_id, sender_id))
    column_names = [desc[0] for desc in cur.description]
    messages = []
    for row in cur.fetchall():
        message_dict = dict(zip(column_names, row))
        # convert BLOB to ArrayBuffer
        message_dict['message_content'] = base64.b64encode(message_dict['message_content']).decode('utf-8')
        message_dict['iv'] = base64.b64encode(message_dict['iv']).decode('utf-8')
        message_dict['sign'] = base64.b64encode(message_dict['sign']).decode('utf-8')
        message_dict['created_time'] = message_dict['created_time'].isoformat()
        messages.append(message_dict)
    cur.close()
    emit('receive_history_message', messages)

# handle sent mesaage from clients
@socketio.on('send_message')
def handle_send_message(data):
    print('Received message:', data)
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    #message_text = data['message']
    cipher_text = bytes(data['cipherText'])
    iv = bytes(data['iv'])
    sign = bytes(data['signature'])
    
    time = data['time']
    keyID = data['keyID']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (sender_id, receiver_id, message_content, iv, sign, created_time, keyID) VALUES (%s, %s, %s, %s, %s, %s, %s)", (sender_id, receiver_id, cipher_text, iv, sign, time, keyID))
    mysql.connection.commit()
    cur.close()
    receiver_sid = user_id_sid.get(int(receiver_id))
    if receiver_sid:
        emit('receive_message', data, to=receiver_sid)
    else:
        print(f"Receiver {receiver_id} is not connected.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
