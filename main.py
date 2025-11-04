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
from proxy_collector import IPAddressCollector, get_fastest_ips

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- File upload setup ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database setup - SEPARATE DATABASE FOR L2 ---
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
    proxy_used = db.Column(db.String(255))  # New field to track which proxy was used


# Initialize database
with app.app_context():
    db.create_all()
    logger.info(f"✅ L2 connected to database: {DB_PATH}")


# --- IP Rotation Functions ---
def get_working_proxy():
    """
    Get a fresh working proxy using IPAddressCollector
    """
    try:
        collector = IPAddressCollector()
        validated_ips = collector.get_validated_ips(max_ips=20)

        if validated_ips:
            # Get the fastest working IP
            fastest_ip = min(validated_ips, key=lambda x: x['response_time'] or float('inf'))
            proxy_url = f"http://{fastest_ip['ip']}"
            logger.info(f"🎯 Selected proxy: {fastest_ip['ip']} ({fastest_ip['response_time']}ms)")
            return proxy_url
        else:
            logger.warning("🚨 No working proxies found")
            return None

    except Exception as e:
        logger.error(f"💥 Error getting proxy: {str(e)}")
        return None


def test_proxy_connection(proxy_url):
    """
    Test if proxy is working before using it
    """
    try:
        proxies = {'http': proxy_url, 'https': proxy_url}
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False


