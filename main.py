import threading
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
import logging
import time
import random

from ip_manager import ip_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- File upload setup ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database setup ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "applications.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- L2 Database Model ---
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    address = db.Column(db.String(255))
    position = db.Column(db.String(100))
    additional_info = db.Column(db.Text)
    resume_filename = db.Column(db.String(255))
    submission_status = db.Column(db.String(50), default='pending')
    l1_submission_id = db.Column(db.String(100))
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())
    ip_source = db.Column(db.String(50))  # Changed from proxy_used to ip_source
def simulate_field_filling(field_name, value, field_type):
    """
    Simulate realistic field filling behavior
    """
    if not value:
        return

    logger.info(f"   Filling {field_name.replace('_', ' ')}...")

    # Different behaviors for different field types
    if field_type == 'name':
        # Names are typed quickly but with occasional pauses
        time.sleep(random.uniform(0.5, 1.5))
        simulate_typing(value, 'fast')

    elif field_type == 'email':
        # Emails are typed quickly (people know their emails well)
        time.sleep(random.uniform(0.3, 1.0))
        simulate_typing(value, 'fast')

    elif field_type == 'phone':
        # Phone numbers with pauses between groups
        time.sleep(random.uniform(0.8, 1.8))
        simulate_typing(value, 'numbers')

    elif field_type == 'dropdown':
        # Dropdown selection with reading time
        time.sleep(random.uniform(1.5, 3.0))

    elif field_type == 'address':
        # Address typing with thinking time
        time.sleep(random.uniform(1.0, 2.0))
        simulate_typing(value, 'medium')

    elif field_type == 'textarea':
        # Text areas with lots of thinking and editing
        time.sleep(random.uniform(2.0, 4.0))
        simulate_typing(value, 'slow')

    # Small pause after each field
    time.sleep(random.uniform(0.2, 0.8))


def simulate_typing(text, speed='medium'):
    """
    Simulate realistic typing with variable speed
    """
    if not text:
        return

    # Define typing speeds (seconds per character)
    speed_config = {
        'fast': (0.05, 0.12),
        'medium': (0.08, 0.18),
        'slow': (0.12, 0.25),
        'numbers': (0.06, 0.15)
    }

    min_delay, max_delay = speed_config.get(speed, (0.08, 0.18))

    for i, char in enumerate(text):

        time_per_char = random.uniform(min_delay, max_delay)
        time.sleep(time_per_char)

        if random.random() < 0.03:
            time.sleep(random.uniform(0.3, 0.8))

        if char == ' ' and random.random() < 0.4:
            time.sleep(random.uniform(0.1, 0.3))

        if random.random() < 0.02 and i > 2:
            time.sleep(random.uniform(0.2, 0.5))


def reset_database():
    """Drop and recreate the database with updated schema"""
    try:
        db.drop_all()
        db.create_all()
        logger.info("✅ Database recreated with updated schema (ip_source column added)")
    except Exception as e:
        logger.error(f"❌ Error resetting database: {e}")

# Initialize database
with app.app_context():
    db.create_all()  # Only create tables if they don't exist
    logger.info(f"✅ L2 connected to database: {DB_PATH}")

def get_preserved_params():
    params = {}
    for key, value in request.args.items():
        if key.startswith('utm_') or key == 'gclid' or key == 'fbclid':
            params[key] = value
    return params

