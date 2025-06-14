from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os, json, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pyrebase

# 🔧 Firebase Config (Add full details for production)
firebase_config = {
    "apiKey": "AIzaSyBIC0u1HfE3aqI-_2aMJT9AKRqUEjlTEJ8",
    "authDomain": "surebet-prefictions.firebaseapp.com",
    "databaseURL": "",
    "projectId": "surebet-prefictions",
    "storageBucket": "surebet-prefictions.appspot.com",
    "messagingSenderId": "",
    "appId": ""
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# 🔐 Flask App Setup
app = Flask(__name__)
app.secret_key = 'admin123'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'data.json'
ADMIN_EMAIL = 'your_admin_email@example.com'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 📦 Load or Initialize Data
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

# 📧 Send Email to Admin
def send_admin_email(subject, content):
    try:
        msg = MIMEMultipart()
        msg['From'] = 'noreply@yourdomain.com'
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('noreply@yourdomain.com', 'your_email_password')  # Use env vars in production
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("❌ Email failed:", e)

# 🔔 Serve Notification Sound
@app.route('/notify.mp3')
def serve_notification_sound():
    return send_from_directory('static', 'notify.mp3')

# 🔁 Withdrawal Count (used for notification badge)
@app.route('/withdrawal-count')
def withdrawal_count():
    return jsonify({"count": len(data['withdrawals'])})

# 🗑️ Delete Video (Admin Only)
@app.route('/delete/<int:index>', methods=['POST'])
def delete(index):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= index < len(data['videos']):
        del data['videos'][index]
        save_data()
    return redirect('/admin-dashboard')

# ✅ Example Homepage (Expand as needed)
@app.route('/')
def home():
    data['visitors'] += 1
    save_data()
    return render_template('index.html')

# 👤 Admin Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'admin@example.com' and password == 'admin123':  # Replace with real credentials
            session['admin'] = True
            return redirect('/admin-dashboard')
        flash('Invalid login')
    return render_template('login.html')

# 👋 Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# 🎯 Admin Dashboard
@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('admin-dashboard.html', videos=data['videos'], withdrawals=data['withdrawals'])

# ⬆️ Upload Video
@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect('/login')
    if 'video' not in request.files:
        flash('No file part')
        return redirect('/admin-dashboard')
    file = request.files['video']
    if file.filename == '':
        flash('No selected file')
        return redirect('/admin-dashboard')
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    data['videos'].append({
        "filename": filename,
        "upload_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_data()
    return redirect('/admin-dashboard')

# 🚀 Start Local Server
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    save_data()
    app.run(debug=True, port=5000)
