#!flask/bin/python
from flask import Flask, jsonify, request, abort
import psycopg2
import os
import time


# A wrapper around the database.
#
# Each method returns a dictionary with key 'ok'.
#
# If 'ok' is true, the operation was successful,
#   and the 'data' might contain returned data.
#
# If 'ok' is false, the operation failed,
#   and the 'error' key will contain a message describing the error.
class Database:
    def __init__(self, dbhost, dbname, dbuser, dbpassword):
        # Save the database connection string
        self.db_info = f"host={dbhost} dbname={dbname} user={dbuser} password={dbpassword}"

        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # Create tables as needed
            c.execute('''
            create table if not exists users (
                username text primary key, name text not null, passhash text not null
            );
            ''')

            c.execute('''
            create table if not exists messages (
                id serial primary key, from_user text not null, to_user text not null, link text not null,
                datetime text not null, archived boolean not null default false,
                foreign key (from_user) references users (username),
                foreign key (to_user) references users (username));
            ''')

    # Add user_data with keys ['username', 'name', 'passhash'] to database
    def add_user(self, user_data):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # First, check if the user is already in the database
            sql = 'select count(*) from users where username=%s'
            c.execute(sql, (user_data['username'],))
            count = c.fetchone()[0] # fetchone returns a tuple (count,), so get just the count

            # If it exists, we can't add it
            if count != 0:
                return dict(ok=False, error=f"User {user_data['username']} already exists")

            # Otherwise, add the user
            sql = 'insert into users (username, name, passhash) values (%s, %s, %s)'
            c.execute(sql, (user_data['username'], user_data['name'], user_data['passhash']))
            conn.commit()
            return dict(ok=True)

    # Check that combination of keys ['username', 'passhash'] in verify_user_data matches database
    def verify_user(self, verify_user_data):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # Try to find rows in database matching username and password combination
            sql = 'select count(*) from users where username=%s and passhash=%s'
            c.execute(sql, (verify_user_data['username'], verify_user_data['passhash']))
            count = c.fetchone()[0] # fetchone returns a tuple (count,), so get just the count

            # If there's a record present, then the credentials are correct
            if count == 1:
                return dict(ok=True)

            # Otherwise it's an error
            else:
                return dict(ok=False, error='Username and password do not match')

    # Add message_data with keys ['from', 'to', 'link'] to database
    def add_message(self, message_data):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # First, try to see if sender is in the database
            sql = 'select count(*) from users where username=%s'
            c.execute(sql, (message_data['from'],))

            # If not, can't send
            if c.fetchone()[0] != 1:
                return dict(ok=False, error='From not in database')

            # Then, check if receiver is in the database, and fail if not
            c.execute(sql, (message_data['to'],))
            if c.fetchone()[0] != 1:
                return dict(ok=False, error='To not in database')

            # Both receiver and sender are known → add the message to the database
            sql = 'insert into messages (from_user, to_user, link, datetime) values (%s, %s, %s, %s);'
            c.execute(sql, (message_data['from'], message_data['to'], message_data['link'], int(time.time())))
            conn.commit()
            return dict(ok=True)

    # Get messages addressed to 'username'
    def get_messages(self, username, archived=False):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # Get all messages from the database that are addressed to 'username' and match the given 'archived' condition
            sql = 'select id, from_user, datetime, link from messages where to_user = %s and archived = %s;'
            c.execute(sql, (username, archived))

            # Get all returned rows and format them appropriately
            rows = c.fetchall()
            result = [{'id': int(msg_id), 'from': from_user, 'datetime': int(datetime), 'link': link} for (msg_id, from_user, datetime, link) in rows]
            result.sort(key=lambda x: x['datetime'], reverse=True)
            return dict(ok=True, data=result)

    # Get message by numeric id 'message_id'
    def get_message_by_id(self, message_id):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # Find a row in the messages table with the specific id
            sql = 'select id, from_user, to_user, link, datetime, archived from messages where id = %s'
            c.execute(sql, (message_id,))

            # Only get that one row, and fail if none were returned
            row = c.fetchone()
            if not row:
                return dict(ok=False, error='Message not in database')

            # Otherwise, format the row appropriately and return it
            result = {'id': int(row[0]), 'from': row[1], 'to': row[2], 'link': row[3],
                'datetime': int(row[4]), 'archived': row[5]}
            return dict(ok=True, data=result)

    # Set 'archived' to true for message with numeric id 'message_id'
    def archive_message(self, message_id):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # First, see if the message is already archived, and fail if it is
            sql = 'select archived from messages where id = %s'
            c.execute(sql, (message_id,))
            archived_status = c.fetchone()[0]
            if archived_status:
                return dict(ok=False, error='Message already archived')

            # Otherwise, set its 'archived' field to true
            sql = 'update messages set archived=true where id = %s'
            c.execute(sql, (message_id,))
            conn.commit()
            return dict(ok=True)


