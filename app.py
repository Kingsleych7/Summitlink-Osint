from flask import Flask, render_template, request, redirect, url_for, flash
from extensions import db
from models import User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import time
import os
from flask_login import login_required, current_user
from models import db, User, SearchHistory
from models import (
    db,
    User,
    SearchHistory,
    Subscription
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)
from functools import wraps
from flask import abort
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from functools import wraps
from flask import abort
from flask import send_file
from xml.sax.saxutils import escape
import requests
import time
from collections import defaultdict
from flask import request
from flask import redirect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app)
ip_log = defaultdict(list)

user_requests = defaultdict(list)

MAX_REQUESTS = 10
TIME_WINDOW = 60  # seconds

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")
BASE_DIR = os.path.abspath("reports")

app.config['SECRET_KEY'] = 'summitlink-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

PLANS = {
    "BASIC": {
        "price": 2000,
        "duration_days": 30
    },
    "PRO": {
        "price": 5000,
        "duration_days": 30
    }
}
def check_subscription(user):

    if not user.is_subscribed:
        return False

    if not user.subscription_end:
        return False

    if user.subscription_end < datetime.utcnow():
        return False

    return True
def is_rate_limited(user_id):

    now = time.time()

    requests = user_requests[user_id]

    # remove old requests
    user_requests[user_id] = [
        t for t in requests if now - t < TIME_WINDOW
    ]

    if len(user_requests[user_id]) >= MAX_REQUESTS:
        return True

    user_requests[user_id].append(now)
    return False
def has_active_subscription(user):

    if user.subscription_end and user.subscription_end > datetime.utcnow():
        return True

    return False
def track_ip(user_id):

    ip = request.remote_addr
    ip_log[ip].append(time.time())

    if len(ip_log[ip]) > 20:
        log_abuse(user_id, "IP suspicious activity")
# INIT DATABASE
db.init_app(app)

#INIT LOGIN MANAGER (IMPORTANT FIX)
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return abort(403)
        return f(*args, **kwargs)
    return wrapper
def is_admin(user):
    return user.role == "admin"

def is_pro(user):
    return user.role in ["pro", "admin"]

def is_free(user):
    return user.role == "free"
def get_total_revenue():
    return db.session.query(db.func.sum(Payment.amount)).filter_by(status="success").scalar() or 0

def get_monthly_revenue():
    return db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == "success",
        Payment.created_at >= datetime.utcnow() - timedelta(days=30)
    ).scalar() or 0
def get_new_report_paths(username):
    user_dir = os.path.join(BASE_DIR, username)
    os.makedirs(user_dir, exist_ok=True)

    timestamp = int(time.time())

    txt_path = os.path.join(user_dir, f"report_{timestamp}.txt")
    pdf_path = os.path.join(user_dir, f"report_{timestamp}.pdf")

    return txt_path, pdf_path, user_dir
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            return abort(403)
        return f(*args, **kwargs)
    return wrapper
def pro_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.role not in ["pro", "admin"]:
            return abort(403)
        return f(*args, **kwargs)
    return wrapper
def log_abuse(user_id, reason):
    log = AbuseLog(user_id=user_id, reason=reason)
    db.session.add(log)
    db.session.commit()
def add_watermark(c, width, height):
    c.saveState()
    c.setFont("Helvetica", 40)
    c.setFillGray(0.5, 0.1)

    c.translate(width / 2, height / 2)
    c.rotate(45)

    c.drawCentredString(0, 0, "SUMMITLINK INTELLIGENCE")

    c.restoreState()
def watermark_canvas(canvas_obj, doc):
    width, height = letter
    add_watermark(canvas_obj, width, height)

# SIMPLE TEST ROUTE (keep your working one)
@app.route('/')
def home():
    return "Summitlink OSINT Platform Running"

@app.route('/test')
def test():
    return "WORKING"
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']

        password = generate_password_hash(
            request.form['password']
        )

        existing = User.query.filter_by(
            username=username
        ).first()

        if existing:
            return "User already exists"

        user = User(
            username=username,
            password=password
        )

        db.session.add(user)
        db.session.commit()

        subscription = Subscription(
            user_id=user.id,
            plan='free',
            searches_left=3
        )

        db.session.add(subscription)
        db.session.commit()

        return redirect(
            url_for('login')
        )

    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            return redirect(
                url_for('dashboard')
            )

        return "Invalid credentials"

    return render_template('login.html')
@app.route('/dashboard')
@login_required
def dashboard():

    searches = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(
        SearchHistory.created_at.desc()
    ).all()

    history_html = ""

    for item in searches:

        history_html += f"""
        <div class='history-card'>

            <h3>{item.searched_username}</h3>

            <p>{item.created_at}</p>

            <a href='/{item.result_file}'>
                View Report
            </a>

        </div>
        """
subscription = Subscription.query.filter_by(
    user_id=current_user.id
).first()