def submit_to_l1_humanized(application_id, preserved_params):
    """Submit to L1 with human-like behavior"""
    try:
        with app.app_context():
            application = db.session.get(Application, application_id)
            if not application:
                return

            application.submission_status = 'processing'
            db.session.commit()

            current_ip = ip_manager.get_current_ip()
            application.ip_source = f"IP_{current_ip}"
            db.session.commit()

            logger.info(f"🔄 Starting submission from IP: {current_ip}")

            logger.info("⏳ Simulating page load and initial orientation...")
            time.sleep(random.uniform(2, 4))

            # Step 2: Simulate scrolling and reading the form
            logger.info("📄 Simulating form scanning...")
            time.sleep(random.uniform(3, 6))

            # Step 3: Fill form fields with realistic timing - ADD THIS SECTION
            logger.info("⌨️  Simulating form filling...")

            # Personal Information section
            simulate_field_filling('first_name', application.first_name, 'name')
            simulate_field_filling('last_name', application.last_name, 'name')
            simulate_field_filling('email', application.email, 'email')
            simulate_field_filling('phone', application.phone, 'phone')

            # Location section
            simulate_field_filling('country', application.country, 'dropdown')
            simulate_field_filling('city', application.city, 'name')
            simulate_field_filling('address', application.address, 'address')

            # Position section
            simulate_field_filling('position', application.position, 'dropdown')
            simulate_field_filling('additional_info', application.additional_info, 'textarea')

            # Step 4: File upload consideration
            if application.resume_filename:
                logger.info("📎 Simulating file upload consideration...")
                time.sleep(random.uniform(2, 4))
                # Simulate file selection delay
                time.sleep(random.uniform(1, 2))

            # Step 5: Terms and conditions reading simulation
            logger.info("📖 Simulating terms and conditions reading...")
            # Simulate reading each terms section
            terms_sections = 3
            for i in range(terms_sections):
                logger.info(f"   Reading terms section {i + 1}/{terms_sections}...")
                time.sleep(random.uniform(3, 8))
                if i < terms_sections - 1:
                    time.sleep(random.uniform(1, 2))

            # Step 6: Checkbox interactions
            logger.info("✅ Simulating checkbox interactions...")
            for i in range(3):  # 3 terms checkboxes
                time.sleep(random.uniform(0.5, 1.5))
                if random.random() < 0.2:
                    time.sleep(random.uniform(0.5, 1))
                    logger.info("   🤔 Reconsidering terms...")

            # Step 7: Final review before submission
            logger.info("🔍 Simulating final form review...")
            time.sleep(random.uniform(4, 8))

            # Random chance of making a small correction
            if random.random() < 0.3:
                logger.info("   ✏️  Making a small correction...")
                time.sleep(random.uniform(2, 4))

            # Step 8: Hover and hesitation before submit
            logger.info("🤔 Hesitating before submission...")
            time.sleep(random.uniform(1, 3))

            # Step 9: Submit to L1
            logger.info("🚀 Submitting to L1...")

            # Prepare payload for L1
            form_data = {
                'first_name': application.first_name,
                'last_name': application.last_name,
                'email': application.email,
                'phone': application.phone,
                'country': application.country,
                'city': application.city,
                'address': application.address,
                'position': application.position,
                'additional_info': application.additional_info
            }

            # Handle file upload
            files = None
            if application.resume_filename:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], application.resume_filename)
                if os.path.exists(file_path):
                    files = {'resume': open(file_path, 'rb')}
                    logger.info(f"📎 Attaching file: {application.resume_filename}")

            # Submit to L1
            l1_payload = {**form_data, **preserved_params}
            response = requests.post(
                "https://application.taskifyjobs.com/",
                data=l1_payload,
                files=files,
                timeout=30
            )

            if files:
                files['resume'].close()

            # Update status
            if response.status_code in [200, 302]:
                application.submission_status = 'completed'
                application.l1_submission_id = f"l1_{application_id}_{int(time.time())}"
                logger.info(f"✅ Successfully submitted from IP: {current_ip}")
            else:
                application.submission_status = 'failed'
                logger.warning(f"❌ Submission failed from IP: {current_ip}")

            db.session.commit()

    except Exception as e:
        logger.error(f"💥 Error in submission: {str(e)}")
        try:
            with app.app_context():
                application = db.session.get(Application, application_id)
                if application:
                    application.submission_status = 'error'
                    db.session.commit()
        except:
            pass

# --- HELPER FUNCTIONS ---
# def get_preserved_params():
#     params = {}
#     for key, value in request.args.items():
#         if key.startswith('utm_') or key == 'gclid' or key == 'fbclid':
#             params[key] = value
#     return params


# --- ROUTES ---
@app.route('/')
def index():
    preserved_params = get_preserved_params()
    return render_template('index.html', query_params=preserved_params)


@app.route('/apply', methods=['POST'])
def apply():
    """Process form submission"""
    try:
        form = request.form
        file = request.files.get('resume')

        # Save file
        resume_filename = None
        if file and file.filename:
            resume_filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
            file.save(file_path)

        # Save to database
        application = Application(
            first_name=form.get('first_name'),
            last_name=form.get('last_name'),
            email=form.get('email'),
            phone=form.get('phone'),
            country=form.get('country'),
            city=form.get('city'),
            address=form.get('address'),
            position=form.get('position'),
            additional_info=form.get('additional_info'),
            resume_filename=resume_filename,
            submission_status='pending'
        )
        db.session.add(application)
        db.session.commit()

        # Start background submission
        preserved_params = get_preserved_params()
        thread = threading.Thread(
            target=submit_to_l1_humanized,
            args=(application.id, preserved_params),
            daemon=True
        )
        thread.start()

        logger.info(f"🤖 Started submission for application {application.id}")
        l1_base_url = "https://application.taskifyjobs.com/submit"
        if preserved_params:
            query_string = urlencode(preserved_params)
            redirect_url = f"{l1_base_url}?{query_string}"
        else:
            redirect_url = l1_base_url

        return redirect(redirect_url)
    except Exception as e:
        logger.error(f"❌ Error processing application: {str(e)}")
        flash('Error submitting application. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/applications')
