from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from pathlib import Path
import uuid
from typing import Dict, List, Optional
import pyrebase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    """Application configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    UPLOAD_FOLDER = Path('static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'}
    
    # Email configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    
    # Admin credentials (use environment variables in production)
    ADMIN_EMAIL_LOGIN = os.getenv('ADMIN_EMAIL_LOGIN', 'admin@example.com')
    ADMIN_PASSWORD_HASH = generate_password_hash(os.getenv('ADMIN_PASSWORD', 'admin123'))
    
    # Firebase configuration
    FIREBASE_CONFIG = {
        "apiKey": os.getenv('FIREBASE_API_KEY'),
        "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
        "databaseURL": os.getenv('FIREBASE_DATABASE_URL', ''),
        "projectId": os.getenv('FIREBASE_PROJECT_ID'),
        "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
        "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID', ''),
        "appId": os.getenv('FIREBASE_APP_ID', '')
    }

class DataManager:
    """Handles data persistence and operations"""
    
    def __init__(self, data_file: str = 'data.json'):
        self.data_file = Path(data_file)
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """Load data from JSON file or create default structure"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"Error loading data file: {e}")
        
        return {
            "visitors": 0,
            "videos": [],
            "users": {},
            "withdrawals": [],
            "daily_logins": {},
            "ad_clicks": 0,
            "daily_login_reward": 0.005,
            "campaigns": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    def save_data(self) -> bool:
        """Save data to JSON file with error handling"""
        try:
            self.data["last_updated"] = datetime.now().isoformat()
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return False
    
    def add_visitor(self) -> None:
        """Increment visitor counter"""
        self.data['visitors'] += 1
        self.save_data()
    
    def add_video(self, filename: str, original_filename: str) -> str:
        """Add video to database"""
        video_id = str(uuid.uuid4())
        video_data = {
            "id": video_id,
            "filename": filename,
            "original_filename": original_filename,
            "upload_time": datetime.now().isoformat(),
            "views": 0,
            "status": "active"
        }
        self.data['videos'].append(video_data)
        self.save_data()
        return video_id
    
    def delete_video(self, index: int) -> bool:
        """Delete video by index"""
        if 0 <= index < len(self.data['videos']):
            video = self.data['videos'][index]
            # Delete physical file
            file_path = Config.UPLOAD_FOLDER / video['filename']
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")
            
            del self.data['videos'][index]
            self.save_data()
            return True
        return False
    
    def get_withdrawal_count(self) -> int:
        """Get count of pending withdrawals"""
        return len([w for w in self.data['withdrawals'] if w.get('status') == 'pending'])

class EmailService:
    """Handles email operations"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def send_admin_notification(self, subject: str, content: str) -> bool:
        """Send email notification to admin"""
        if not all([self.config.EMAIL_ADDRESS, self.config.EMAIL_PASSWORD, self.config.ADMIN_EMAIL]):
            logger.warning("Email configuration incomplete")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.EMAIL_ADDRESS
            msg['To'] = self.config.ADMIN_EMAIL
            msg['Subject'] = f"[Admin Alert] {subject}"
            
            # Add timestamp to content
            timestamped_content = f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}"
            msg.attach(MIMEText(timestamped_content, 'plain'))
            
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.EMAIL_ADDRESS, self.config.EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Admin notification sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send admin email: {e}")
            return False

# Initialize components
config = Config()
data_manager = DataManager()
email_service = EmailService(config)

# Initialize Firebase
try:
    firebase = pyrebase.initialize_app(config.FIREBASE_CONFIG)
    auth = firebase.auth()
    logger.info("Firebase initialized successfully")
except Exception as e:
    logger.error(f"Firebase initialization failed: {e}")
    firebase = None
    auth = None

# Create Flask app
app = Flask(__name__)
app.config.from_object(config)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def home():
    """Homepage with visitor tracking"""
    data_manager.add_visitor()
    return render_template('index.html', 
                         visitor_count=data_manager.data['visitors'],
                         video_count=len(data_manager.data['videos']))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login with improved security"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        if (email == config.ADMIN_EMAIL_LOGIN and 
            check_password_hash(config.ADMIN_PASSWORD_HASH, password)):
            session['admin'] = True
            session['login_time'] = datetime.now().isoformat()
            logger.info(f"Admin login successful from {request.remote_addr}")
            flash('Login successful', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            logger.warning(f"Failed login attempt for {email} from {request.remote_addr}")
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    if session.get('admin'):
        logger.info("Admin logged out")
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('home'))

@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with enhanced statistics"""
    stats = {
        'total_visitors': data_manager.data['visitors'],
        'total_videos': len(data_manager.data['videos']),
        'pending_withdrawals': data_manager.get_withdrawal_count(),
        'total_users': len(data_manager.data['users']),
        'ad_clicks': data_manager.data['ad_clicks']
    }
    
    return render_template('admin-dashboard.html', 
                         videos=data_manager.data['videos'],
                         withdrawals=data_manager.data['withdrawals'],
                         stats=stats)

@app.route('/upload', methods=['POST'])
@admin_required
def upload_video():
    """Upload video with enhanced validation and error handling"""
    if 'video' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['video']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if not allowed_file(file.filename):
        flash(f'File type not allowed. Allowed types: {", ".join(config.ALLOWED_EXTENSIONS)}', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Ensure upload directory exists
        config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = config.UPLOAD_FOLDER / unique_filename
        file.save(str(file_path))
        
        # Add to database
        video_id = data_manager.add_video(unique_filename, original_filename)
        
        # Send admin notification
        email_service.send_admin_notification(
            "New Video Uploaded",
            f"Video '{original_filename}' has been uploaded successfully.\nVideo ID: {video_id}"
        )
        
        logger.info(f"Video uploaded successfully: {original_filename} -> {unique_filename}")
        flash(f'Video "{original_filename}" uploaded successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        flash('Error uploading video. Please try again.', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/delete/<int:index>', methods=['POST'])
@admin_required
def delete_video(index):
    """Delete video with confirmation"""
    if data_manager.delete_video(index):
        flash('Video deleted successfully', 'success')
        logger.info(f"Video at index {index} deleted by admin")
    else:
        flash('Error deleting video', 'error')
        logger.error(f"Failed to delete video at index {index}")
    
    return redirect(url_for('admin_dashboard'))

@app.route('/api/withdrawal-count')
def api_withdrawal_count():
    """API endpoint for withdrawal count"""
    return jsonify({
        "count": data_manager.get_withdrawal_count(),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/stats')
@admin_required
def api_stats():
    """API endpoint for dashboard statistics"""
    return jsonify({
        "visitors": data_manager.data['visitors'],
        "videos": len(data_manager.data['videos']),
        "users": len(data_manager.data['users']),
        "withdrawals": len(data_manager.data['withdrawals']),
        "ad_clicks": data_manager.data['ad_clicks'],
        "last_updated": data_manager.data.get('last_updated')
    })

@app.route('/static/notify.mp3')
def serve_notification_sound():
    """Serve notification sound file"""
    return send_from_directory('static', 'notify.mp3')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('File too large. Maximum size is 16MB.', 'error')
    return redirect(url_for('admin_dashboard'))

# Context processors for templates
@app.context_processor
def utility_processor():
    return dict(
        current_year=datetime.now().year,
        app_version="2.0.0"
    )

if __name__ == '__main__':
    # Create necessary directories
    config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Save initial data
    data_manager.save_data()
    
    # Run app
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    
    logger.info(f"Starting Flask application on port {port}")
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