return f'''
<!DOCTYPE html>
<html>

<head>

<title>Dashboard</title>

    <style>

    body{{
        background:#0f172a;
        color:white;
        font-family:Arial;
        padding:30px;
    }}

    .box{{
        max-width:900px;
        margin:auto;
    }}

    .search-box{{
        background:#1e293b;
        padding:25px;
        border-radius:15px;
    }}

    input{{
        width:100%;
        padding:12px;
        border:none;
        border-radius:8px;
    }}

    button{{
        margin-top:15px;
        padding:12px 20px;
        background:#2563eb;
        color:white;
        border:none;
        border-radius:8px;
        cursor:pointer;
    }}

    .history-card{{
        background:#111827;
        padding:20px;
        margin-top:15px;
        border-radius:12px;
    }}

    a{{
        color:#38bdf8;
        text-decoration:none;
    }}

    </style>

    </head>

    <body>

    <div class="box">

        <div class="search-box">

            <h1>Welcome {current_user.username}</h1>

            <p>
Plan: {subscription.plan.upper()}
<br>
Searches Left: {subscription.searches_left}
</p>

            <form method="POST" action="/search">

                <input
                    name="username"
                    placeholder="Enter username..."
                    required
                >

                <button type="submit">
                    Search OSINT
                </button>

            </form>

        </div>

        <h2 style="margin-top:40px;">
            Search History
        </h2>

        {history_html}

    </div>

    </body>
    </html>
    '''
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
@app.route('/search', methods=['POST'])
@login_required
def search():

    if len(user_requests[current_user.id]) > 8:

         log_abuse(
            current_user.id,
            "High request frequency"
        )

    if is_rate_limited(current_user.id):

         return "Too many requests. Slow down.", 429

    username = current_user.username

    # 1. OSINT result
    report_content = "Sherlock investigation completed"

    output = report_content

    # 2. File paths
    txt_path = os.path.join(
        BASE_DIR,
        f"{username}.txt"
    )

    pdf_path = os.path.join(
        BASE_DIR,
        f"{username}.pdf"
    )

    # 3. Save TXT report
    with open(
        txt_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report_content)

    title = Paragraph(
        f"<b>Summitlink Intelligence Report: {username}</b>",
        styles['Title']
    )

    elements = []

    elements.append(title)

    # 4. Generate PDF
    build_pdf_with_watermark(
        pdf_path,
        report_content,
        f"Summitlink Intelligence Report: {username}"
    )
    # 5. Save to database (history tracking)
    history = SearchHistory(
        searched_username=username,
        result_file=pdf_path,
        user_id=current_user.id
    )

    db.session.add(history)
    db.session.commit()

    # 6. Return result page
    return render_template(
        'result.html',
        username=username,
        output=output,
        report=pdf_path
    )
@app.route('/pay')
@login_required
def pay():

    url = "https://api.paystack.co/transaction/initialize"

    data = {
        "email": current_user.email,
        "amount": 2000 * 100,
        "callback_url": "http://127.0.0.1:5000/verify"
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    response = requests.post(url, json=data, headers=headers)
    res = response.json()

    return redirect(res['data']['authorization_url'])

@app.route('/paystack/webhook', methods=['POST'])
def paystack_webhook():

    payload = request.get_json()

    event = payload.get('event')

    if event == "charge.success":

        data = payload['data']

        reference = data['reference']
        amount = data['amount']
        email = data['customer']['email']

        # fraud check
        if amount not in [200000, 500000]:
            log_abuse(email, "Invalid payment amount detected")
            return "Invalid amount", 400

        user = User.query.filter_by(email=email).first()

        if user:

            payment = Payment(
                user_id=user.id,
                reference=reference,
                amount=amount,
                status="success"
            )

            db.session.add(payment)
            db.session.commit()

    return "OK", 200
@app.route('/download')
@login_required
def download_report():

    payment = Payment.query.filter_by(
    user_id=current_user.id,
    status="success"
).first()

    if not payment:
    return redirect('/pay')

user_dir = os.path.join(
    BASE_DIR,
    current_user.username
)

files = sorted(os.listdir(user_dir))

pdf_files = [
    f for f in files if f.endswith(".pdf")
]

if not pdf_files:
    return "No PDF reports found", 404

    latest_pdf = pdf_files[-1]
    pdf_path = os.path.join(user_dir, latest_pdf)

    return send_file(pdf_path, as_attachment=True)
@app.route('/subscribe/<plan>')
@login_required
def subscribe(plan):

    # prevent duplicate subscriptions
    if has_active_subscription(current_user):
        return "Already subscribed", 403

    # validate plan
    if plan not in PLANS:
        return "Invalid plan", 400

    amount = PLANS[plan]["price"] * 100

    url = "https://api.paystack.co/transaction/initialize"

    data = {
        "email": current_user.email,
        "amount": amount,
        "metadata": {
            "plan": plan
        },
        "callback_url": "https://summitlink-osint-cybercommand.onrender.com/verify"
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    response = requests.post(
        url,
        json=data,
        headers=headers
    )

    res = response.json()

    return redirect(
        res['data']['authorization_url']
    )
@app.route('/admin')
@login_required
def admin():
    if current_user.role != "admin":
         return "Access denied", 403
    total_users = User.query.count()

    total_payments = Payment.query.filter_by(status="success").count()

    revenue = get_total_revenue()
    monthly_revenue = get_monthly_revenue()

    user_roles = {
        "free": User.query.filter_by(role="free").count(),
        "pro": User.query.filter_by(role="pro").count(),
        "admin": User.query.filter_by(role="admin").count()
    }

    return render_template(
        "admin.html",
        total_users=total_users,
        total_payments=total_payments,
        revenue=revenue,
        monthly_revenue=monthly_revenue,
        user_roles=user_roles
    )
@app.route('/admin/abuse')
@login_required
@admin_required
def abuse_dashboard():

    logs = AbuseLog.query.order_by(
        AbuseLog.id.desc()
    ).limit(50).all()

    return render_template(
        "abuse.html",
        logs=logs
    )

  if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=5000, debug=False)