def applications():
    """View submitted applications"""
    all_applications = Application.query.order_by(Application.submitted_at.desc()).all()
    status_summary = {
        'total': Application.query.count(),
        'pending': Application.query.filter_by(submission_status='pending').count(),
        'processing': Application.query.filter_by(submission_status='processing').count(),
        'completed': Application.query.filter_by(submission_status='completed').count(),
        'failed': Application.query.filter_by(submission_status='failed').count(),
        'error': Application.query.filter_by(submission_status='error').count()
    }

    # Get IP statistics
    ip_stats = {}
    for app in all_applications:
        ip = app.ip_source or "Unknown"
        if ip not in ip_stats:
            ip_stats[ip] = 0
        ip_stats[ip] += 1

    # Get IP manager status
    ip_status = ip_manager.get_ip_status()

    return render_template('applications.html',
                           applications=all_applications,
                           status_summary=status_summary,
                           ip_stats=ip_stats,
                           ip_status=ip_status)  # Add this line

@app.route('/current-ip')
def current_ip():
    """Check current IP address"""
    ip = ip_manager.get_current_ip()
    return jsonify({"current_ip": ip})


@app.route('/status')
def status():
    """Check submission status"""
    total = Application.query.count()
    pending = Application.query.filter_by(submission_status='pending').count()
    completed = Application.query.filter_by(submission_status='completed').count()
    failed = Application.query.filter_by(submission_status='failed').count()

    return jsonify({
        'total_applications': total,
        'pending_submissions': pending,
        'completed_submissions': completed,
        'failed_submissions': failed
    })

@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    preserved_params = get_preserved_params()
    return render_template('privacy.html', query_params=preserved_params)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    uploads_dir = os.path.join(app.root_path, 'uploads')
    return send_from_directory(uploads_dir, filename)
if __name__ == '__main__':
    logger.info("🚀 Starting L2 Server with IP Rotation...")
    logger.info("💡 TIP: Use VPN/Mobile Hotspot to change IP between submissions")
    app.run(debug=True, host='0.0.0.0', port=5000)
