from flask import Flask, render_template, request, redirect, session, flash from werkzeug.utils import secure_filename from datetime import datetime, timedelta import os, json

app = Flask(name) app.secret_key = 'admin123'

For Render or HTTPS deployment

app.config['SESSION_COOKIE_SECURE'] = True app.config['SESSION_COOKIE_SAMESITE'] = 'None'

UPLOAD_FOLDER = 'static/uploads' app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

USERS_FILE = 'users.json'

Load or create users.json

if os.path.exists(USERS_FILE): with open(USERS_FILE, 'r') as f: users = json.load(f) else: users = { "user1": {"earnings": 0.50, "password": "pass123"}, "user2": {"earnings": 1.75, "password": "mypassword"} } with open(USERS_FILE, 'w') as f: json.dump(users, f)

withdrawals = [] videos = [] youtuber_campaigns = []

-------------------- HOME --------------------

@app.route('/') def home(): if 'admin' in session: return redirect('/admin-dashboard') elif 'user' in session: return redirect('/user-dashboard') return redirect('/login')

@app.route('/user-dashboard') def user_dashboard(): if 'user' not in session: return redirect('/login') username = session['user'] now = datetime.utcnow() if 'login_time' in session: elapsed = (now - session['login_time']).total_seconds() if elapsed > 30: users[username]['earnings'] += 0.01 * (elapsed // 30) with open(USERS_FILE, 'w') as f: json.dump(users, f) session['login_time'] = now else: session['login_time'] = now earnings = users.get(username, {}).get('earnings', 0.00) return render_template('index.html', videos=videos, earnings=earnings)

-------------------- LOGIN --------------------

@app.route('/login', methods=['GET', 'POST']) def login(): if request.method == 'POST': username = request.form['username'].strip() password = request.form['password'].strip()

if username.lower() == 'marshall' and password == 'forgot password':
        session.clear()
        session['admin'] = True
        return redirect('/admin-dashboard')

    elif username in users and password == users[username].get('password'):
        session.clear()
        session['user'] = username
        session['login_time'] = datetime.utcnow()
        return redirect('/user-dashboard')

    else:
        flash("Invalid credentials.")
return render_template('login.html')

@app.route('/register', methods=['GET', 'POST']) def register(): if request.method == 'POST': username = request.form['username'].strip() password = request.form['password'].strip() if username in users: flash("Username already exists.") else: users[username] = {"password": password, "earnings": 0.0} with open(USERS_FILE, 'w') as f: json.dump(users, f) flash("Account created. Please log in.") return redirect('/login') return render_template('register.html')

@app.route('/logout') def logout(): session.clear() return redirect('/login')

-------------------- ADMIN DASHBOARD --------------------

@app.route('/admin-dashboard') def admin_dashboard(): if not session.get('admin'): return redirect('/login') return render_template('dashboard.html', users=users, withdrawals=withdrawals, videos=videos, visitors=123, youtuber_campaigns=youtuber_campaigns)

@app.route('/upload', methods=['POST']) def upload(): if not session.get('admin'): return redirect('/login') if 'video' in request.files: video = request.files['video'] title = request.form['title'] thumb_file = request.files.get('thumbnail') thumbnail_path = '' if thumb_file: thumb_name = secure_filename(thumb_file.filename) thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], thumb_name) thumb_file.save(thumb_path) thumbnail_path = f"/static/uploads/{thumb_name}" filename = secure_filename(video.filename) path = os.path.join(app.config['UPLOAD_FOLDER'], filename) video.save(path) videos.append({ "title": title, "filename": filename, "thumbnail": thumbnail_path }) return redirect('/admin-dashboard')

@app.route('/delete/int:vid_id', methods=['POST']) def delete_video(vid_id): if not session.get('admin'): return redirect('/login') if 0 <= vid_id < len(videos): del videos[vid_id] return redirect('/admin-dashboard')

-------------------- WITHDRAWAL --------------------

@app.route('/withdraw') def withdraw_page(): if not session.get('admin'): return redirect('/login') return render_template('withdraw.html', withdrawals=withdrawals)

@app.route('/withdraw/int:req_id/approve', methods=['POST']) def approve_withdraw(req_id): if not session.get('admin'): return redirect('/login') if 0 <= req_id < len(withdrawals): withdrawals[req_id]['status'] = 'approved' return redirect('/admin-dashboard')

@app.route('/withdraw/int:req_id/reject', methods=['POST']) def reject_withdraw(req_id): if not session.get('admin'): return redirect('/login') if 0 <= req_id < len(withdrawals): withdrawals[req_id]['status'] = 'rejected' return redirect('/admin-dashboard')

-------------------- YOUTUBER CAMPAIGN --------------------

@app.route('/youtuber-upload', methods=['GET', 'POST']) def youtuber_upload(): if request.method == 'POST': title = request.form['title'] youtube_link = request.form['youtube_link'] submitted_by = request.form['submitted_by'] youtuber_campaigns.append({ 'title': title, 'youtube_link': youtube_link, 'submitted_by': submitted_by, 'status': 'pending' }) return "Submitted successfully" return render_template('youtuber_upload.html')

@app.route('/approve-campaign/int:index', methods=['POST']) def approve_campaign(index): if not session.get('admin'): return redirect('/login') if 0 <= index < len(youtuber_campaigns): youtuber_campaigns[index]['status'] = 'approved' return redirect('/admin-dashboard')

@app.route('/reject-campaign/int:index', methods=['POST']) def reject_campaign(index): if not session.get('admin'): return redirect('/login') if 0 <= index < len(youtuber_campaigns): youtuber_campaigns[index]['status'] = 'rejected' return redirect('/admin-dashboard')

-------------------- RULES --------------------

@app.route('/rules') def show_rules(): with open('rules.txt', 'r') as f: content = f.read() return render_template('rules.html', rules=content)

-------------------- WATCH VIDEO --------------------

@app.route('/watch/int:video_id') def watch(video_id): if 'user' not in session: return redirect('/login') if 0 <= video_id < len(videos): video = videos[video_id] return f"<h1>Watching: {video['title']}</h1><br><video src='/static/uploads/{video['filename']}' controls width='600'></video>" return "Video not found"

-------------------- SERVER --------------------

if name == 'main': os.makedirs(UPLOAD_FOLDER, exist_ok=True) app.run(debug=True, port=5000)

