from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash from werkzeug.utils import secure_filename import os

app = Flask(name) app.secret_key = 'admin123'

UPLOAD_FOLDER = 'static/uploads' app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

Visitor counter

visitor_count = 0

In-memory data

users = { "user1": {"earnings": 0.50, "daily_login": False}, "user2": {"earnings": 1.75, "daily_login": False} } withdrawals = [] videos = [] youtuber_campaigns = [] watched_videos = {}  # Tracks which videos users have watched

Admin settings

def get_settings(): return { "reward_per_session": 0.001,  # USD earned per 30s watch "daily_login_reward": 0.2     # Reward for daily login after 60 seconds }

settings = get_settings()

-------------------- PUBLIC ROUTES --------------------

@app.route('/') def index(): global visitor_count visitor_count += 1 video_list = [{**video, "id": i} for i, video in enumerate(videos)] return render_template('index.html', videos=video_list, visitors=visitor_count)

@app.route('/earnings') def get_earnings(): return jsonify({"earnings": 1.25})

@app.route('/watch/int:video_id') def watch(video_id): user = session.get('user', 'anonymous') if user not in watched_videos: watched_videos[user] = set() if video_id in watched_videos[user]: return "Already watched and rewarded. No reward for repeat views.", 403

if 0 <= video_id < len(videos):
    watched_videos[user].add(video_id)
    return render_template('watch.html', video=videos[video_id], video_id=video_id, reward=settings["reward_per_session"])
return "Video not found", 404

@app.route('/check-daily-login') def check_daily_login(): user = session.get('user', 'anonymous') if user not in users: users[user] = {"earnings": 0.0, "daily_login": False}

if not users[user]['daily_login']:
    users[user]['daily_login'] = True
    users[user]['earnings'] += settings['daily_login_reward']
    return jsonify({"message": "Daily reward granted!", "reward": settings['daily_login_reward']})
return jsonify({"message": "Already claimed today."})

-------------------- ADMIN AUTH --------------------

@app.route('/admin-login', methods=['GET', 'POST']) def admin_login(): if request.method == 'POST': username = request.form['username'] password = request.form['password'] if username == 'admin' and password == 'admin': session['admin'] = True return redirect('/admin-dashboard') else: flash("Invalid credentials.") return render_template('login.html')

@app.route('/logout') def logout(): session.clear() return redirect('/')

-------------------- ADMIN DASHBOARD --------------------

@app.route('/admin-dashboard') def admin_dashboard(): if not session.get('admin'): return redirect('/admin-login') return render_template('dashboard.html', users=users, withdrawals=withdrawals, videos=videos, visitors=visitor_count, youtuber_campaigns=youtuber_campaigns, settings=settings)

@app.route('/update-settings', methods=['POST']) def update_settings(): if not session.get('admin'): return redirect('/admin-login') try: settings["reward_per_session"] = float(request.form['reward_per_session']) settings["daily_login_reward"] = float(request.form['daily_login_reward']) flash("Settings updated.") except: flash("Invalid input. Please enter a number.") return redirect('/admin-dashboard')

@app.route('/upload', methods=['POST']) def upload(): if not session.get('admin'): return redirect('/admin-login') if 'video' in request.files: video = request.files['video'] title = request.form['title'] thumbnail = request.form.get('thumbnail', '') filename = secure_filename(video.filename) path = os.path.join(app.config['UPLOAD_FOLDER'], filename) video.save(path) videos.append({"title": title, "filename": filename, "thumbnail": thumbnail}) return redirect('/admin-dashboard')

@app.route('/delete/int:vid_id', methods=['POST']) def delete_video(vid_id): if not session.get('admin'): return redirect('/admin-login') if 0 <= vid_id < len(videos): del videos[vid_id] return redirect('/admin-dashboard')

@app.route('/withdraw') def withdraw_page(): if not session.get('admin'): return redirect('/admin-login') return render_template('withdraw.html', withdrawals=withdrawals)

@app.route('/withdraw/int:req_id/approve', methods=['POST']) def approve_withdraw(req_id): if not session.get('admin'): return redirect('/admin-login') if 0 <= req_id < len(withdrawals): withdrawals[req_id]['status'] = 'approved' return redirect('/admin-dashboard')

@app.route('/withdraw/int:req_id/reject', methods=['POST']) def reject_withdraw(req_id): if not session.get('admin'): return redirect('/admin-login') if 0 <= req_id < len(withdrawals): withdrawals[req_id]['status'] = 'rejected' return redirect('/admin-dashboard')

-------------------- YOUTUBER SUBMISSION --------------------

@app.route('/youtuber-upload', methods=['GET', 'POST']) def youtuber_upload(): if request.method == 'POST': title = request.form['title'] youtube_link = request.form['youtube_link'] submitted_by = request.form['submitted_by'] youtuber_campaigns.append({ 'title': title, 'youtube_link': youtube_link, 'submitted_by': submitted_by, 'status': 'pending' }) return "Submitted" return render_template('youtuber_upload.html')

@app.route('/approve-campaign/int:index', methods=['POST']) def approve_campaign(index): if not session.get('admin'): return redirect('/admin-login') if 0 <= index < len(youtuber_campaigns): youtuber_campaigns[index]['status'] = 'approved' return redirect('/admin-dashboard')

@app.route('/reject-campaign/int:index', methods=['POST']) def reject_campaign(index): if not session.get('admin'): return redirect('/admin-login') if 0 <= index < len(youtuber_campaigns): youtuber_campaigns[index]['status'] = 'rejected' return redirect('/admin-dashboard')

-------------------- MAIN --------------------

if name == 'main': os.makedirs(UPLOAD_FOLDER, exist_ok=True) app.run(debug=True, port=5000)

