from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os
import json
from datetime import datetime

app = Flask(__name__)  # FIXED: __name__ instead of name
app.secret_key = 'admin123'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'data.json'

# --- Helper Functions ---

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_rules():
    try:
        with open('rules.txt', 'r') as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return ["No reward rules found."]

def save_rules(new_rules):
    with open('rules.txt', 'w') as f:
        f.write('\n'.join(new_rules))

# --- Load Data on Startup ---

data = load_data()
videos = data['videos']
users = data['users']
visitor_count = data['visitors']
withdrawals = data['withdrawals']
youtuber_requests = data.get('youtuber_requests', [])
settings = {
    'min_withdraw_amount': data.get('min_withdraw_amount', 150.0),
    'daily_login_reward': data.get('daily_login_reward', 0.5),
    'watch_reward_amount': data.get('watch_reward_amount', 0.01)
}

# --- Home ---

@app.route('/')
def index():
    global visitor_count
    visitor_count += 1
    data['visitors'] = visitor_count

    if session.get('user'):
        username = session['user']
        today = datetime.now().strftime('%Y-%m-%d')
        user = users.get(username)
        if user.get('last_login_date') != today:
            user['earnings'] += settings['daily_login_reward']
            user['last_login_date'] = today
            save_data(data)
        if session.pop('show_rules', False):
            return redirect(url_for('rules_popup'))

    save_data(data)
    return render_template('index.html', videos=videos, visitors=visitor_count)

# --- Login ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and (password == user['password'] or check_password_hash(user['password'], password)):
            session['user'] = username
            session['show_rules'] = True
            return redirect(url_for('index'))
        flash("Invalid login details.")
    return render_template('login.html')

# --- Register ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash("User already exists.")
        else:
            users[username] = {
                'password': generate_password_hash(password),
                'earnings': 0,
                'watched': [],
                'last_login_date': ""
            }
            save_data(data)
            flash("Account created. Please log in.")
            return redirect(url_for('login'))
    return render_template('register.html')

# --- Admin Login ---

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and (
            password == users['admin']['password'] or check_password_hash(users['admin']['password'], password)
        ):
            session['admin'] = True
            return redirect(url_for('dashboard'))
        flash("Wrong credentials")
    return render_template('login.html')

# --- Logout ---

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('user', None)
    flash("Logged out successfully.")
    return redirect(url_for('login'))

# --- Admin Dashboard ---

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        try:
            settings['min_withdraw_amount'] = float(request.form['min_withdraw_amount'])
            settings['daily_login_reward'] = float(request.form['daily_login_reward'])
            settings['watch_reward_amount'] = float(request.form['watch_reward_amount'])
            data['min_withdraw_amount'] = settings['min_withdraw_amount']
            data['daily_login_reward'] = settings['daily_login_reward']
            data['watch_reward_amount'] = settings['watch_reward_amount']
            save_data(data)
            flash("Settings updated successfully!")
        except ValueError:
            flash("Invalid input! Please enter valid numbers.")

    return render_template('dashboard.html', videos=videos, visitors=visitor_count, settings=settings, withdrawals=withdrawals, youtuber_requests=youtuber_requests)

# --- Upload Video (Admin Only) ---

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
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    video.save(path)

    video_id = str(len(videos) + 1)
    videos.append({
        'id': video_id,
        'title': title,
        'filename': filename,
        'thumbnail': 'default.jpg',
        'reward': settings['watch_reward_amount']
    })
    save_data(data)
    flash(f"Video '{title}' uploaded successfully!")
    return redirect(url_for('dashboard'))

# --- Reward After Watch ---

@app.route('/reward/<video_id>', methods=['POST'])
def reward(video_id):
    username = session.get('user')
    if not username:
        return redirect(url_for('login'))

    user = users.get(username)
    if video_id not in user['watched']:
        user['earnings'] += settings['watch_reward_amount']
        user['watched'].append(video_id)
        save_data(data)
    return jsonify({'status': 'rewarded'})

# --- Withdraw Request (User) ---

@app.route('/withdraw', methods=['GET', 'POST'])
def request_withdrawal():
    if not session.get('user'):
        return redirect(url_for('login'))

    username = session['user']
    user = users.get(username)

    if request.method == 'POST':
        if user['earnings'] < settings['min_withdraw_amount']:
            flash("Minimum $150 required.")
        else:
            withdrawals.append({
                'username': username,
                'amount': user['earnings'],
                'status': 'pending'
            })
            user['earnings'] = 0
            save_data(data)
            flash("Withdrawal request submitted.")
        return redirect(url_for('request_withdrawal'))

    return render_template('withdraw.html', balance=user['earnings'])

# --- Withdraw Approve/Reject ---

@app.route('/withdraw/<int:index>/approve', methods=['POST'])
def approve_withdraw(index):
    if session.get('admin'):
        withdrawals[index]['status'] = 'approved'
        save_data(data)
        flash("Withdrawal approved.")
    return redirect(url_for('dashboard'))

@app.route('/withdraw/<int:index>/reject', methods=['POST'])
def reject_withdraw(index):
    if session.get('admin'):
        withdrawals[index]['status'] = 'rejected'
        save_data(data)
        flash("Withdrawal rejected.")
    return redirect(url_for('dashboard'))

@app.route('/withdrawal-count')
def withdrawal_count():
    return jsonify({'count': len(withdrawals)})

# --- Admin Change Password ---

@app.route('/admin/password', methods=['GET', 'POST'])
def change_password():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        current = request.form['current_password']
        new = request.form['new_password']
        stored = users['admin']['password']
        if current == stored or check_password_hash(stored, current):
            users['admin']['password'] = generate_password_hash(new)
            save_data(data)
            flash("Password changed successfully.")
        else:
            flash("Current password is incorrect.")
        return redirect(url_for('change_password'))

    return render_template('password.html')

# --- Rules Display (Popup) ---

@app.route('/rules-popup')
def rules_popup():
    rule_lines = load_rules()
    return render_template('rules_popup.html', rules=rule_lines)

# --- Admin Edit Reward Rules ---

@app.route('/admin/rules', methods=['GET', 'POST'])
def edit_rules():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        new_rules = request.form.get('rules', '').strip().splitlines()
        save_rules(new_rules)
        flash("Rules updated successfully!")
        return redirect(url_for('edit_rules'))

    current_rules = '\n'.join(load_rules())
    return render_template('edit_rules.html', rules=current_rules)

# --- User Profile Page ---

@app.route('/profile')
def profile():
    if not session.get('user'):
        return redirect(url_for('login'))

    username = session['user']
    user_data = users.get(username, {})
    return render_template('profile.html', user=user_data)

# --- YouTuber Submission Page ---

@app.route('/submit-video', methods=['GET', 'POST'])
def submit_video():
    if request.method == 'POST':
        title = request.form.get('title')
        link = request.form.get('link')
        email = request.form.get('email')
        views = request.form.get('views')
        youtuber_requests.append({
            'title': title,
            'link': link,
            'email': email,
            'views': views,
            'status': 'pending'
        })
        data['youtuber_requests'] = youtuber_requests
        save_data(data)
        flash("Submission received! We will contact you.")
        return redirect(url_for('submit_video'))
    return render_template('submit_video.html')

# --- Payment Page ---

@app.route('/pay')
def pay():
    return render_template('pay.html')

# --- Run App ---

if __name__ == '__main__':  # FIXED: __name__ == '__main__'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
