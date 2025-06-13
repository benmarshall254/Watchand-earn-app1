from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'data.json'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load or initialize video data
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

def load_videos():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_videos(videos):
    with open(DATA_FILE, 'w') as f:
        json.dump(videos, f)

@app.route('/')
def index():
    videos = load_videos()
    return render_template('index.html', videos=videos)

@app.route('/watch/<video>')
def watch(video):
    return render_template('watch.html', video=video)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/dashboard')
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('admin'):
        return redirect('/login')
    videos = load_videos()
    return render_template('dashboard.html', videos=videos)

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect('/login')
    file = request.files['video']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        videos = load_videos()
        videos.append(filename)
        save_videos(videos)
    return redirect('/dashboard')

@app.route('/delete/<filename>')
def delete(filename):
    if not session.get('admin'):
        return redirect('/login')
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    videos = load_videos()
    videos = [v for v in videos if v != filename]
    save_videos(videos)
    return redirect('/dashboard')

@app.route('/uploads/<filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
