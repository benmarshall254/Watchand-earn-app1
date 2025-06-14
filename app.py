from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify from werkzeug.utils import secure_filename from datetime import datetime import os, json, pyrebase, smtplib from email.mime.text import MIMEText from email.mime.multipart import MIMEMultipart

Firebase config

firebase_config = { "apiKey": "AIzaSyBIC0u1HfE3aqI-_2aMJT9AKRqUEjlTEJ8", "authDomain": "surebet-prefictions.firebaseapp.com", "databaseURL": "", "projectId": "surebet-prefictions", "storageBucket": "surebet-prefictions.appspot.com", "messagingSenderId": "", "appId": "" }

firebase = pyrebase.initialize_app(firebase_config) auth = firebase.auth()

app = Flask(name) app.secret_key = 'admin123' app.config['SESSION_COOKIE_SECURE'] = True app.config['SESSION_COOKIE_SAMESITE'] = 'None' UPLOAD_FOLDER = 'static/uploads' app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER DATA_FILE = 'data.json' ADMIN_EMAIL = 'your_admin_email@example.com'

Load or initialize data

if os.path.exists(DATA_FILE): with open(DATA_FILE, 'r') as f: data = json.load(f) else: data = { "visitors": 0, "videos": [], "users": {}, "withdrawals": [], "daily_logins": {}, "ad_clicks": 0, "daily_login_reward": 0.005, "campaigns": [] }

def save_data(): with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=2)

def send_admin_email(subject, content): try: msg = MIMEMultipart() msg['From'] = 'noreply@yourdomain.com' msg['To'] = ADMIN_EMAIL msg['Subject'] = subject msg.attach(MIMEText(content, 'plain'))

server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('noreply@yourdomain.com', 'your_email_password')
    server.send_message(msg)
    server.quit()
except Exception as e:
    print("Email failed:", e)

@app.route('/') def home(): if 'admin' in session: return redirect('/admin-dashboard') elif 'user' in session: return redirect('/user-dashboard') return redirect('/login')

@app.route('/login', methods=['GET', 'POST']) def login(): if request.method == 'POST': username = request.form['username'].strip() password = request.form['password'].strip() if username == 'marshall' and password == 'forgot password': session.clear() session['admin'] = True return redirect('/admin-dashboard') elif username in data['users'] and password == data['users'][username]['password']: session.clear() session['user'] = username session['login_time'] = datetime.utcnow().isoformat() return redirect('/user-dashboard') else: flash("Invalid credentials.") return render_template('login.html')

@app.route('/register', methods=['GET', 'POST']) def register(): if request.method == 'POST': username = request.form['username'].strip() password = request.form['password'].strip() if username in data['users']: flash("Username already exists.") else: data['users'][username] = { "password": password, "earnings": 0.0, "watched": [], "last_reward_time": 0, "last_login_date": "", "daily_rewarded": False } save_data() flash("Account created. Please log in.") return redirect('/login') return render_template('register.html')

@app.route('/forgot-password', methods=['GET', 'POST']) def forgot_password(): if request.method == 'POST': email = request.form['email'].strip() try: auth.send_password_reset_email(email) flash("Password reset email sent. Check your inbox.") except Exception as e: flash("Error sending reset email. Please check the email or try again later.") return render_template('forgot_password.html')

@app.route('/logout') def logout(): session.clear() return redirect('/login')

@app.route('/user-dashboard') def user_dashboard(): if 'user' not in session: return redirect('/login') username = session['user'] earnings = data['users'][username]['earnings'] return render_template('index.html', videos=data['videos'], earnings=earnings)

@app.route('/admin-dashboard') def admin_dashboard(): if not session.get('admin'): return redirect('/login') return render_template('dashboard.html', users=data['users'], withdrawals=data['withdrawals'], videos=data['videos'], visitors=data['visitors'], youtuber_campaigns=data['campaigns'])

@app.route('/upload', methods=['POST']) def upload(): if not session.get('admin'): return redirect('/login') video = request.files['video'] title = request.form['title'] reward = float(request.form.get('reward', 0.0001)) thumbnail = request.files['thumbnail']

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

@app.route('/delete/int:index', methods=['POST']) def delete(index): if not session.get('admin'): return redirect('/login') if 0 <= index < len(data['videos']): del data['videos'][index] save_data() return redirect('/admin-dashboard')

@app.route('/withdraw', methods=['GET', 'POST']) def withdraw(): if 'user' not in session: return redirect('/login') username = session['user'] user_data = data['users'][username] earnings = user_data['earnings'] if request.method == 'POST': name = request.form['name'].strip() method = request.form['method'].strip() details = request.form['details'].strip() if earnings < 150: return render_template('withdraw.html', earnings=earnings, message="Minimum withdrawal is $150.") withdrawal = { "user": username, "name": name, "method": method, "details": details, "amount": earnings, "status": "pending", "time": datetime.utcnow().isoformat() } user_data['earnings'] = 0 data['withdrawals'].append(withdrawal) save_data() send_admin_email("New Withdrawal Request", f"User {username} requested ${earnings} via {method}. Details: {details}") return render_template('withdraw.html', earnings=0, message="✅ Withdrawal request sent! Await admin approval.") return render_template('withdraw.html', earnings=earnings)

if name == 'main': os.makedirs(UPLOAD_FOLDER, exist_ok=True) save_data() app.run(debug=True, port=5000)

