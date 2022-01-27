from flask import Flask, render_template, request, url_for, redirect, make_response, session
import os
import requests
import hashlib


# Just a small abstraction over the REST API, so we don't have to constantly
# enter the base URI
class RestAPI:
    def __init__(self):
        self.base = f"http://{os.getenv('REST_API_SERVICE_HOST')}:{os.getenv('REST_API_SERVICE_PORT')}"

    def get(self, endpoint):
        return requests.get(self.base+endpoint)

    def post(self, endpoint, data):
        return requests.post(self.base+endpoint, data=data)


api = RestAPI()
app = Flask(__name__, template_folder="templates")

# This is needed for 'session'
app.secret_key = os.getenv("SECRET_KEY")


@app.route('/home', methods=['GET'])
def home():
    picked_name = request.args.get('picked_name')
    success = session.pop('success') if 'success' in session else None
    username = request.cookies.get('username')

    # Get incoming messages from the API
    resp = api.get(f"/{username}/messages")
    messages = resp.json()['data']

    # Get a set of all users that sent those messages
    users = {m['from'] for m in messages}

    # If the user clicked on a specific name, show the links they shared, otherwise show nothing.
    if picked_name:
        messages = [m for m in messages if m['from'] == picked_name]
        return render_template('homescreen.html', username=username, users=users, messages=messages, to_user=picked_name, success=success)
    else:
        return render_template('homescreen.html', username=username, users=users, success=success)


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/registered', methods=['POST'])
def registered():
    # TODO throw error if empty uname pwd
    name = str(request.form['name'])
    username = str(request.form['username'])
    password = str(request.form['password'])
    passhash = hashlib.sha512(password.encode()).hexdigest()

    api.post("/add_user", {'name': name, 'username': username, 'passhash': passhash})
    return render_template('login.html', success='User successfully created!')


@app.route("/")
def start():
    username = request.cookies.get('username')
    if username:
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))


@app.route("/login", methods=['POST', 'GET'])
def login():
    error = None
    if request.method == "GET":
        return render_template('login.html')
    elif request.method == 'POST':
        username = str(request.form['username'])
        password = str(request.form['password'])

        if not username or not password:
            error = 'Username and/or password have not correctly been received.'
            return render_template('login.html', error=error)

        passhash = hashlib.sha512(password.encode()).hexdigest()

        resp = api.post('/verify_user', {'username': username, 'passhash': passhash})

        if resp.ok:
            resp = redirect(url_for('home'))
            resp.set_cookie('username', username)
            return resp
        else:
            error = resp.json()['message']
            return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    resp = make_response(render_template('login.html', success='Successfully logged out!'))
    resp.set_cookie('username', '', max_age=0)
    return resp


@app.route("/new_message", methods=['GET'])
def new_message():
    username = request.cookies.get('username')
    return render_template('new_message.html', username=username)


@app.route("/send_message", methods=['POST'])
def send_message():
    message = str(request.form['message'])
    me = str(request.form['from_user'])
    to_user = str(request.form['to_user'])

    resp = api.post(f"/{me}/messages", {'to': to_user, 'link': message})
    if resp.ok:
        session['success'] = "Message sent!"
        return redirect(url_for('home'))
    else:
        if resp.status_code == 400:
            return render_template('new_message.html', username=me, error=resp.json()['message'])

# TODO: archiving and viewing archive not yet implemented.
