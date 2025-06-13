from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DATA_FILE = 'data.json'
VIDEO_LIST = [
    {"id": "1", "title": "Mini Video 1", "url": "/static/video1.mp4"},
    {"id": "2", "title": "Mini Video 2", "url": "/static/video2.mp4"}
]

# Initialize data.json if not exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            "earnings": {},
            "views": {},
            "visitors": {},
            "admin": {"username": "admin", "password": "1234"}
        }, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html', videos=VIDEO_LIST)

@app.route('/watch/<video_id>')
def watch(video_id):
    data = load_data()
    video = next((v for v in VIDEO_LIST if v['id'] == video_id), None)
    if not video:
        return redirect(url_for('index'))

    # Silent visitor tracking
    visitor_ip = request.remote_addr
    today = datetime.now().strftime('%Y-%m-%d')
    key = f"{video_id}_{today}"

    if key not in data["visitors"]:
        data["visitors"][key] = []

    if visitor_ip not in data["visitors"][key]:
        data["visitors"][key].append(visitor_ip)

    # Total view count (per video)
    data["views"][video_id] = data["views"].get(video_id, 0) + 1
    save_data(data)

    return render_template('watch.html', video=video)

@app.route('/reward', methods=['POST'])
def reward():
    data = load_data()
    user_ip = request.remote_addr
    data["earnings"][user_ip] = round(data["earnings"].get(user_ip, 0.0) + 0.0001, 5)
    save_data(data)
    return jsonify({"message": "Reward credited!"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = load_data()
        username = request.form['username']
        password = request.form['password']
        if username == data['admin']['username'] and password == data['admin']['password']:
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid login"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))
    data = load_data()
    views = data.get('views', {})
    visitors = {
        vid: len([ip for key, ips in data['visitors'].items() if key.startswith(vid) for ip in ips])
        for vid in views
    }
    return render_template('dashboard.html', videos=VIDEO_LIST, views=views, visitors=visitors)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
