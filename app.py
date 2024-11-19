from flask import Flask, redirect, url_for, render_template
from flask_mysqldb import MySQL
import yaml

app = Flask(__name__)

# Open and read the config file
with open('db.yaml', 'r') as config_file:
    db_config = yaml.safe_load(config_file)

# MySQL config
app.config['MYSQL_HOST'] = db_config['mysql']['host']
app.config['MYSQL_USER'] = db_config['mysql']['user']
app.config['MYSQL_PASSWORD'] = db_config['mysql']['password']
app.config['MYSQL_DB'] = db_config['mysql']['db']

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('chatroom.html')

@app.route('/users')
def users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, username FROM users")
    user_data = cur.fetchall()
    cur.close()

    filtered_users = [[user[0], user[1]] for user in user_data]
    return {'users': filtered_users}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
