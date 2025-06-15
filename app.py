from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os
import json
import datetime

app = Flask(__name__)
app.secret_key = 'admin123'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'data.json'

# --- Helper Functions ---

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({
                "videos": [],
                "users": {
                    "admin": {
                        "password": generate_password_hash("admin123"),
                        "email": "admin@example.com",
                        "joined": str(datetime.datetime.now()),
                        "earnings": 0,
                        "watched": [],
                        "withdrawals": []
                    },
                    "bensonmwangi834@gmail.com": {
                        "password": generate_password_hash("mypassword"),
                        "email": "bensonmwangi834@gmail.com",
                        "joined": str(datetime.datetime.now()),
                        "earnings": 0,
                        "watched": [],
                        "withdrawals": []
                    }
                },
                "visitors": 0,
                "withdrawals": [],
                "youtuber_requests": [],
                "daily_logins": {},
                "min_withdraw_amount": 150.0,
                "daily_login_reward": 0.5,
                "watch_reward_amount": 0.01,
                "reward_rules": [
                    "Time-based earnings start after 30 seconds of watching.",
                    "Daily login rewards are earned after 60 seconds online.",
                    "Reward Rules are shown in three places and are editable by Ben."
                ],
                "settings": {
                    "enable_rewards": True,
                    "maintenance_mode": False
                }
            }, f)
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# --- Load App Data ---
data = load_data()
users = data['users']
videos = data['videos']
visitor_count = data.get('visitors', 0)
withdrawals = data.get('withdrawals', [])
daily_logins = data.get('daily_logins', {})
reward_rules = data.get("reward_rules", [])
settings = data.get("settings", {})

# --- Routes ---

@app.route('/')
def index():
    global visitor_count
    visitor_count += 1
    data['visitors'] = visitor_count
    save_data(data)
    if session.get('user') and session.pop('show_rules', False):
        return redirect(url_for('rules_popup'))
    return render_template('index.html', videos=videos, visitors=visitor_count)

@app.route('/rules-popup')
def rules_popup():
    return render_template('rules_popup.html', rules=reward_rules)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form['username']
        password = request.form['password']

        # Try to find user by username, email, or phone
        user = users.get(user_input)
        if not user:
            for uname, u in users.items():
                if u.get("email") == user_input or u.get("phone") == user_input:
                    user = u
                    user_input = uname
                    break

        if user and (password == user['password'] or check_password_hash(user['password'], password)):
            session['user'] = user_input
            session['show_rules'] = True
            return redirect(url_for('index'))
        flash("Invalid login details.")
    return render_template('login.html')

@app.route('/forgot-password')
def forgot_password():
    flash("Password reset feature coming soon.")
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('login'))

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_user = users.get('admin', {})
        if username == 'admin' and (password == admin_user.get('password') or check_password_hash(admin_user.get('password', ''), password)):
            session['admin'] = True
            return redirect(url_for('dashboard'))
        flash("Wrong credentials")
    return render_template('admin-login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    return render_template('admin-dashboard.html', videos=videos, users=users, withdrawals=withdrawals)

# Add other necessary routes like: /upload, /withdraw, /admin/review, etc.

# --- Run App ---
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
