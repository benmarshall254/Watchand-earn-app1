from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
import os, json, time
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # CHANGE in production

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
DATA_FILE = 'data.json'

# Initialize data.json
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            "visitors": 0,
            "videos": [],
            "users": {},
            "withdrawals": [],
            "ad_clicks": 0,
            "daily_login_reward": 0.005
        }, f, indent=2)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def count_visits():
    if request.endpoint not in ('static',):
        data = load_data()
        data['visitors'] += 1
        save_data(data)

@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', videos=data.get("videos", []))

@app.route('/watch/<video_id>')
def watch(video_id):
    data = load_data()
    video = next((v for v in data['videos'] if v['id'] == video_id), None)
    if not video:
        return "Video not found", 404
    return render_template('watch.html', video=video)

@app.route('/reward', methods=['POST'])
def reward():
    user_ip = request.remote_addr
    data = load_data()
    user = data['users'].get(user_ip, {
        "earnings": 0,
        "watched": [],
        "last_reward_time": 0,
        "last_login_date": "",
        "daily_rewarded": False
    })

    current_time = int(time.time())
    if current_time - user.get("last_reward_time", 0) >= 30:
        user["earnings"] += 0.001
        user["last_reward_time"] = current_time

    # Daily login bonus
    today_str = str(date.today())
    if user.get("last_login_date") != today_str and not user.get("daily_rewarded", False):
        reward_amount = data.get("daily_login_reward", 0.005)
        user["earnings"] += reward_amount
        user["last_login_date"] = today_str
        user["daily_rewarded"] = True

    data['users'][user_ip] = user
    save_data(data)
    return jsonify({"earnings": round(user["earnings"], 4)})

@app.route('/earnings')
def earnings():
    user_ip = request.remote_addr
    data = load_data()
    earnings = data['users'].get(user_ip, {}).get("earnings", 0)
    return jsonify({"earnings": round(earnings, 4)})

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    user_ip = request.remote_addr
    data = load_data()
    user = data['users'].get(user_ip, {
        "earnings": 0,
        "watched": [],
        "last_reward_time": 0
    })

    if request.method == 'POST':
        method = request.form['method']
        account = request.form['account']
        amount = float(user.get("earnings", 0))
        if amount >= 1:
            data['withdrawals'].append({
                "user": user_ip,
                "method": method,
                "account": account,
                "amount": round(amount, 4),
                "timestamp": str(datetime.now()),
                "status": "Pending"
            })
            user['earnings'] = 0
            data['users'][user_ip] = user
            save_data(data)
            return render_template('withdraw.html', message="Withdrawal requested!")
        else:
            return render_template('withdraw.html', message="Minimum $1 required.")
    return render_template('withdraw.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    data = load_data()

    # Admin can update daily login reward
    if request.method == 'POST':
        try:
            reward = float(request.form['daily_reward'])
            data['daily_login_reward'] = reward
            save_data(data)
            flash("Daily login reward updated.")
        except:
            flash("Invalid reward amount.")

    return render_template('dashboard.html',
                           videos=data.get("videos", []),
                           visitors=data.get("visitors", 0),
                           users=data.get("users", {}),
                           withdrawals=data.get("withdrawals", []),
                           daily_reward=data.get("daily_login_reward", 0.005))

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return redirect(url_for('dashboard'))
    file = request.files['video']
    if file.filename == '' or not allowed_file(file.filename):
        return redirect(url_for('dashboard'))
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    data = load_data()
    video_id = str(int(time.time()))
    data['videos'].append({
        "id": video_id,
        "filename": filename,
        "title": request.form.get("title", f"Video {video_id}"),
        "reward": 0.001
    })
    save_data(data)
    return redirect(url_for('dashboard'))

@app.route('/delete/<video_id>', methods=['POST'])
def delete_video(video_id):
    data = load_data()
    video = next((v for v in data['videos'] if v['id'] == video_id), None)
    if video:
        data['videos'].remove(video)
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], video['filename']))
        except FileNotFoundError:
            pass
        save_data(data)
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
