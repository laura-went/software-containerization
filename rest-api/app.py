#!flask/bin/python
from flask import Flask, jsonify, request, abort
import psycopg2
import os
import time


# A wrapper around the database, modify this to use a postgres driver instead of sqlite.
# Probably psycopg would be best: https://www.psycopg.org/
class Database:
    def __init__(self, dbhost, dbname, dbuser, dbpassword):
        self.db_info = f"host={dbhost} dbname={dbname} user={dbuser} password={dbpassword}"
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()

            # Create tables as needed
            c.execute('''
            create table if not exists users
            (username text primary key, name text not null, passhash text not null);
            ''')

            c.execute('''
            create table if not exists messages
            (id serial primary key, from_user text not null, to_user text not null, link text not null,
            datetime text not null, archived boolean not null default false,
            foreign key (from_user) references users (username), foreign key (to_user) references users (username));
            ''')

    def add_user(self, user_data):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()
            sql = 'select count(*) from users where username=%s'
            c.execute(sql, (user_data['username'],))
            count = c.fetchone()[0]
            if count != 0:
                return dict(ok=False, error=f"User {user_data['username']} already exists")

            sql = 'insert into users (username, name, passhash) values (%s, %s, %s)'
            c.execute(sql, (user_data['username'], user_data['name'], user_data['passhash']))
            conn.commit()
            return dict(ok=True)

    def verify_user(self, verify_user_data):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()
            sql = 'select count(*) from users where username=%s and passhash=%s'
            c.execute(sql, (verify_user_data['username'], verify_user_data['passhash']))
            count = c.fetchone()[0]
            if count == 1:
                return dict(ok=True)
            else:
                return dict(ok=False, error='Username and password do not match')

    def add_message(self, message_data):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()
            sql = 'select count(*) from users where username=%s'
            c.execute(sql, (message_data['from'],))
            if c.fetchone()[0] != 1:
                return dict(ok=False, error='From not in database')

            c.execute(sql, (message_data['to'],))
            if c.fetchone()[0] != 1:
                return dict(ok=False, error='To not in database')

            sql = 'insert into messages (from_user, to_user, link, datetime) values (%s, %s, %s, %s);'
            c.execute(sql, (message_data['from'], message_data['to'], message_data['link'], int(time.time())))
            conn.commit()
            return dict(ok=True)

    def get_messages(self, username, archived=False):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()
            sql = 'select id, from_user, datetime, link from messages where to_user = %s and archived = %s;'
            c.execute(sql, (username, archived))
            rows = c.fetchall()
            result = [{'id': int(msg_id), 'from': from_user, 'datetime': int(datetime), 'link': link} for (msg_id, from_user, datetime, link) in rows]
            result.sort(key=lambda x: x['datetime'], reverse=True)
            return dict(ok=True, data=result)

    def get_message_by_id(self, message_id):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()
            sql = 'select id, from_user, to_user, link, datetime, archived from messages where id = %s'
            c.execute(sql, (message_id,))
            row = c.fetchone()
            if not row:
                return dict(ok=False, error='Message not in database')

            result = {'id': int(row[0]), 'from': row[1], 'to': row[2], 'link': row[3],
                'datetime': int(row[4]), 'archived': row[5]}
            return dict(ok=True, data=result)

    def archive_message(self, message_id):
        with psycopg2.connect(self.db_info) as conn:
            c = conn.cursor()
            sql = 'select archived from messages where id = %s'
            c.execute(sql, (message_id,))
            archived_status = c.fetchone()[0]
            if archived_status:
                return dict(ok=False, error='Message already archived')

            sql = 'update messages set archived=true where id = %s'
            c.execute(sql, (message_id,))
            conn.commit()
            return dict(ok=True)


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
    if not 'id' in request.form:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    query = db.get_message_by_id(request.form['id'])
    if not query['ok']:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    query = db.archive_message(request.form['id'])
    if not query['ok']:
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    return jsonify({'status': f"Archived message {request.form['id']}"})


@app.route('/<username>/messages', methods=['POST'])
def send_message(username):
    if not all(k in request.form for k in ['to', 'link']):
        abort(jsonify(message=query['error']), 400)

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
    if not all(k in request.form for k in ['username', 'name', 'passhash']):
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

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
    if not all(k in request.form for k in ['username', 'passhash']):
        response = jsonify(message=query['error'])
        response.status_code = 400
        abort(response)

    data = {'username': request.form['username'], 'passhash': request.form['passhash']}
    query = db.verify_user(data)
    if query['ok']:
        return jsonify({'status': f"User {data['username']} verified"})
    else:
        response = jsonify(message=query['error'])
        response.status_code = 401
        abort(response)


if __name__ == '__main__':
    app.run(debug=True)
