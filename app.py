from flask import Flask, render_template, request, redirect, session, flash, url_for
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

# Editable settings with default values
settings = {
    'min_withdraw_amount': 150.00,
    'daily_login_reward': 0.50,
    'watch_reward_amount': 0.01
}

# Home page
@app.route('/')
def index():
    global visitor_count
    visitor_count += 1
    return render_template('index.html', videos=videos, visitors=visitor_count)

# Admin login
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin'] = True
            return redirect(url_for('dashboard'))  # Redirect to /dashboard after login
        flash("Wrong credentials")
    return render_template('login.html')

# Dashboard GET shows dashboard, POST updates settings
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        # Update settings from form inputs safely
        try:
            min_withdraw = float(request.form.get('min_withdraw_amount', settings['min_withdraw_amount']))
            daily_login = float(request.form.get('daily_login_reward', settings['daily_login_reward']))
            watch_reward = float(request.form.get('watch_reward_amount', settings['watch_reward_amount']))

            settings['min_withdraw_amount'] = min_withdraw
            settings['daily_login_reward'] = daily_login
            settings['watch_reward_amount'] = watch_reward
            flash("Settings updated successfully!")
        except ValueError:
            flash("Invalid input! Please enter valid numbers.")

    return render_template('dashboard.html', videos=videos, visitors=visitor_count, settings=settings)

# Upload video (admin only)
@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    video = request.files.get('video')
    title = request.form.get('title', 'Untitled')

    if not video or video.filename == '':
        flash("No video selected.")
        return redirect(url_for('dashboard'))

    filename = secure_filename(video.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    video.save(save_path)

    # Add video info with id for frontend if needed
    video_id = len(videos) + 1
    videos.append({'id': video_id, 'title': title, 'filename': filename})

    flash(f"Video '{title}' uploaded successfully!")
    return redirect(url_for('dashboard'))

# Logout route
@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash("Logged out successfully.")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
