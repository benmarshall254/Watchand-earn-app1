from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'admin123'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Sample data
videos = []
users = {'testuser': {'earnings': 0.0, 'daily_login': False}}
visitor_count = 0

@app.route('/')
def index():
    global visitor_count
    visitor_count += 1
    return render_template('index.html', videos=videos, visitors=visitor_count)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin'] = True
            return redirect('/admin-dashboard')
        flash("Wrong credentials")
    return render_template('login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin-login')
    return render_template('dashboard.html', videos=videos)

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect('/admin-login')
    video = request.files['video']
    title = request.form['title']
    filename = secure_filename(video.filename)
    video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    videos.append({'title': title, 'filename': filename})
    return redirect('/admin-dashboard')

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