def generate_fake_headers():
    """
    Generate realistic browser headers for proxy requests
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
    ]

    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


# --- Updated Submission Functions with IP Rotation ---
def submit_to_l1_with_ip_rotation(application_id, preserved_params):
    """
    Background task to submit data to L1 with IP rotation
    """
    try:
        with app.app_context():
            application = Application.query.get(application_id)
            if not application:
                logger.error(f"Application {application_id} not found")
                return

            logger.info(f"🔄 Starting IP-ROTATED submission for application {application_id}")

            # Update status to processing
            application.submission_status = 'processing'
            db.session.commit()

            # Get fresh working proxy for THIS submission
            proxy_url = get_working_proxy()
            headers = generate_fake_headers()

            proxies = None
            if proxy_url and test_proxy_connection(proxy_url):
                proxies = {'http': proxy_url, 'https': proxy_url}
                logger.info(f"🌐 Using proxy: {proxy_url}")
                application.proxy_used = proxy_url
            else:
                logger.warning("🚨 No proxy available, using direct connection")
                application.proxy_used = "DIRECT"

            db.session.commit()

            # Humanized delays (your existing code)
            logger.info("⏳ Simulating human behavior...")
            time.sleep(random.uniform(2, 4))

            # Simulate form filling (your existing code)
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

            # Submit with proxy rotation
            l1_payload = {**form_data, **preserved_params}
            files = None

            if application.resume_filename:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], application.resume_filename)
                if os.path.exists(file_path):
                    files = {'resume': open(file_path, 'rb')}
                    logger.info(f"📎 Attaching file: {application.resume_filename}")

            # Submit to L1 with proxy
            l1_submit_url = "https://velvelt.onrender.com/"
            response = requests.post(
                l1_submit_url,
                data=l1_payload,
                files=files,
                headers=headers,
                proxies=proxies,
                timeout=30
            )

            if files:
                files['resume'].close()

            logger.info(f"📡 L1 Response Status: {response.status_code}")

            if response.status_code in [200, 302]:
                logger.info(f"✅ Successfully submitted via proxy: {proxy_url}")
                application.submission_status = 'completed'
                application.l1_submission_id = f"l1_{application_id}_{int(time.time())}"
            else:
                logger.warning(f"❌ L1 submission failed via proxy: {proxy_url}")
                application.submission_status = 'failed'

            db.session.commit()

    except Exception as e:
        logger.error(f"💥 Error in IP-rotated submission: {str(e)}")
        try:
            with app.app_context():
                application = Application.query.get(application_id)
                if application:
                    application.submission_status = 'error'
                    db.session.commit()
        except Exception as inner_e:
            logger.error(f"💥 Could not update error status: {inner_e}")


# --- Keep your existing helper functions ---
def get_preserved_params():
    params = {}
    for key, value in request.args.items():
        if key.startswith('utm_') or key == 'gclid' or key == 'fbclid':
            params[key] = value
    return params


def build_redirect_url(base_url, extra_params=None):
    params = get_preserved_params()
    if extra_params:
        params.update(extra_params)
    if params:
        return f"{base_url}?{urlencode(params)}"
    return base_url


def simulate_field_filling(field_name, value, field_type):
    """Your existing function"""
    # ... keep your existing implementation


def simulate_typing(text, speed='medium'):
    """Your existing function"""
    # ... keep your existing implementation


def submit_to_l1_humanized(application_id, preserved_params):
    """Your existing humanized function"""
    # ... keep your existing implementation


# --- New Routes for Proxy Management ---
@app.route('/proxy-test')
def proxy_test():
    """Test the proxy system"""
    try:
        collector = IPAddressCollector()
        validated_ips = collector.get_validated_ips(max_ips=10)

        # Test one proxy with L1
        test_result = "Not tested"
        if validated_ips:
            proxy_url = f"http://{validated_ips[0]['ip']}"
            try:
                response = requests.get(
                    "https://velvelt.onrender.com/",
                    proxies={'http': proxy_url, 'https': proxy_url},
                    timeout=10
                )
                test_result = f"Success ({response.status_code})"
            except Exception as e:
                test_result = f"Failed: {str(e)}"

        return jsonify({
            "proxies_fetched": len(validated_ips),
            "working_proxies": [ip['ip'] for ip in validated_ips],
            "l1_connection_test": test_result,
            "fastest_proxy": validated_ips[0]['ip'] if validated_ips else None
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/proxy-dashboard')
def proxy_dashboard():
    """Dashboard to monitor proxy usage"""
    applications = Application.query.filter(Application.proxy_used.isnot(None)).order_by(
        Application.submitted_at.desc()).all()

    proxy_stats = {}
    for app in applications:
        proxy = app.proxy_used or "DIRECT"
        if proxy not in proxy_stats:
            proxy_stats[proxy] = 0
        proxy_stats[proxy] += 1

    return render_template('proxy_dashboard.html',
                           applications=applications,
                           proxy_stats=proxy_stats)


# --- Updated Routes ---
@app.route('/')
def index():
    """Show the application form"""
    preserved_params = get_preserved_params()
    return render_template('index.html', query_params=preserved_params)


@app.route('/apply', methods=['POST'])
def apply():
    """
    Process form submission with IP rotation option
    """
    try:
        form = request.form
        file = request.files.get('resume')

        # Save file locally
        resume_filename = None
        if file and file.filename:
            resume_filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
            file.save(file_path)
            logger.info(f"✅ File saved locally: {resume_filename}")

        # Save to L2 database
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

        logger.info(f"✅ Application saved to L2 database with ID: {application.id}")

        preserved_params = get_preserved_params()

        # 🚀 Choose submission method (IP rotation or humanized)
        use_ip_rotation = request.form.get('use_ip_rotation', 'no') == 'yes'

        if use_ip_rotation:
            # Use IP rotation
            thread = threading.Thread(
                target=submit_to_l1_with_ip_rotation,
                args=(application.id, preserved_params),
                daemon=True
            )
            logger.info(f"🌐 Started IP-ROTATED L1 submission for application {application.id}")
        else:
            # Use humanized submission (original)
            thread = threading.Thread(
                target=submit_to_l1_humanized,
                args=(application.id, preserved_params),
                daemon=True
            )
            logger.info(f"🤖 Started HUMANIZED L1 submission for application {application.id}")

        thread.start()

        # ⚡ IMMEDIATE redirect to L1's success page
        l1_success_url = build_redirect_url("https://velvelt.onrender.com/submit")
        logger.info(f"📍 Immediate redirect to L1 success page: {l1_success_url}")
        return redirect(l1_success_url)

    except Exception as e:
        logger.error(f"❌ Error processing application: {str(e)}")
        db.session.rollback()
        flash('Error submitting application. Please try again.', 'error')
        return redirect(url_for('index'))


# --- Keep your existing routes ---
@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    preserved_params = get_preserved_params()
    return render_template('privacy.html', query_params=preserved_params)


@app.route('/applications')
def applications():
    """View all submitted applications in L2"""
    try:
        all_applications = Application.query.order_by(Application.submitted_at.desc()).all()
        status_summary = {
            'total': Application.query.count(),
            'pending': Application.query.filter_by(submission_status='pending').count(),
            'processing': Application.query.filter_by(submission_status='processing').count(),
            'completed': Application.query.filter_by(submission_status='completed').count(),
            'failed': Application.query.filter_by(submission_status='failed').count(),
            'error': Application.query.filter_by(submission_status='error').count()
        }
        return render_template('applications.html',
                               applications=all_applications,
                               status_summary=status_summary)
    except Exception as e:
        logger.error(f"❌ Error loading applications: {str(e)}")
        flash('Error loading applications.', 'error')
        return redirect(url_for('index'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/status')
def status():
    """Check submission status"""
    total = Application.query.count()
    pending = Application.query.filter_by(submission_status='pending').count()
    processing = Application.query.filter_by(submission_status='processing').count()
    completed = Application.query.filter_by(submission_status='completed').count()
    failed = Application.query.filter_by(submission_status='failed').count()
    error = Application.query.filter_by(submission_status='error').count()

    return jsonify({
        'total_applications': total,
        'pending_submissions': pending,
        'processing_submissions': processing,
        'completed_submissions': completed,
        'failed_submissions': failed,
        'error_submissions': error,
        'database': DB_PATH
    })


if __name__ == '__main__':
    logger.info("🚀 Starting L2 Server with IP Rotation...")
    logger.info(f"📊 Using L2 database: {DB_PATH}")
    logger.info("🌐 IP Rotation system: ACTIVE")
    app.run(debug=True, host='0.0.0.0', port=5000)