# Create the database interface and the Flask app
# Use the environment variables passed from the ConfigMap and Secret, via the Deployment
db = Database(os.environ['POSTGRES_SERVICE_HOST'], os.environ['POSTGRES_DB'], os.environ['POSTGRES_USER'], os.environ['POSTGRES_PASSWORD'])
app = Flask(__name__)

@app.route('/<username>/messages', methods=['GET'])
def get_messages(username):
    query = db.get_messages(username)
    if query['ok']:
        return jsonify({'status': f"Retrieved messages of {username}",
                        'data': query['data']})
    else:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)


@app.route('/<username>/archive', methods=['GET'])
def get_archive(username):
    query = db.get_messages(username, archived=True)
    if query['ok']:
        return jsonify({'status': f"Retrieved archived messages of {username}",
                        'data': query['data']})
    else:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

@app.route('/<username>/archive', methods=['POST'])
def archive(username):
    # Fail if 'id' isn't provided in the body
    if not 'id' in request.form:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    # Fail if we can't find message with id 'id'
    query = db.get_message_by_id(request.form['id'])
    if not query['ok']:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    # Archive the message
    query = db.archive_message(request.form['id'])
    if not query['ok']:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    return jsonify({'status': f"Archived message {request.form['id']}"})


@app.route('/<username>/messages', methods=['POST'])
def send_message(username):
    # Fail if 'to' and 'link' aren't provided in the body
    if not all(k in request.form for k in ['to', 'link']):
        abort(jsonify(message=query['error']), 400)

    # Add the message to the database
    data = {'from': username, 'to': request.form['to'], 'link': request.form['link']}
    query = db.add_message(data)

    if query['ok']:
        return jsonify({'status': 'Message sent'})
    else:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)


@app.route('/add_user', methods=['POST'])
def add_user():
    # Fail if 'username', 'name', and 'passhash' aren't all provided in the body
    if not all(k in request.form for k in ['username', 'name', 'passhash']):
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    # Add the user to the database
    data = {'username': request.form['username'], 'name': request.form['name'], 'passhash': request.form['passhash']}
    query = db.add_user(data)

    if query['ok']:
        return jsonify({'status': f"Added user {data['username']}"})
    else:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)


@app.route('/verify_user', methods=['POST'])
def verify_user():
    # Fail if 'username' and 'passhash' aren't provided in the body
    if not all(k in request.form for k in ['username', 'passhash']):
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    # Check the user+passhash against the database
    data = {'username': request.form['username'], 'passhash': request.form['passhash']}
    query = db.verify_user(data)
    if query['ok']:
        return jsonify({'status': f"User {data['username']} verified"})
    else:
        response = jsonify(message=query['error'])
        response.status_code = 401
        abort(response)


# In case you run the file as ./app.py (but `flask run` should be the main way)
if __name__ == '__main__':
    app.run(debug=True)
