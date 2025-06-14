from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
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

# Admin settings
def get_settings():
    return {
        "reward_per_session": 0.001  # USD earned per 30s watch
    }

settings = get_settings()

# Add some sample videos for testing
videos = [
    {"title": "Sample Video 1", "filename": "sample1.mp4", "thumbnail": ""},
    {"title": "Sample Video 2", "filename": "sample2.mp4", "thumbnail": ""}
]

# Add some sample data for testing
youtuber_campaigns = [
    {
        'title': 'Sample YouTube Video 1',
        'youtube_link': 'https://youtube.com/watch?v=sample1',
        'submitted_by': 'creator1@email.com',
        'status': 'pending'
    }
]

withdrawals = [
    {
        'user': 'user1',
        'amount': 5.00,
        'status': 'pending'
    }
]

# -------------------- PUBLIC ROUTES --------------------

@app.route('/')
def index():
    # Return a simple HTML page if templates don't exist
    try:
        video_list = []
        for i, video in enumerate(videos):
            video_list.append({**video, "id": i})
        return render_template('index.html', videos=video_list)
    except:
        # Fallback HTML if template doesn't exist
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Video Platform</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .video { border: 1px solid #ddd; padding: 10px; margin: 10px 0; }
                a { color: #007bff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>Welcome to Video Platform</h1>
            <h2>Available Videos:</h2>
            ''' + ''.join([f'<div class="video"><h3>{video["title"]}</h3><a href="/watch/{i}">Watch Video</a></div>' 
                          for i, video in enumerate(videos)]) + '''
            <hr>
            <p><a href="/admin-login">Admin Login</a></p>
            <p><a href="/youtuber-upload">Submit YouTube Video</a></p>
        </body>
        </html>
        '''

@app.route('/earnings')
def get_earnings():
    return jsonify({"earnings": 1.25})

@app.route('/watch/<int:video_id>')
def watch(video_id):
    if 0 <= video_id < len(videos):
        try:
            return render_template('watch.html', 
                                 video=videos[video_id], 
                                 video_id=video_id, 
                                 reward=settings["reward_per_session"])
        except:
            # Fallback HTML if template doesn't exist
            video = videos[video_id]
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{video["title"]}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .video-container {{ text-align: center; }}
                    button {{ padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }}
                </style>
            </head>
            <body>
                <div class="video-container">
                    <h1>{video["title"]}</h1>
                    <p>Video file: {video["filename"]}</p>
                    <p>Reward per session: ${settings["reward_per_session"]}</p>
                    <button onclick="alert('Video playing! Earning ${settings['reward_per_session']}')">Play Video</button>
                    <br><br>
                    <a href="/">← Back to Home</a>
                </div>
            </body>
            </html>
            '''
    return "Video not found", 404

# -------------------- ADMIN AUTH --------------------

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'admin' and password == 'admin':
            session['admin'] = True
            return redirect('/admin-dashboard')
        else:
            flash("Invalid credentials.")
    
    try:
        return render_template('login.html')
    except:
        # Fallback HTML if template doesn't exist
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Login</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; max-width: 400px; }
                input { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; }
                button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h2>Admin Login</h2>
            <form method="POST">
                <label>Username:</label>
                <input type="text" name="username" required>
                
                <label>Password:</label>
                <input type="password" name="password" required>
                
                <button type="submit">Login</button>
            </form>
            <p><a href="/">← Back to Home</a></p>
        </body>
        </html>
        '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# -------------------- ADMIN DASHBOARD --------------------

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin-login')
    
    try:
        return render_template('dashboard.html', 
                             users=users, 
                             withdrawals=withdrawals, 
                             videos=videos, 
                             visitors=123, 
                             youtuber_campaigns=youtuber_campaigns, 
                             settings=settings)
    except:
        # Fallback HTML if template doesn't exist
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .section {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                button {{ padding: 5px 10px; margin: 2px; cursor: pointer; }}
                .approve {{ background: green; color: white; }}
                .reject {{ background: red; color: white; }}
            </style>
        </head>
        <body>
            <h1>Admin Dashboard</h1>
            <p><a href="/logout">Logout</a> | <a href="/">Home</a></p>
            
            <div class="section">
                <h2>Settings</h2>
                <form method="POST" action="/update-settings">
                    <label>Reward per session: $</label>
                    <input type="number" step="0.001" name="reward_per_session" value="{settings['reward_per_session']}">
                    <button type="submit">Update</button>
                </form>
            </div>
            
            <div class="section">
                <h2>Upload Video</h2>
                <form method="POST" action="/upload" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="Video Title" required><br><br>
                    <input type="text" name="thumbnail" placeholder="Thumbnail URL (optional)"><br><br>
                    <input type="file" name="video" accept="video/*" required><br><br>
                    <button type="submit">Upload</button>
                </form>
            </div>
            
            <div class="section">
                <h2>Videos ({len(videos)})</h2>
                <table>
                    <tr><th>ID</th><th>Title</th><th>Filename</th><th>Actions</th></tr>
                    {''.join([f'<tr><td>{i}</td><td>{v["title"]}</td><td>{v["filename"]}</td><td><form method="POST" action="/delete/{i}" style="display:inline;"><button type="submit" onclick="return confirm(\'Delete this video?\')">Delete</button></form></td></tr>' for i, v in enumerate(videos)])}
                </table>
            </div>
            
            <div class="section">
                <h2>YouTuber Campaigns ({len(youtuber_campaigns)})</h2>
                <table>
                    <tr><th>Title</th><th>YouTube Link</th><th>Submitted By</th><th>Status</th><th>Actions</th></tr>
                    {''.join([f'<tr><td>{c["title"]}</td><td><a href="{c["youtube_link"]}" target="_blank">View</a></td><td>{c["submitted_by"]}</td><td>{c["status"]}</td><td>' + 
                             (f'<form method="POST" action="/approve-campaign/{i}" style="display:inline;"><button type="submit" class="approve">Approve</button></form>' +
                              f'<form method="POST" action="/reject-campaign/{i}" style="display:inline;"><button type="submit" class="reject">Reject</button></form>' 
                              if c["status"] == "pending" else f'<span>{c["status"].title()}</span>') + 
                             '</td></tr>' for i, c in enumerate(youtuber_campaigns)])}
                </table>
            </div>
            
            <div class="section">
                <h2>Users & Earnings</h2>
                <table>
                    <tr><th>User</th><th>Earnings</th></tr>
                    {''.join([f'<tr><td>{user}</td><td>${data["earnings"]}</td></tr>' for user, data in users.items()])}
                </table>
            </div>
            
            <div class="section">
                <h2>Withdrawals ({len(withdrawals)})</h2>
                <table>
                    <tr><th>ID</th><th>User</th><th>Amount</th><th>Status</th><th>Actions</th></tr>
                    {''.join([f'<tr><td>{i}</td><td>{w.get("user", "N/A")}</td><td>${w.get("amount", "0")}</td><td>{w.get("status", "pending")}</td><td>' + 
                             (f'<form method="POST" action="/withdraw/{i}/approve" style="display:inline;"><button type="submit" class="approve">Approve</button></form>' +
                              f'<form method="POST" action="/withdraw/{i}/reject" style="display:inline;"><button type="submit" class="reject">Reject</button></form>' 
                              if w.get("status") == "pending" else f'<span>{w.get("status", "").title()}</span>') + 
                             '</td></tr>' for i, w in enumerate(withdrawals)])}
                </table>
            </div>
        </body>
        </html>
        '''

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if not session.get('admin'):
        return redirect('/admin-login')
    
    try:
        new_reward = float(request.form['reward_per_session'])
        if new_reward >= 0:
            settings["reward_per_session"] = new_reward
            flash("Settings updated successfully!")
        else:
            flash("Reward amount must be positive.")
    except ValueError:
        flash("Invalid input. Please enter a valid number.")
    except Exception as e:
        flash(f"Error updating settings: {str(e)}")
    
    return redirect('/admin-dashboard')

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect('/admin-login')
    
    if 'video' in request.files:
        video = request.files['video']
        title = request.form['title']
        thumbnail = request.form.get('thumbnail', '')
        
        if video.filename != '':
            filename = secure_filename(video.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            video.save(path)
            
            videos.append({
                "title": title, 
                "filename": filename, 
                "thumbnail": thumbnail
            })
            flash("Video uploaded successfully!")
        else:
            flash("Please select a video file.")
    else:
        flash("No video file provided.")
    
    return redirect('/admin-dashboard')

@app.route('/delete/<int:vid_id>', methods=['POST'])
def delete_video(vid_id):
    if not session.get('admin'):
        return redirect('/admin-login')
    
    if 0 <= vid_id < len(videos):
        del videos[vid_id]
    
    return redirect('/admin-dashboard')

@app.route('/withdraw')
def withdraw_page():
    if not session.get('admin'):
        return redirect('/admin-login')
    
    try:
        return render_template('withdraw.html', withdrawals=withdrawals)
    except:
        return redirect('/admin-dashboard')

@app.route('/withdraw/<int:req_id>/approve', methods=['POST'])
def approve_withdraw(req_id):
    if not session.get('admin'):
        return redirect('/admin-login')
    
    if 0 <= req_id < len(withdrawals):
        withdrawals[req_id]['status'] = 'approved'
    
    return redirect('/admin-dashboard')

@app.route('/withdraw/<int:req_id>/reject', methods=['POST'])
def reject_withdraw(req_id):
    if not session.get('admin'):
        return redirect('/admin-login')
    
    if 0 <= req_id < len(withdrawals):
        withdrawals[req_id]['status'] = 'rejected'
    
    return redirect('/admin-dashboard')

# -------------------- YOUTUBER SUBMISSION --------------------

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
        
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Submission Successful</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
                .success { color: green; font-size: 18px; }
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ Video Submitted Successfully!</h2>
                <p>Your YouTube video has been submitted for review.</p>
                <p><a href="/youtuber-upload">Submit Another Video</a></p>
                <p><a href="/">← Back to Home</a></p>
            </div>
        </body>
        </html>
        '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTuber Upload</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; max-width: 500px; }
            input, button { width: 100%; padding: 12px; margin: 8px 0; box-sizing: border-box; }
            button { background: #007bff; color: white; border: none; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            label { font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Submit Your YouTube Video</h1>
        <form method="POST">
            <label>Video Title:</label>
            <input type="text" name="title" placeholder="Enter video title" required>
            
            <label>YouTube URL:</label>
            <input type="url" name="youtube_link" placeholder="https://youtube.com/..." required>
            
            <label>Your Email:</label>
            <input type="email" name="submitted_by" placeholder="your@email.com" required>
            
            <button type="submit">Submit Video</button>
        </form>
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    '''

@app.route('/approve-campaign/<int:index>', methods=['POST'])
def approve_campaign(index):
    if not session.get('admin'):
        return redirect('/admin-login')
    
    if 0 <= index < len(youtuber_campaigns):
        youtuber_campaigns[index]['status'] = 'approved'
    
    return redirect('/admin-dashboard')

@app.route('/reject-campaign/<int:index>', methods=['POST'])
def reject_campaign(index):
    if not session.get('admin'):
        return redirect('/admin-login')
    
    if 0 <= index < len(youtuber_campaigns):
        youtuber_campaigns[index]['status'] = 'rejected'
    
    return redirect('/admin-dashboard')

# -------------------- MAIN --------------------

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)
