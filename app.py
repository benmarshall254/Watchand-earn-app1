from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, make_response, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import os, json, datetime

# Optional Firebase support
import pyrebase
from firebase_config import firebase_config

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey123")

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'data.json'

# === Mail config (Gmail SMTP) ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bensonmwangi834@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your_app_password_here')  # set via Render.com
mail = Mail(app)

# === Load / Save Data ===
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

data = load_data()
users = data['users']
videos = data['videos']
withdrawals = data['withdrawals']
daily_logins = data.get('daily_logins', {})
reward_rules = data.get("reward_rules", [])
settings = data.get("settings", {})
visitor_count = data.get('visitors', 0)

# === Security Headers ===
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
    return response

# === ROUTES ===

@app.route('/')
def index():
    if 'firebase_user' not in session:
        flash("You must log in to access this page.")
        return redirect(url_for('login'))
    global visitor_count
    visitor_count += 1
    data['visitors'] = visitor_count
    save_data(data)
    return render_template('index.html', videos=videos)

@app.route('/rules-popup')
def rules_popup():
    if 'firebase_user' not in session:
        return redirect(url_for('login'))
    return render_template('rules_popup.html', rules=reward_rules)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot-password.html')

@app.route('/session-login', methods=['POST'])
def session_login():
    email = request.form.get('email')
    password = request.form.get('password')
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        session['firebase_user'] = email
        return jsonify({'message': 'Logged in successfully'}), 200
    except:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.pop('firebase_user', None)
    session.pop('admin', None)
    flash("Logged out successfully.")
    return redirect(url_for('login'))

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = users.get("admin")
        if username == "admin" and check_password_hash(admin["password"], password):
            session['admin'] = True
            return redirect(url_for('dashboard'))
        flash("Incorrect admin credentials.")
    return render_template("admin-login.html")

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        flash("Unauthorized access.")
        return redirect(url_for('admin_login'))
    return render_template('dashboard.html', videos=videos, users=users,
                           withdrawals=withdrawals, visitors=visitor_count,
                           settings=settings, rules=reward_rules)

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'firebase_user' not in session:
        return redirect(url_for('login'))
    email = session['firebase_user']
    user = users.get(email, {})
    if request.method == 'POST':
        method = request.form.get('method')
        account = request.form.get('account')
        amount = float(request.form.get('amount'))
        if amount >= data['min_withdraw_amount'] and user['earnings'] >= amount:
            withdrawal = {
                "user": email,
                "method": method,
                "account": account,
                "amount": amount,
                "date": str(datetime.datetime.now()),
                "status": "pending"
            }
            withdrawals.append(withdrawal)
            user['earnings'] -= amount
            save_data(data)
            flash("Withdrawal request submitted.")
        else:
            flash("Insufficient balance or below minimum withdrawal.")
    return render_template('withdraw.html', user=email, info=user)

@app.route('/submit-video', methods=['GET', 'POST'])
def submit_video():
    if 'firebase_user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title')
        url = request.form.get('url')
        if title and url:
            videos.append({"title": title, "url": url, "submitted_by": session['firebase_user']})
            save_data(data)
            flash("Video submitted for review.")
        else:
            flash("Title and URL required.")
    return render_template('submit_video.html')

@app.route('/watch/<int:video_id>')
def watch(video_id):
    if 'firebase_user' not in session:
        return redirect(url_for('login'))
    if 0 <= video_id < len(videos):
        video = videos[video_id]
        return render_template('watch.html', video=video)
    return render_template('404.html'), 404

@app.route('/profile')
def profile():
    if 'firebase_user' not in session:
        flash("Please log in to view your profile.")
        return redirect(url_for('login'))
    email = session['firebase_user']
    user_data = users.get(email)
    if not user_data:
        flash("User not found.")
        return redirect(url_for('logout'))
    if 'last_login_date' not in user_data:
        user_data['last_login_date'] = str(datetime.datetime.now().date())
    return render_template('profile.html', user=user_data)

@app.route('/send-welcome/<email>')
def send_welcome(email):
    try:
        msg = Message("Welcome to Watch & Earn", sender="bensonmwangi834@gmail.com", recipients=[email])
        msg.body = f"Hi {email}, welcome to Watch & Earn! Enjoy watching and earning today."
        mail.send(msg)
        return f"Email sent to {email}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# === Run Server ===
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=False)
