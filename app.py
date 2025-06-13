from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'admin123'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory data
users = {
    "user1": {"earnings": 0.50},
    "user2": {"earnings": 1.75}
}
withdrawals = []
videos = []
youtuber_campaigns = []

# -------------------- HOME --------------------

@app.route('/')
def home():
    if 'admin' in session:
        return redirect('/admin-dashboard')
    elif 'user' in session:
        return redirect('/index')
    return redirect('/login')

@app.route('/index')
def index():
    if 'user' not in session:
        return redirect('/login')
    username = session['user']
    earnings = users.get(username, {}).get('earnings', 0.00)
    return render_template('index.html', videos=videos, earnings=earnings)

# -------------------- LOGIN --------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if username == 'admin' and password == 'admin':
            session.clear()
            session['admin'] = True
            return redirect('/admin-dashboard')

        elif username in users:
            session.clear()
            session['user'] = username
            return redirect('/index')

        else:
            flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -------------------- ADMIN DASHBOARD --------------------

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('dashboard.html', users=users, withdrawals=withdrawals,
                           videos=videos, visitors=123, youtuber_campaigns=youtuber_campaigns)

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect('/login')
    if 'video' in request.files:
        video = request.files['video']
        title = request.form['title']
        thumbnail = request.form.get('thumbnail', '')
        filename = secure_filename(video.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video.save(path)
        videos.append({
            "id": len(videos),
            "title": title,
            "filename": filename,
            "thumbnail": thumbnail
        })
    return redirect('/admin-dashboard')

@app.route('/delete/<int:vid_id>', methods=['POST'])
def delete_video(vid_id):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= vid_id < len(videos):
        del videos[vid_id]
    return redirect('/admin-dashboard')

# -------------------- WITHDRAWAL --------------------

@app.route('/withdraw')
def withdraw_page():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('withdraw.html', withdrawals=withdrawals)

@app.route('/withdraw/<int:req_id>/approve', methods=['POST'])
def approve_withdraw(req_id):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= req_id < len(withdrawals):
        withdrawals[req_id]['status'] = 'approved'
    return redirect('/admin-dashboard')

@app.route('/withdraw/<int:req_id>/reject', methods=['POST'])
def reject_withdraw(req_id):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= req_id < len(withdrawals):
        withdrawals[req_id]['status'] = 'rejected'
    return redirect('/admin-dashboard')

# -------------------- YOUTUBER CAMPAIGN --------------------

@app.route('/youtuber-upload', methods=['GET', 'POST'])
def youtuber_upload():
    if request.method == 'POST':
        title = request.form['title']
        youtube_link = request.form['youtube_link']
        submitted_by = request.form['submitted_by']
        youtuber_campaigns.append({
            'title': title,
            'youtube_link': youtube_link,
            'submitted_by': submitted_by,
            'status': 'pending'
        })
        return "Submitted successfully"
    return '''
        <form method="POST">
            <input name='title' placeholder='Video Title'><br>
            <input name='youtube_link' placeholder='YouTube URL'><br>
            <input name='submitted_by' placeholder='Your Email'><br>
            <button type='submit'>Submit</button>
        </form>
    '''

@app.route('/approve-campaign/<int:index>', methods=['POST'])
def approve_campaign(index):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= index < len(youtuber_campaigns):
        youtuber_campaigns[index]['status'] = 'approved'
    return redirect('/admin-dashboard')

@app.route('/reject-campaign/<int:index>', methods=['POST'])
def reject_campaign(index):
    if not session.get('admin'):
        return redirect('/login')
    if 0 <= index < len(youtuber_campaigns):
        youtuber_campaigns[index]['status'] = 'rejected'
    return redirect('/admin-dashboard')

# -------------------- WATCH VIDEO --------------------

@app.route('/watch/<int:video_id>')
def watch(video_id):
    if 'user' not in session:
        return redirect('/login')
    if 0 <= video_id < len(videos):
        video = videos[video_id]
        return f"<h1>Watching: {video['title']}</h1><br><video src='/static/uploads/{video['filename']}' controls width='600'></video>"
    return "Video not found"

# -------------------- SERVER --------------------

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)