# import threading
# import requests
# from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
# from flask_sqlalchemy import SQLAlchemy
# import os
# from werkzeug.utils import secure_filename
# from urllib.parse import urlencode
# import logging
# import time
# import random
# import re
# from concurrent.futures import ThreadPoolExecutor, as_completed
# import concurrent.futures
# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
# app = Flask(__name__)
# app.secret_key = 'supersecretkey'
#
# # --- File upload setup ---
# UPLOAD_FOLDER = 'uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#
# # --- Database setup - SEPARATE DATABASE FOR L2 ---
# BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# DB_PATH = os.path.join(BASE_DIR, "applications.db")
# app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
#
#
# # --- L2 Database Model ---
# class Application(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     first_name = db.Column(db.String(100))
#     last_name = db.Column(db.String(100))
#     email = db.Column(db.String(150))
#     phone = db.Column(db.String(50))
#     country = db.Column(db.String(100))
#     city = db.Column(db.String(100))
#     address = db.Column(db.String(255))
#     position = db.Column(db.String(100))
#     additional_info = db.Column(db.Text)
#     resume_filename = db.Column(db.String(255))
#     submission_status = db.Column(db.String(50), default='pending')
#     l1_submission_id = db.Column(db.String(100))
#     submitted_at = db.Column(db.DateTime, server_default=db.func.now())
#     proxy_used = db.Column(db.String(255))  # New field for proxy tracking
#
# def reset_database():
#     """Drop and recreate the database with updated schema"""
#     try:
#         db.drop_all()
#         db.create_all()
#         logger.info("✅ Database recreated with updated schema (proxy_used column added)")
#     except Exception as e:
#         logger.error(f"❌ Error resetting database: {e}")
# # Initialize database
# with app.app_context():
#     db.create_all()
#     logger.info(f"✅ L2 connected to database: {DB_PATH}")
#
# # With:
# with app.app_context():
#     reset_database()  # This will recreate the table with the new column
#     logger.info(f"✅ L2 connected to database: {DB_PATH}")
#
# def get_fresh_proxies():
#     """
#     Get fresh working proxies from multiple sources
#     """
#     proxy_sources = [
#         "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
#         "https://www.proxy-list.download/api/v1/get?type=http",
#         "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
#         "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
#         "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"
#     ]
#
#     all_proxies = []
#
#     for source in proxy_sources:
#         try:
#             logger.info(f"📥 Fetching proxies from: {source}")
#             response = requests.get(source, timeout=15)
#
#             if response.status_code == 200:
#                 # Parse proxy list (different formats)
#                 proxies = []
#                 for line in response.text.strip().split('\n'):
#                     line = line.strip()
#                     if line and ':' in line and not line.startswith('#'):
#                         # Handle different formats: "ip:port" or "http://ip:port"
#                         if line.startswith('http://'):
#                             proxies.append(line)
#                         else:
#                             proxies.append(f"http://{line}")
#
#                 all_proxies.extend(proxies)
#                 logger.info(f"✅ Got {len(proxies)} proxies from {source}")
#             else:
#                 logger.warning(f"❌ Failed to fetch from {source}: Status {response.status_code}")
#
#         except Exception as e:
#             logger.warning(f"❌ Error fetching from {source}: {str(e)}")
#
#     # Remove duplicates
#     unique_proxies = list(set(all_proxies))
#     logger.info(f"📊 Total unique proxies: {len(unique_proxies)}")
#
#     return unique_proxies
#
# def validate_proxy(proxy):
#     """
#     Validate if a proxy is working with better error handling
#     """
#     try:
#         logger.debug(f"🔍 Testing proxy: {proxy}")
#         response = requests.get(
#             "https://httpbin.org/ip",
#             proxies={'http': proxy, 'https': proxy},
#             timeout=10,  # Reduced timeout to fail faster
#             headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
#         )
#         if response.status_code == 200:
#             ip_data = response.json()
#             logger.info(f"🎯 Valid proxy: {proxy} → IP: {ip_data['origin']}")
#             return proxy
#         else:
#             logger.debug(f"❌ Proxy returned status {response.status_code}: {proxy}")
#             return None
#     except requests.exceptions.ConnectTimeout:
#         logger.debug(f"⏰ Proxy timeout: {proxy}")
#         return None
#     except requests.exceptions.ProxyError:
#         logger.debug(f"🔌 Proxy error: {proxy}")
#         return None
#     except Exception as e:
#         logger.debug(f"⚠️ Proxy test failed: {proxy} - {e}")
#         return None
#
#
# def test_proxy_shopify(proxy):
#     """
#     Test if proxy works by connecting to reliable sites
#     Returns the proxy if working, None if failed
#     """
#     try:
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.5',
#         }
#
#         # Test with multiple reliable sites
#         test_urls = [
#             "https://httpbin.org/ip",  # Fast, reliable
#             "https://api.ipify.org?format=json",  # Simple IP check
#             "https://www.google.com",  # Major site
#         ]
#
#         for test_url in test_urls:
#             try:
#                 response = requests.get(
#                     test_url,
#                     headers=headers,
#                     proxies={'http': proxy, 'https': proxy},
#                     timeout=5  # Reasonable timeout
#                 )
#
#                 if response.status_code == 200:
#                     logger.info(f"🎯 Working proxy found: {proxy}")
#                     return {
#                         'proxy': proxy,
#                         'statuscode': response.status_code,
#                         'test_url': test_url
#                     }
#             except:
#                 continue  # Try next URL if this one fails
#
#     except Exception as e:
#         logger.debug(f"❌ Proxy failed: {proxy} - {e}")
#
#     return None
#
# def get_working_proxies_advanced(max_proxies=10):
#     """
#     Get ONLY working proxies using advanced testing
#     """
#     try:
#         fresh_proxies = get_fresh_proxies()
#
#         if not fresh_proxies:
#             logger.warning("🚨 No proxies fetched")
#             return []
#
#         logger.info(f"🧪 Testing {len(fresh_proxies[:30])} proxies thoroughly...")
#
#         working_proxies = []
#
#         with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:  # FIXED: added concurrent.futures
#             # Test proxies concurrently
#             future_to_proxy = {
#                 executor.submit(test_proxy_shopify, proxy): proxy
#                 for proxy in fresh_proxies[:30]  # Test first 30
#             }
#
#             for future in concurrent.futures.as_completed(future_to_proxy):  # FIXED: added concurrent.futures
#                 proxy = future_to_proxy[future]
#                 try:
#                     result = future.result()
#                     if result:
#                         working_proxies.append(result['proxy'])
#                         logger.info(f"✅ Valid proxy #{len(working_proxies)}: {result['proxy']}")
#
#                         if len(working_proxies) >= max_proxies:
#                             logger.info(f"🎯 Found {len(working_proxies)} working proxies - stopping")
#                             break
#                 except Exception as e:
#                     continue
#
#         logger.info(f"📊 Result: {len(working_proxies)}/{len(fresh_proxies[:30])} proxies working")
#         return working_proxies
#
#     except Exception as e:
#         logger.error(f"💥 Error in advanced proxy testing: {str(e)}")
#         return []
#
#
# def get_working_proxies(max_proxies=5):
#     """
#     Main function to get working proxies - uses advanced testing
#     """
#     logger.info("🔄 Starting advanced proxy discovery...")
#
#     # Try advanced method first
#     working_proxies = get_working_proxies_advanced(max_proxies)
#
#     if working_proxies:
#         logger.info(f"🎉 Success! Found {len(working_proxies)} working proxies")
#         return working_proxies
#     else:
#         logger.warning("🚨 No working proxies found with advanced method")
#         return []
#
# def submit_to_l1_humanized_with_proxy(application_id, preserved_params):
#     """
#     Background task to submit data to L1 with realistic human behavior AND proxy
#     User is already redirected to success page - this runs in background
#     """
#     try:
#         # Create application context for the thread
#         with app.app_context():
#             # Get application from L2 database
#             application = Application.query.get(application_id)
#             if not application:
#                 logger.error(f"Application {application_id} not found")
#                 return
#
#             logger.info(f"🔄 Starting HUMANIZED+PROXY submission for application {application_id}")
#
#             # Update status to processing
#             application.submission_status = 'processing'
#             db.session.commit()
#
#             # Get fresh working proxy for THIS submission
#             working_proxies = get_working_proxies(max_proxies=5)
#             proxy_url = working_proxies[0] if working_proxies else None
#
#             proxies = None
#             if proxy_url:
#                 proxies = {'http': proxy_url, 'https': proxy_url}
#                 logger.info(f"🌐 Using proxy: {proxy_url}")
#                 application.proxy_used = proxy_url
#             else:
#                 logger.warning("🚨 No proxy available, using direct connection")
#                 application.proxy_used = "DIRECT"
#
#             db.session.commit()
#
#             # Step 1: Initial page load simulation (2-4 seconds)
#             logger.info("⏳ Simulating page load and initial orientation...")
#             time.sleep(random.uniform(2, 4))
#
#             # Step 2: Simulate scrolling and reading the form
#             logger.info("📄 Simulating form scanning...")
#             time.sleep(random.uniform(3, 6))
#
#             # Step 3: Fill form fields with realistic timing
#             form_data = {
#                 'first_name': application.first_name,
#                 'last_name': application.last_name,
#                 'email': application.email,
#                 'phone': application.phone,
#                 'country': application.country,
#                 'city': application.city,
#                 'address': application.address,
#                 'position': application.position,
#                 'additional_info': application.additional_info
#             }
#
#             # Simulate filling each field with human-like behavior
#             logger.info("⌨️  Simulating form filling...")
#
#             # Personal Information section
#             simulate_field_filling('first_name', application.first_name, 'name')
#             simulate_field_filling('last_name', application.last_name, 'name')
#             simulate_field_filling('email', application.email, 'email')
#             simulate_field_filling('phone', application.phone, 'phone')
#
#             # Location section
#             simulate_field_filling('country', application.country, 'dropdown')
#             simulate_field_filling('city', application.city, 'name')
#             simulate_field_filling('address', application.address, 'address')
#
#             # Position section
#             simulate_field_filling('position', application.position, 'dropdown')
#             simulate_field_filling('additional_info', application.additional_info, 'textarea')
#
#             # Step 4: File upload consideration
#             if application.resume_filename:
#                 logger.info("📎 Simulating file upload consideration...")
#                 time.sleep(random.uniform(2, 4))
#                 # Simulate file selection delay
#                 time.sleep(random.uniform(1, 2))
#
#             # Step 5: Terms and conditions reading simulation
#             logger.info("📖 Simulating terms and conditions reading...")
#             # Simulate reading each terms section
#             terms_sections = 3
#             for i in range(terms_sections):
#                 logger.info(f"   Reading terms section {i + 1}/{terms_sections}...")
#                 # Simulate reading time per section (3-8 seconds each)
#                 time.sleep(random.uniform(3, 8))
#                 # Simulate scrolling between sections
#                 if i < terms_sections - 1:
#                     time.sleep(random.uniform(1, 2))
#
#             # Step 6: Checkbox interactions
#             logger.info("✅ Simulating checkbox interactions...")
#             for i in range(3):  # 3 terms checkboxes
#                 time.sleep(random.uniform(0.5, 1.5))
#                 # Random chance of unchecking and rechecking (human hesitation)
#                 if random.random() < 0.2:
#                     time.sleep(random.uniform(0.5, 1))
#                     logger.info("   🤔 Reconsidering terms...")
#
#             # Step 7: Final review before submission
#             logger.info("🔍 Simulating final form review...")
#             time.sleep(random.uniform(4, 8))
#
#             # Random chance of making a small correction
#             if random.random() < 0.3:
#                 logger.info("   ✏️  Making a small correction...")
#                 time.sleep(random.uniform(2, 4))
#
#             # Step 8: Hover and hesitation before submit
#             logger.info("🤔 Hesitating before submission...")
#             time.sleep(random.uniform(1, 3))
#
#             # Step 9: Submit to L1 WITH PROXY
#             logger.info("🚀 Submitting to L1 with proxy...")
#
#             # Prepare payload for L1
#             l1_payload = {**form_data, **preserved_params}
#
#             # Handle file upload
#             files = None
#             if application.resume_filename:
#                 file_path = os.path.join(app.config['UPLOAD_FOLDER'], application.resume_filename)
#                 if os.path.exists(file_path):
#                     files = {'resume': open(file_path, 'rb')}
#                     logger.info(f"📎 Attaching file: {application.resume_filename}")
#
#             # Submit to L1 with proxy
#             l1_submit_url = "https://application.taskifyjobs.com/"
#             response = requests.post(l1_submit_url, data=l1_payload, files=files, proxies=proxies, timeout=30)
#
#             if files:
#                 files['resume'].close()
#
#             logger.info(f"📡 L1 Response Status: {response.status_code}")
#
#             if response.status_code in [200, 302]:
#                 logger.info(f"✅ Successfully submitted to L1 via proxy: {application_id}")
#                 application.submission_status = 'completed'
#                 application.l1_submission_id = f"l1_{application_id}_{int(time.time())}"
#             else:
#                 logger.warning(f"❌ L1 submission failed with status {response.status_code}")
#                 application.submission_status = 'failed'
#
#             db.session.commit()
#
#     except Exception as e:
#         logger.error(f"💥 Error in humanized L1 submission with proxy: {str(e)}")
#         # Try to update status even if there's an error
#         try:
#             with app.app_context():
#                 application = Application.query.get(application_id)
#                 if application:
#                     application.submission_status = 'error'
#                     db.session.commit()
#         except Exception as inner_e:
#             logger.error(f"💥 Could not update error status: {inner_e}")
#
#
# def simulate_field_filling(field_name, value, field_type):
#     """
#     Simulate realistic field filling behavior
#     """
#     if not value:
#         return
#
#     logger.info(f"   Filling {field_name.replace('_', ' ')}...")
#
#     # Different behaviors for different field types
#     if field_type == 'name':
#         # Names are typed quickly but with occasional pauses
#         time.sleep(random.uniform(0.5, 1.5))
#         simulate_typing(value, 'fast')
#
#     elif field_type == 'email':
#         # Emails are typed quickly (people know their emails well)
#         time.sleep(random.uniform(0.3, 1.0))
#         simulate_typing(value, 'fast')
#
#     elif field_type == 'phone':
#         # Phone numbers with pauses between groups
#         time.sleep(random.uniform(0.8, 1.8))
#         simulate_typing(value, 'numbers')
#
#     elif field_type == 'dropdown':
#         # Dropdown selection with reading time
#         time.sleep(random.uniform(1.5, 3.0))
#
#     elif field_type == 'address':
#         # Address typing with thinking time
#         time.sleep(random.uniform(1.0, 2.0))
#         simulate_typing(value, 'medium')
#
#     elif field_type == 'textarea':
#         # Text areas with lots of thinking and editing
#         time.sleep(random.uniform(2.0, 4.0))
#         simulate_typing(value, 'slow')
#
#     # Small pause after each field
#     time.sleep(random.uniform(0.2, 0.8))
#
#
# def simulate_typing(text, speed='medium'):
#     """
#     Simulate realistic typing with variable speed
#     """
#     if not text:
#         return
#
#     # Define typing speeds (seconds per character)
#     speed_config = {
#         'fast': (0.05, 0.12),
#         'medium': (0.08, 0.18),
#         'slow': (0.12, 0.25),
#         'numbers': (0.06, 0.15)
#     }
#
#     min_delay, max_delay = speed_config.get(speed, (0.08, 0.18))
#
#     for i, char in enumerate(text):
#         # Base typing delay
#         time_per_char = random.uniform(min_delay, max_delay)
#         time.sleep(time_per_char)
#
#         # Occasional longer pauses (thinking, correcting)
#         if random.random() < 0.03:  # 3% chance of longer pause
#             time.sleep(random.uniform(0.3, 0.8))
#
#         # Pause between words
#         if char == ' ' and random.random() < 0.4:
#             time.sleep(random.uniform(0.1, 0.3))
#
#         # Occasional backspacing and retyping (typos)
#         if random.random() < 0.02 and i > 2:  # 2% chance of typo correction
#             time.sleep(random.uniform(0.2, 0.5))
#
#
# # --- Helper functions ---
# def get_preserved_params():
#     params = {}
#     for key, value in request.args.items():
#         if key.startswith('utm_') or key == 'gclid' or key == 'fbclid':
#             params[key] = value
#     return params
#
#
# def build_redirect_url(base_url, extra_params=None):
#     params = get_preserved_params()
#     if extra_params:
#         params.update(extra_params)
#     if params:
#         return f"{base_url}?{urlencode(params)}"
#     return base_url
#
#
# @app.route('/quick-proxy-test')
# def quick_proxy_test():
#     """Quick test to verify proxy system is working"""
#     try:
#         # Test just 10 proxies quickly
#         fresh_proxies = get_fresh_proxies()[:10]
#         working_count = 0
#
#         for proxy in fresh_proxies:
#             if test_proxy_shopify(proxy):
#                 working_count += 1
#
#         return jsonify({
#             "tested_proxies": len(fresh_proxies),
#             "working_proxies": working_count,
#             "status": "SUCCESS" if working_count > 0 else "NO_WORKING_PROXIES"
#         })
#
#     except Exception as e:
#         return jsonify({"error": str(e)})
#
# @app.route('/proxy-test')
# def proxy_test():
#     """Test the proxy system"""
#     try:
#         working_proxies = get_working_proxies(max_proxies=10)
#
#         # Test one proxy with L1
#         test_result = "Not tested"
#         if working_proxies:
#             proxy_url = working_proxies[0]
#             try:
#                 response = requests.get(
#                     "https://application.taskifyjobs.com/",
#                     proxies={'http': proxy_url, 'https': proxy_url},
#                     timeout=10
#                 )
#                 test_result = f"Success ({response.status_code})"
#             except Exception as e:
#                 test_result = f"Failed: {str(e)}"
#
#         return jsonify({
#             "total_proxies_fetched": len(working_proxies),
#             "working_proxies": working_proxies,
#             "l1_connection_test": test_result,
#             "tested_proxy": working_proxies[0] if working_proxies else None
#         })
#     except Exception as e:
#         return jsonify({"error": str(e)})
#
#
# @app.route('/test-proxy-detailed')
# def test_proxy_detailed():
#     """Detailed proxy system test"""
#     try:
#         # Test a small batch thoroughly
#         test_proxies = get_fresh_proxies()[:10]  # First 10 proxies
#
#         results = {
#             "total_proxies_fetched": len(test_proxies),
#             "tested_proxies": [],
#             "working_count": 0
#         }
#
#         for proxy in test_proxies:
#             is_working = validate_proxy(proxy) is not None
#             results["tested_proxies"].append({
#                 "proxy": proxy,
#                 "working": is_working
#             })
#             if is_working:
#                 results["working_count"] += 1
#
#         return jsonify(results)
#
#     except Exception as e:
#         return jsonify({"error": str(e)})
# @app.route('/test-proxy-system')
# def test_proxy_system():
#     """Test the proxy system in detail"""
#     try:
#         # Test with just 5 proxies
#         working_proxies = get_working_proxies(max_proxies=3)
#
#         results = {
#             "working_proxies_found": len(working_proxies),
#             "working_proxies": working_proxies,
#             "message": "No working proxies found" if not working_proxies else "Success!"
#         }
#
#         return jsonify(results)
#
#     except Exception as e:
#         return jsonify({"error": str(e)})
# @app.route('/fresh-proxies')
# def fresh_proxies():
#     """Get fresh proxies only"""
#     try:
#         working_proxies = get_working_proxies(max_proxies=20)
#         return jsonify({
#             "total_working_proxies": len(working_proxies),
#             "proxies": working_proxies
#         })
#     except Exception as e:
#         return jsonify({"error": str(e)})
#
#
# # --- Routes ---
# @app.route('/')
# def index():
#     """Show the application form"""
#     preserved_params = get_preserved_params()
#     return render_template('index.html', query_params=preserved_params)
#
#
# @app.route('/apply', methods=['POST'])
# def apply():
#     """
#     Process form submission:
#     - Save to L2 database
#     - Start HUMANIZED+PROXY background submission to L1
#     - IMMEDIATELY redirect to L1's website
#     """
#     try:
#         form = request.form
#         file = request.files.get('resume')
#
#         # Save file locally
#         resume_filename = None
#         if file and file.filename:
#             resume_filename = secure_filename(file.filename)
#             file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
#             file.save(file_path)
#             logger.info(f"✅ File saved locally: {resume_filename}")
#
#         # Save to L2 database
#         application = Application(
#             first_name=form.get('first_name'),
#             last_name=form.get('last_name'),
#             email=form.get('email'),
#             phone=form.get('phone'),
#             country=form.get('country'),
#             city=form.get('city'),
#             address=form.get('address'),
#             position=form.get('position'),
#             additional_info=form.get('additional_info'),
#             resume_filename=resume_filename,
#             submission_status='pending'
#         )
#         db.session.add(application)
#         db.session.commit()
#
#         logger.info(f"✅ Application saved to L2 database with ID: {application.id}")
#
#         preserved_params = get_preserved_params()
#
#         # 🚀 Start HUMANIZED+PROXY background submission to L1
#         thread = threading.Thread(
#             target=submit_to_l1_humanized_with_proxy,
#             args=(application.id, preserved_params),
#             daemon=True
#         )
#         thread.start()
#
#         logger.info(f"🤖 Started HUMANIZED+PROXY L1 submission for application {application.id}")
#
#         # ⚡ IMMEDIATE redirect to L1's success page
#         l1_success_url = "https://application.taskifyjobs.com/submit"
#         logger.info(f"📍 Immediate redirect to L1 success page: {l1_success_url}")
#         return redirect(l1_success_url)
#
#     except Exception as e:
#         logger.error(f"❌ Error processing application: {str(e)}")
#         db.session.rollback()
#         flash('Error submitting application. Please try again.', 'error')
#         return redirect(url_for('index'))
#
#
# @app.route('/privacy')
# def privacy():
#     """Privacy policy page"""
#     preserved_params = get_preserved_params()
#     return render_template('privacy.html', query_params=preserved_params)
#
#
# @app.route('/applications')
# def applications():
#     """View all submitted applications in L2"""
#     try:
#         # Get all applications ordered by most recent
#         all_applications = Application.query.order_by(Application.submitted_at.desc()).all()
#
#         # Get status summary
#         status_summary = {
#             'total': Application.query.count(),
#             'pending': Application.query.filter_by(submission_status='pending').count(),
#             'processing': Application.query.filter_by(submission_status='processing').count(),
#             'completed': Application.query.filter_by(submission_status='completed').count(),
#             'failed': Application.query.filter_by(submission_status='failed').count(),
#             'error': Application.query.filter_by(submission_status='error').count()
#         }
#
#         logger.info(f"📊 Applications page accessed - Total: {status_summary['total']}")
#
#         return render_template('applications.html',
#                                applications=all_applications,
#                                status_summary=status_summary)
#
#     except Exception as e:
#         logger.error(f"❌ Error loading applications: {str(e)}")
#         flash('Error loading applications.', 'error')
#         return redirect(url_for('index'))
#
#
# @app.route('/uploads/<filename>')
# def uploaded_file(filename):
#     """Serve uploaded files"""
#     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
#
#
# @app.route('/status')
# def status():
#     """Check submission status"""
#     total = Application.query.count()
#     pending = Application.query.filter_by(submission_status='pending').count()
#     processing = Application.query.filter_by(submission_status='processing').count()
#     completed = Application.query.filter_by(submission_status='completed').count()
#     failed = Application.query.filter_by(submission_status='failed').count()
#     error = Application.query.filter_by(submission_status='error').count()
#
#     return jsonify({
#         'total_applications': total,
#         'pending_submissions': pending,
#         'processing_submissions': processing,
#         'completed_submissions': completed,
#         'failed_submissions': failed,
#         'error_submissions': error,
#         'database': DB_PATH
#     })
#
#
# @app.route('/proxy-usage')
# def proxy_usage():
#     """View which proxies were used for submissions"""
#     applications = Application.query.filter(Application.proxy_used.isnot(None)).order_by(
#         Application.submitted_at.desc()).all()
#
#     proxy_stats = {}
#     for app in applications:
#         proxy = app.proxy_used or "DIRECT"
#         if proxy not in proxy_stats:
#             proxy_stats[proxy] = 0
#         proxy_stats[proxy] += 1
#
#     return jsonify({
#         "total_submissions": len(applications),
#         "proxy_usage": proxy_stats,
#         "recent_submissions": [
#             {
#                 "id": app.id,
#                 "name": f"{app.first_name} {app.last_name}",
#                 "proxy_used": app.proxy_used,
#                 "status": app.submission_status,
#                 "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None
#             }
#             for app in applications[:10]  # Last 10 submissions
#         ]
#     })
#
# if __name__ == '__main__':
#     logger.info("🚀 Starting L2 Server with Humanized+Proxy Submission...")
#     logger.info(f"📊 Using L2 database: {DB_PATH}")
#     logger.info("🌐 Fresh proxy system: ACTIVE")
#     logger.info("📍 Redirecting to: https://application.taskifyjobs.com/")
#     app.run(debug=True, host='0.0.0.0', port=5000)
# # import threading
# # import requests
# # from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
# # from flask_sqlalchemy import SQLAlchemy
# # import os
# #True, host='0.0.0.0', port=5000)