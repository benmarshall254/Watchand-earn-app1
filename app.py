from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os, json, pyrebase, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Firebase Config
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

app = Flask(__name__)
app.secret_key = 'admin123'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'data.json'
ADMIN_EMAIL = 'your_admin_email@example.com'

# Load data
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

def send_admin_email(subject, content):
    try:
        msg = MIMEMultipart()
        msg['From'] = 'noreply@yourdomain.com'
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('noreply@yourdomain.com', 'your_email_password')
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email failed:", e)

# ✅ Serve notification sound
@app.route('/noty.mp3')
def serve_notification_sound():
    return send_from_directory('static', 'noty.mp3')

# ✅ Withdrawal count route (Step 2)
@app.route('/withdrawal-count')
def withdrawal_count():
    return jsonify({"count": len(data['withdrawals'])})

# 👇 Your other routes go here (already correct, skip duplication)
# home, login, register, forgot-password, logout
# user-dashboard, admin-dashboard, upload

# ✅ Fixed delete route
@app.route('/delete/<int:index>', methods=['POST'])
def delete(index):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= index < len(data['videos']):
        del data['videos'][index]
        save_data()
    return redirect('/admin-dashboard')

# Withdraw route (already correct)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    save_data()
    app.run(debug=True, port=5000)
