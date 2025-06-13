from flask import Flask, render_template, request, redirect, session, jsonify import json import os from datetime import datetime

app = Flask(name) app.secret_key = 'supersecretkey'

DATA_FILE = 'data.json' ADMIN_PASSWORD = 'admin123'  # You can change this later ADSENSE_CODE = """

<!-- Google AdSense --><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6332657251575161"
     crossorigin="anonymous"></script><!-- Ad Slot --><ins class="adsbygoogle"
style="display:block"
data-ad-client="ca-pub-6332657251575161"
data-ad-slot="8486290217"
data-ad-format="auto"
data-full-width-responsive="true"></ins>

<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>"""

def load_data(): if not os.path.exists(DATA_FILE): return {} with open(DATA_FILE, 'r') as f: return json.load(f)

def save_data(data): with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)

@app.route('/') def index(): if 'username' not in session: session['username'] = f'user_{datetime.utcnow().timestamp()}' return render_template('index.html', adsense_code=ADSENSE_CODE)

@app.route('/watch/<video_id>') def watch(video_id): return render_template('watch.html', video_id=video_id)

@app.route('/reward', methods=['POST']) def reward(): username = session.get('username') if not username: return jsonify({"success": False, "error": "Not logged in"}), 403

data = load_data()
if username not in data:
    data[username] = 0.0

data[username] += 0.0001  # $0.0001 reward
save_data(data)
return jsonify({"success": True, "balance": data[username]})

@app.route('/admin', methods=['GET', 'POST']) def admin(): if request.method == 'POST': password = request.form.get('password') if password == ADMIN_PASSWORD: session['is_admin'] = True return redirect('/dashboard') return ''' <form method="POST"> <input type="password" name="password" placeholder="Enter admin password" required /> <button type="submit">Login</button> </form> '''

@app.route('/dashboard') def dashboard(): if not session.get('is_admin'): return redirect('/admin') data = load_data() return '<h1>Admin Dashboard</h1>' + '<br>'.join([f"{user}: ${balance:.6f}" for user, balance in data.items()])

if name == 'main': app.run(debug=True)

