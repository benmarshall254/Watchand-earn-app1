from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os
import json
import datetime

app = Flask(__name__)
app.secret_key = 'admin123'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'data.json'

# --- Helper Functions ---

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({"videos": [], "users": {"admin": {"password": generate_password_hash("admin123")}}, "visitors": 0, "withdrawals": []}, f)
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

def calculate_profit():
    ad_revenue = data.get("ad_clicks", 0) * 0.01
    total_earnings_paid = sum([u.get("earnings", 0) for u in users.values()])
    return ad_revenue - total_earnings_paid

def get_user_growth_data():
    growth = {}
    for u in users.values():
        date = u.get('joined', '')[:10]
        if date:
            growth[date] = growth.get(date, 0) + 1
    dates = sorted(growth)
    counts = [growth[d] for d in dates]
    return dates, counts

def get_withdrawal_stats():
    date_totals = {}
    for w in withdrawals:
        if 'date' in w and w.get('status') == 'approved':
            d = w['date'][:10]
            date_totals[d] = date_totals.get(d, 0) + float(w['amount'])
    dates = sorted(date_totals)
    amounts = [date_totals[d] for d in dates]
    return dates, amounts

# --- Load Data ---
data = load_data()
videos = data.get('videos', [])
users = data.get('users', {})
visitor_count = data.get('visitors', 0)
withdrawals = data.get('withdrawals', [])
youtuber_requests = data.get('youtuber_requests', [])
daily_logins = data.get("daily_logins", {})
settings = {
    'min_withdraw_amount': data.get('min_withdraw_amount', 150.0),
    'daily_login_reward': data.get('daily_login_reward', 0.5),
    'watch_reward_amount': data.get('watch_reward_amount', 0.01)
}

# --- Routes ---

@app.route('/')
def index():
    global visitor_count
    visitor_count += 1
    data['visitors'] = visitor_count
    save_data(data)
    if session.get('user') and session.pop('show_rules', False):
        return redirect(url_for('rules_popup'))
    return render_template('index.html', videos=videos, visitors=visitor_count)

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

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_user = users.get('admin', {})
        if username == 'admin' and (password == admin_user.get('password') or check_password_hash(admin_user.get('password', ''), password)):
            session['admin'] = True
            return redirect(url_for('dashboard'))
        flash("Wrong credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('login'))

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

    user_list = sorted(users.items(), key=lambda x: x[1].get("earnings", 0), reverse=True)
    profit = calculate_profit()
    user_growth_dates, user_growth_counts = get_user_growth_data()
    withdrawal_dates, withdrawal_amounts = get_withdrawal_stats()

    return render_template('dashboard.html',
        videos=videos,
        settings=settings,
        withdrawals=withdrawals,
        youtuber_requests=youtuber_requests,
        visitors=visitor_count,
        users=user_list,
        profit=profit,
        user_growth_dates=user_growth_dates,
        user_growth_counts=user_growth_counts,
        withdrawal_amounts=withdrawal_amounts
    )

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
        'thumbnail': '',
        'reward': settings['watch_reward_amount']
    })
    save_data(data)

    flash(f"Video '{title}' uploaded successfully!")
    return redirect(url_for('dashboard'))

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

@app.route('/rules-popup')
def rules_popup():
    rule_lines = load_rules()
    return render_template('rules_popup.html', rules=rule_lines)

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

@app.route('/profile')
def profile():
    if not session.get('user'):
        return redirect(url_for('login'))
    username = session['user']
    user_data = users.get(username, {})
    return render_template('profile.html', user=user_data)

@app.route('/submit-video', methods=['GET', 'POST'])
def submit_video():
    if request.method == 'POST':
        youtuber_requests.append({
            'title': request.form.get('title'),
            'link': request.form.get('link'),
            'email': request.form.get('email'),
            'views': request.form.get('views'),
            'status': 'pending'
        })
        data['youtuber_requests'] = youtuber_requests
        save_data(data)
        flash("Submission received! We will contact you.")
        return redirect(url_for('submit_video'))
    return render_template('submit_video.html')

@app.route('/pay')
def pay():
    return render_template('pay.html')

@app.route('/download-report')
def download_report():
    with open(DATA_FILE, 'rb') as f:
        return send_file(f, download_name="report.json", as_attachment=True)

# --- Run ---
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
