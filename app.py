from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import os, json

app = Flask(__name__)
app.secret_key = 'admin123'

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'data.json'

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
else:
    data = {
        "visitors": 0,
        "videos": [],
        "users": {},
        "withdrawals": [],
        "daily_logins": {},
        "ad_clicks": 0,
        "daily_login_reward": 0.005,
        "campaigns": []
    }

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def home():
    if 'admin' in session:
        return redirect('/admin-dashboard')
    elif 'user' in session:
        return redirect('/user-dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if username == 'marshall' and password == 'forgot password':
            session.clear()
            session['admin'] = True
            return redirect('/admin-dashboard')
        elif username in data['users'] and password == data['users'][username]['password']:
            session.clear()
            session['user'] = username
            session['login_time'] = datetime.utcnow().isoformat()
            return redirect('/user-dashboard')
        else:
            flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if username in data['users']:
            flash("Username already exists.")
        else:
            data['users'][username] = {
                "password": password,
                "earnings": 0.0,
                "watched": [],
                "last_reward_time": 0,
                "last_login_date": "",
                "daily_rewarded": False
            }
            save_data()
            flash("Account created. Please log in.")
            return redirect('/login')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/user-dashboard')
def user_dashboard():
    if 'user' not in session:
        return redirect('/login')
    username = session['user']
    earnings = data['users'][username]['earnings']
    return render_template('index.html', videos=data['videos'], earnings=earnings)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('dashboard.html',
                           users=data['users'],
                           withdrawals=data['withdrawals'],
                           videos=data['videos'],
                           visitors=data['visitors'],
                           youtuber_campaigns=data['campaigns'])

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect('/login')
    video = request.files['video']
    title = request.form['title']
    reward = float(request.form.get('reward', 0.0001))
    thumbnail = request.files['thumbnail']

    filename = secure_filename(video.filename)
    video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    thumbname = secure_filename(thumbnail.filename)
    thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbname))

    video_data = {
        "id": str(len(data['videos']) + 1),
        "title": title,
        "filename": filename,
        "thumbnail": thumbname,
        "reward": reward
    }
    data['videos'].append(video_data)
    save_data()
    return redirect('/admin-dashboard')

@app.route('/delete/<int:index>', methods=['POST'])
def delete(index):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= index < len(data['videos']):
        del data['videos'][index]
        save_data()
    return redirect('/admin-dashboard')

@app.route('/approve-campaign/<int:index>', methods=['POST'])
def approve_campaign(index):
    if 0 <= index < len(data['campaigns']):
        data['campaigns'][index]['status'] = 'approved'
        save_data()
    return redirect('/admin-dashboard')

@app.route('/reject-campaign/<int:index>', methods=['POST'])
def reject_campaign(index):
    if 0 <= index < len(data['campaigns']):
        data['campaigns'][index]['status'] = 'rejected'
        save_data()
    return redirect('/admin-dashboard')

@app.route('/withdraw/<int:index>/approve', methods=['POST'])
def approve_withdraw(index):
    if 0 <= index < len(data['withdrawals']):
        data['withdrawals'][index]['status'] = 'approved'
        save_data()
    return redirect('/admin-dashboard')

@app.route('/withdraw/<int:index>/reject', methods=['POST'])
def reject_withdraw(index):
    if 0 <= index < len(data['withdrawals']):
        data['withdrawals'][index]['status'] = 'rejected'
        save_data()
    return redirect('/admin-dashboard')

@app.route('/watch/<int:video_id>')
def watch(video_id):
    if 'user' not in session:
        return redirect('/login')
    for v in data['videos']:
        if int(v['id']) == video_id:
            return render_template('watch.html', video=v)
    return "Video not found"

@app.route('/reward/<int:video_id>', methods=['POST'])
def reward(video_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    username = session['user']
    for v in data['videos']:
        if int(v['id']) == video_id:
            if video_id not in data['users'][username]['watched']:
                data['users'][username]['earnings'] += v['reward']
                data['users'][username]['watched'].append(video_id)
                save_data()
            break
    return jsonify({"status": "ok", "earnings": data['users'][username]['earnings']})

@app.route('/withdraw')
def manual_withdraw_page():
    return "<h2>Manual Withdrawal Instructions</h2><p>PayPal/M-Pesa steps here.</p>"

# -------------- Run Server --------------
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    save_data()
    app.run(debug=True, port=5000)
