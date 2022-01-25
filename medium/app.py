from flask import Flask, jsonify, render_template, request, flash, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from sqlalchemy import or_, and_
from sqlalchemy.future import engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime


app = Flask(__name__, template_folder="templates")
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://bob:test@localhost/flask_medium4"
app.secret_key = 'admin'
db = SQLAlchemy()
db.init_app(app)


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer(), primary_key=True)
    from_user = db.Column(db.String())
    to_user = db.Column(db.String())
    message = db.Column(db.String())
    time = db.Column(db.DateTime())


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String())
    pwd = db.Column(db.String())


@app.route('/pick_name', methods=['POST', 'GET'])
def pick_name():
    error = None
    # TODO: check if username comes through
    if request.method == 'POST':
        from_name = str(request.form['from_name'])
        to_name = str(request.form['to_name'])

        messages = Message.query.filter(or_(and_(Message.from_user == from_name, Message.to_user == to_name), and_(Message.from_user == to_name, Message.to_user == from_name))
                                        ).order_by(Message.time)
        message = messages.first()
        users = User.query.filter(User.name != from_name).all()
        return render_template("homescreen.html", username=from_name, users=users, messages=messages, to_user=to_name)
    error = "Request method wasn't POST."
    return render_template("login.html", error=error)


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/add_user', methods=["GET", "POST"])
def add_user():
    db.create_all()
    db.session.commit()
    user = User.query.first()
    message = Message.query.first()
    # TODO edit function
    if not user:
        u = User(name='laura', pwd='hoi')
        db.session.add(u)
        db.session.commit()
    if not message:
        m = Message(from_user='laura', to_user='laura2', message='hoi test', time=datetime.now())
        db.session.add(m)
        db.session.commit()
    user = User.query.first()
    message = Message.query.first()
    # return "User '{} {}' is from database".format(user.name, user.pwd)
    return render_template('new.html', username=user.name, pwd=message.message)


@app.route('/registered', methods=['POST', 'GET'])
def registered():
    error = None
    # TODO throw error if empty uname pwd
    if request.method == 'POST':
        username = str(request.form['username'])
        password = str(request.form['password'])
        users = User.query.filter(User.name == username, User.pwd == password)
        usernames = User.query.filter(User.name == username)
        if users.first():
            error = 'User already exists!'
        elif usernames.first():
            error = 'Username already taken.'
        else:
            u = User(name=username, pwd=password)
            db.session.add(u)
            db.session.commit()
            return render_template('login.html', success='User successfully created!')
    return render_template('register.html', error=error)


@app.route("/")
def start():
    return render_template('login.html')


@app.route("/login", methods=['POST', 'GET'])
def login():
    error = None
    if request.method == 'POST':
        username = str(request.form['username'])
        password = str(request.form['password'])

        if not username or not password:
            error = 'Username and/or password have not correctly been received.'
            return render_template('login.html', error=error)

        users = User.query.filter(User.name == username, User.pwd == password)
        user = users.first()
        if user:
            users = User.query.filter(User.name != username).all() # Get all users for homescreen list except for own user
            return render_template("homescreen.html", username=username, users=users)
        else:
            error = 'Invalid credentials'
    error = "Request method wasn't POST."
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    return render_template('login.html', success='Successfully logged out!')


@app.route("/new_message", methods=['POST', 'GET'])
def new_message():
    error = None
    if request.method == 'POST':
        message = str(request.form['message'])
        from_user = str(request.form['from_user'])
        to_user = str(request.form['to_user'])
        now = datetime.now()

        users = User.query.filter(User.name != from_user).all()

        if not message or not from_user or not to_user:
            error = 'Message cannot be sent. From: ' + from_user + ' To: ' + to_user
            return render_template("homescreen.html", username=from_user, users=users, error=error)

        message = Message(from_user=from_user, to_user=to_user, message=message, time=now)
        db.session.add(message)
        db.session.commit()

        messages = Message.query.filter(or_(and_(Message.from_user == from_user, Message.to_user == to_user),
                                            and_(Message.from_user == to_user, Message.to_user == from_user))
                                        ).order_by(Message.time)
        return render_template("homescreen.html", username=from_user, to_user=to_user, users=users, messages=messages)
    error = "Request method wasn't POST."
    return render_template("login.html", error=error)


@app.route("/delete_message", methods=['POST', 'GET'])
def delete_message():
    error = None
    if request.method == 'POST':
        delete_id = str(request.form['id'])
        from_user = str(request.form['from_user'])
        to_user = str(request.form['to_user'])
        if not delete_id:
            error = 'no id or users.'
            return render_template("login.html", error=error)
        message = Message.query.filter(Message.id == delete_id)
        db.session.delete(message.first())
        db.session.commit()
        users = User.query.filter(User.name != from_user).all()
        messages = Message.query.filter(or_(and_(Message.from_user == from_user, Message.to_user == to_user),
                                            and_(Message.from_user == to_user, Message.to_user == from_user))
                                        ).order_by(Message.time)

        return render_template("homescreen.html", username=from_user, to_user=to_user, users=users, messages=messages)
    error = "Request method wasn't POST."
    return render_template("login.html", error=error)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
