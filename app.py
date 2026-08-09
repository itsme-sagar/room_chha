from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response
)
from flask_migrate import Migrate

from utils.notification_service import notify
from utils.email_service import send_email
from utils.email_templates import (
    welcome_email,
    room_approved,
    room_rejected,
    wallet_approved,
    wallet_rejected,
    new_room_notification
)

from flask_socketio import SocketIO, emit, join_room
from flask_login import login_required
from config import Config
from models import db, User, Room, Application, Message, Review, Favorite, Notification, PremiumRequest, FeaturedRoomRequest,Wallet, WalletTransaction
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sqlalchemy import or_
from flask_mail import Mail
from flask_mail import Message as MailMessage
from authlib.integrations.flask_client import OAuth
import random
import re
import string

app = Flask(__name__)
load_dotenv()

# Load configuration FIRST
app.config.from_object(Config)

# Google OAuth
app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")

# Mail
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = (
    "Room Chha",
    "virtualsagarindia@gmail.com"
)

db.init_app(app)
mail = Mail(app)
socketio = SocketIO(app, async_mode="threading")

#  //Temporary added for Sql migrate
# print("Database URI:", app.config["SQLALCHEMY_DATABASE_URI"])

migrate = Migrate(app, db)

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    server_metadata_url=
    "https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)

# ================= PATHS =================
UPLOAD_FOLDER = "static/uploads"
ROOM_IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, "rooms")
PROFILE_IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, "profiles")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ROOM_IMAGE_FOLDER, exist_ok=True)
os.makedirs(PROFILE_IMAGE_FOLDER, exist_ok=True)

# ================= INIT =================
with app.app_context():
    db.create_all()

    admin = User.query.filter_by(role="admin").first()
    if not admin:
        admin = User(
            name="Admin",
            email="admin@roomchha.com",
            role="admin",
            password=generate_password_hash("admin123"),
            profile_image="default.png"
        )
        db.session.add(admin)
        db.session.commit()

# ================= GLOBAL CONTEXT =================
@app.context_processor
def inject_globals():
    current_user = None
    unread_count = 0
    notification_count = 0
    admin_alerts = 0

    if "user_id" in session:
        current_user = db.session.get(User,session["user_id"])

        notification_count = Notification.query.filter_by(
            user_id=session["user_id"],
            is_read=False
        ).count()

        unread_count = Message.query.filter_by(
            receiver_id=session["user_id"],
            is_read=False
        ).count()

        # Admin alerts
        if session.get("role") == "admin":

            pending_rooms = Room.query.filter_by(
                approved=False
            ).count()

            pending_applications = Application.query.filter_by(
                status="pending"
            ).count()

            pending_wallet_deposits = WalletTransaction.query.filter_by(
                status="pending",
                transaction_type="deposit"
            ).count()

            pending_premium = PremiumRequest.query.filter_by(
                status="pending"
            ).count()

            pending_featured = FeaturedRoomRequest.query.filter_by(
                status="pending"
            ).count()

            admin_alerts = (
                pending_rooms +
                pending_applications +
                pending_wallet_deposits +
                pending_premium +
                pending_featured
            )

    latest_notifications = []

    if "user_id" in session:

        latest_notifications = (
            Notification.query
            .filter_by(
                user_id=session["user_id"]
            )
            .order_by(
                Notification.id.desc()
            )
            .limit(5)
            .all()
        )

    return dict(

    current_user=current_user,

    unread_count=unread_count,

    notification_count=notification_count,

    latest_notifications=latest_notifications,

    admin_alerts=admin_alerts

)


def notify_matching_users(room):

    users = User.query.filter_by(
        role="renter",
        email_notifications=True
    ).all()

    for user in users:

        # City must match
        if (
            user.preferred_city and
            user.preferred_city != room.city
        ):
            continue

        # Room type must match
        if (
            user.preferred_room_type and
            user.preferred_room_type != room.room_type
        ):
            continue

        # Budget check
        if (
            user.preferred_budget and
            room.rent > user.preferred_budget
        ):
            continue

        # Create notification
        notify(
            user.id,
            f"🏠 New room available in {room.city}",
            f"/room/{room.id}"
        )
        

        # Send email
        send_email(
            mail,

            user.email,

            "🏠 New Room Available",

            new_room_notification(room)

        )
    db.session.commit()

# ================= AUTO PREMIUM EXPIRY =================

@app.before_request
def check_premium_expiry():

    users = User.query.filter_by(
        verified_owner=True
    ).all()

    for user in users:

        if (
            user.premium_plan != "lifetime"
            and user.premium_until
            and user.premium_until < datetime.utcnow()
        ):

            user.verified_owner = False

            user.premium_plan = None

            user.premium_until = None

            notify(
                user.id,
                "Your Premium Plan has expired.",
                "/premium"
            )

    db.session.commit()

# ================= AUTO FEATURED EXPIRY =================

@app.before_request
def check_featured_expiry():

    featured_rooms = Room.query.filter_by(
        featured=True
    ).all()

    for room in featured_rooms:

        if (
            room.featured_until
            and room.featured_until < datetime.utcnow()
        ):

            room.featured = False

            room.featured_until = None

            notify(
                room.owner_id,
                f"Featured status expired for room in {room.city}",
                "/owner/rooms"
            )

    db.session.commit()

# ================= AUTH =================
@app.route("/")
def home():

    total_rooms = Room.query.filter_by(
        approved=True
    ).count()

    total_users = User.query.count()

    total_cities = (
        db.session.query(Room.city)
        .filter(Room.approved == True)
        .distinct()
        .count()
    )

    featured_rooms = (
        Room.query
        .filter_by(
            approved=True,
            featured=True
        )
        .order_by(
            Room.featured_until.desc()
        )
        .limit(6)
        .all()
    )
    latest_rooms = (
        Room.query
        .filter_by(
            approved=True
        )
        .order_by(
            Room.id.desc()
        )
        .limit(8)
        .all()
    )

    cities = (
        db.session.query(Room.city)
        .filter(Room.approved == True)
        .distinct()
        .all()
    )

    return render_template(
        "home.html",
        total_rooms=total_rooms,
        total_users=total_users,
        total_cities=total_cities,
        featured_rooms=featured_rooms,
        latest_rooms=latest_rooms,
        cities=[c[0] for c in cities]
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        u = User(
            name=request.form["name"],
            email=request.form["email"],
            role=request.form["role"],
            profile_image="default.png"
        )

        u.set_password(request.form["password"])

        db.session.add(u)
        db.session.commit()
        # Create wallet automatically

        wallet = Wallet(
            user_id=u.id,
            balance=0
        )

        db.session.add(wallet)
        db.session.commit()
        send_email(
            mail,

            u.email,

            "Welcome to Room Chha",

            welcome_email(

                u.name

            )

        )

        admins = User.query.filter_by(role="admin").all()

        for admin in admins:
            notify(
                admin.id,
                f"New {u.role} registered: {u.name}",
                "/admin/users"
            )
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("auth/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(email=request.form["email"]).first()
        if u and u.check_password(request.form["password"]):
            session["user_id"] = u.id
            session["role"] = u.role
            session["name"] = u.name
            return redirect(url_for("dashboard"))
        flash("Invalid credentials")
    return render_template("auth/login.html")

@app.route("/login/google")
def google_login():

    redirect_uri = url_for(
        "google_callback",
        _external=True
    )

    return google.authorize_redirect(
        redirect_uri
    )

@app.route("/google/callback")
def google_callback():

    token = google.authorize_access_token()

    user_info = token["userinfo"]

    email = user_info["email"]
    name = user_info["name"]

    user = User.query.filter_by(email=email).first()

    if user:

        session["user_id"] = user.id
        session["name"] = user.name
        session["role"] = user.role

        return redirect(url_for("dashboard"))

    session["google_name"] = name
    session["google_email"] = email

    return redirect(url_for("google_role"))

@app.route("/google/role", methods=["GET", "POST"])
def google_role():

    if "google_email" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        role = request.form["role"]

        user = User(
            name=session["google_name"],
            email=session["google_email"],
            role=role,
            profile_image="default.png"
        )

        user.password = ""

        db.session.add(user)
        db.session.commit()

        wallet = Wallet(
            user_id=user.id,
            balance=0
        )

        db.session.add(wallet)
        db.session.commit()

        admins = User.query.filter_by(role="admin").all()

        for admin in admins:
            notify(
                admin.id,
                f"New {user.role} registered: {user.name}",
                "/admin/users"
            )

        db.session.commit()

        session["user_id"] = user.id
        session["name"] = user.name
        session["role"] = user.role

        session.pop("google_name", None)
        session.pop("google_email", None)

        flash("Welcome to Room Chha!")

        return redirect(url_for("dashboard"))

    return render_template("auth/google_role.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        user = User.query.filter_by(email=email).first()

        if not user:

            flash("No account found with this email.")

            return redirect(url_for("forgot_password"))

        otp = random.randint(100000,999999)

        session["reset_email"] = email
        session["reset_otp"] = str(otp)

        session["otp_expiry"] = (
            datetime.now() +
            timedelta(minutes=10)
        ).strftime("%Y-%m-%d %H:%M:%S")

        session["otp_attempts"] = 0

        session["otp_last_sent"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        msg = MailMessage(
            "Room Chha Password Reset OTP",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email]
        )

        msg.html = f"""
<div style="font-family:Arial;background:#f5f5f5;padding:30px;">

<div style="background:white;padding:30px;border-radius:12px;max-width:600px;margin:auto;">

<h1 style="color:#0d6efd;">
🏠 Room Chha
</h1>

<p>Hello <b>{user.name}</b>,</p>

<p>
We received a request to reset your password.
</p>

<div style="
background:#0d6efd;
color:white;
font-size:34px;
padding:20px;
text-align:center;
border-radius:10px;
letter-spacing:8px;
font-weight:bold;
">

{otp}

</div>

<p style="margin-top:20px;">
This OTP expires in
<b>10 minutes.</b>
</p>

<p>
If this wasn't you,
ignore this email.
</p>

<hr>

<center>

<small>

© 2026 Room Chha Nepal

</small>

</center>

</div>

</div>
"""

        mail.send(msg)

        flash("OTP sent to your email.")

        return redirect(url_for("verify_otp"))

    return render_template("auth/forgot_password.html")
@app.route("/verify-otp", methods=["GET","POST"])
def verify_otp():

    if request.method == "POST":

        expiry = datetime.strptime(
            session["otp_expiry"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() > expiry:

            flash("OTP expired.")

            return redirect(url_for("forgot_password"))

        entered = request.form["otp"]

        if entered == session.get("reset_otp"):

            session["otp_attempts"] = 0

            return redirect(url_for("reset_password"))

        session["otp_attempts"] += 1

        remaining = 5 - session["otp_attempts"]

        if remaining <= 0:

            session.clear()

            flash("Too many wrong attempts.")

            return redirect(url_for("forgot_password"))

        flash(f"Wrong OTP. {remaining} attempts left.")

    return render_template("auth/verify_otp.html")

@app.route("/resend-otp")
def resend_otp():

    if "reset_email" not in session:

        return redirect(url_for("forgot_password"))

    last = datetime.strptime(
        session["otp_last_sent"],
        "%Y-%m-%d %H:%M:%S"
    )

    if datetime.now() - last < timedelta(seconds=60):

        flash("Please wait 60 seconds.")

        return redirect(url_for("verify_otp"))

    otp = random.randint(100000,999999)

    session["reset_otp"] = str(otp)

    session["otp_expiry"] = (
        datetime.now()+timedelta(minutes=10)
    ).strftime("%Y-%m-%d %H:%M:%S")

    session["otp_last_sent"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    msg = MailMessage(

        subject="Room Chha Password Reset OTP",

        sender=app.config["MAIL_USERNAME"],

        recipients=[session["reset_email"]]

    )

    msg.html = f"""

    <h2>Room Chha</h2>

    <h1>{otp}</h1>

    <p>This OTP expires in 10 minutes.</p>

    """

    mail.send(msg)

    flash("New OTP sent.")

    return redirect(url_for("verify_otp"))

@app.route("/reset-password", methods=["GET","POST"])
def reset_password():

    if request.method == "POST":

        p1 = request.form["password"]
        if len(p1) < 8:

            flash("Password must contain at least 8 characters.")

            return redirect(url_for("reset_password"))

        if not re.search(r"[A-Z]", p1):

            flash("Password must contain one uppercase letter.")

            return redirect(url_for("reset_password"))

        if not re.search(r"[0-9]", p1):

            flash("Password must contain one number.")

            return redirect(url_for("reset_password"))
        p2 = request.form["confirm_password"]

        if p1 != p2:

            flash("Passwords don't match.")

            return redirect(url_for("reset_password"))

        email = session.get("reset_email")

        user = User.query.filter_by(email=email).first()

        user.set_password(p1)

        db.session.commit()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        session.pop("otp_expiry", None)
        session.pop("otp_attempts", None)
        session.pop("otp_last_sent", None)

        flash("Password updated successfully.")

        return redirect(url_for("login"))

    return render_template("auth/reset_password.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "owner":
        return redirect(url_for("owner_dashboard"))
    if role == "renter":
        return redirect(url_for("renter_dashboard"))
    return redirect(url_for("login"))
# Preminium page
@app.route("/premium")
def premium():
    return render_template(
        "premium.html"
    )

@app.route("/request-premium/<plan>")
def request_premium(plan):

    if session.get("role") != "owner":
        return redirect("/login")

    prices = {
        "monthly": 20,
        "yearly": 199,
        "lifetime": 399
    }

    if plan not in prices:

        flash("Invalid plan.")

        return redirect("/premium")

    wallet = Wallet.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if not wallet:

        flash("Wallet not found.")

        return redirect("/owner/wallet")

    if wallet.balance < prices[plan]:

        flash(
            f"Insufficient balance. Rs.{prices[plan]} required."
        )

        return redirect("/owner/wallet")

    wallet.balance -= prices[plan]

    req = PremiumRequest(
        user_id=session["user_id"],
        request_type="verified_owner",
        plan=plan
    )

    db.session.add(req)

    admins = User.query.filter_by(
        role="admin"
    ).all()

    for admin in admins:

        notify(
            admin.id,
            f"New Premium Request ({plan})",
            "/admin/premium-requests"
        )

    db.session.commit()

    flash(
        "Premium request submitted successfully."
    )

    return redirect("/owner/dashboard")

@app.route("/admin/premium-requests")
def admin_premium_requests():

    if session.get("role") != "admin":
        return redirect("/login")

    requests = (
        db.session.query(
            PremiumRequest,
            User
        )
        .join(
            User,
            PremiumRequest.user_id == User.id
        )
        .order_by(
            PremiumRequest.id.desc()
        )
        .all()
    )

    return render_template(
        "admin/premium_requests.html",
        requests=requests
    )

# Wallet Page 

@app.route("/admin/approve-deposit/<int:txn_id>")
def approve_deposit(txn_id):

    if session.get("role") != "admin":
        return redirect("/login")

    txn = WalletTransaction.query.get_or_404(txn_id)

    if txn.status != "pending":
        return redirect("/admin/wallet-deposits")

    wallet = Wallet.query.filter_by(user_id=txn.user_id).first()

    if wallet is None:
        wallet = Wallet(user_id=txn.user_id, balance=0)
        db.session.add(wallet)

    wallet.balance += txn.amount
    txn.status = "approved"

    db.session.commit()

    notify(
        txn.user_id,
        f"Rs. {txn.amount} added to your wallet 💰",
        "/owner/wallet",
    )
    user=db.session.get(User,txn.user_id)

    send_email(
        mail,

        user.email,

        "Wallet Approved",

        wallet_approved(

            user.name,

            txn.amount

        )

    )
    db.session.commit()

    flash("Deposit approved successfully.", "success")

    return redirect("/admin/wallet-deposits")
@app.route(
    "/admin/reject-deposit/<int:txn_id>"
)
def reject_deposit(txn_id):

    if session.get("role") != "admin":
        return redirect("/login")

    txn = WalletTransaction.query.get_or_404(
        txn_id
    )

    txn.status = "rejected"

    db.session.commit()

    notify(
        txn.user_id,
        "Your wallet deposit was rejected.",
        "/owner/wallet"
    )
    user=db.session.get(User, txn.user_id)

    send_email(
        mail,

        user.email,

        "Wallet Deposit Rejected",

        wallet_rejected(

            user.name

        )

    )
    db.session.commit()

    return redirect(
        "/admin/wallet-deposits"
    )
# ================= ADMIN =================
@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    # Pending Rooms
    pending_rooms = Room.query.filter_by(
        approved=False
    ).count()

    # Pending Applications
    pending_applications = Application.query.filter_by(
        status="pending"
    ).count()

    # Pending Wallet Deposits
    pending_wallet_deposits = WalletTransaction.query.filter_by(
        status="pending",
        transaction_type="deposit"
    ).count()

    # Pending Premium Requests
    pending_premium = PremiumRequest.query.filter_by(
        status="pending"
    ).count()

    # Pending Featured Requests
    pending_featured = FeaturedRoomRequest.query.filter_by(
        status="pending"
    ).count()

    # Total Admin Alerts
    admin_alerts = (
        pending_rooms +
        pending_applications +
        pending_wallet_deposits +
        pending_premium +
        pending_featured
    )

    return render_template(
        "admin/dashboard.html",

        admin_alerts=admin_alerts,

        pending_rooms=pending_rooms,

        pending_applications=pending_applications,

        pending_wallet_deposits=pending_wallet_deposits,

        pending_premium=pending_premium,

        pending_featured=pending_featured
    )

@app.route("/admin/room/<int:room_id>")
def admin_room_detail(room_id):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    room = Room.query.get_or_404(room_id)

    owner = db.session.get(User, room.owner_id)

    return render_template(
        "admin/room_detail.html",
        room=room,
        owner=owner
    )

@app.route("/admin/rooms")
def admin_rooms():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    rooms = Room.query.filter_by(approved=False).all()
    return render_template("admin/rooms.html", rooms=rooms)

@app.route("/admin/approve-room/<int:room_id>")
def approve_room(room_id):

    room = Room.query.get_or_404(room_id)

    room.approved = True
    favorites = Favorite.query.all()

    for fav in favorites:

        old_room = db.session.get(Room, fav.room_id)

        if not old_room:
            continue

        if (
            old_room.city == room.city
            and
            old_room.room_type == room.room_type
        ):

            notify(

                fav.renter_id,

                f"🏠 New room available in {room.city}",

                f"/room/{room.id}"

            )
            user = db.session.get(User,
                fav.renter_id
            )

            send_email(
                mail,

                user.email,

                "🏠 New Room Available",

                new_room_notification(room)

            )

    notify(
        room.owner_id,
        f"Your room in {room.city} was approved",
        "/owner/rooms"
    )
    owner=db.session.get(User, room.owner_id)

    send_email(
        mail,

        owner.email,

        "Room Approved",

            room_approved(

            owner.name,

            room.city

        )

    )
    db.session.commit()

    return redirect(url_for("admin_rooms"))

@app.route("/admin/reject-room/<int:room_id>")
def reject_room(room_id):
    room = Room.query.get_or_404(room_id)
    notify(
    room.owner_id,
    f"Your room in {room.city} was rejected",
    "/owner/rooms"
)
    owner=db.session.get(User, room.owner_id)

    send_email(
        mail,

        owner.email,

        "Room Rejected",

        room_rejected(

            owner.name,

            room.city

        )

    )
    db.session.delete(room)
    db.session.commit()
    return redirect(url_for("admin_rooms"))

@app.route("/admin/all-rooms")
def admin_all_rooms():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    city = request.args.get("city")
    status = request.args.get("status")

    query = db.session.query(Room, User).join(User, Room.owner_id == User.id)

    if city:
        query = query.filter(Room.city == city)
    if status == "approved":
        query = query.filter(Room.approved == True)
    elif status == "pending":
        query = query.filter(Room.approved == False)

    rooms = query.all()
    cities = db.session.query(Room.city).distinct().all()

    return render_template(
        "admin/all_rooms.html",
        rooms=rooms,
        cities=[c[0] for c in cities],
        selected_city=city,
        selected_status=status
    )

@app.route("/admin/applications")
def admin_applications():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    apps = (
        db.session.query(Application, Room, User)
        .join(Room, Application.room_id == Room.id)
        .join(User, Application.renter_id == User.id)
        .all()
    )

    return render_template("admin/applications.html", apps=apps)

@app.route("/admin/users")
def admin_users():

    if session.get("role") != "admin":
        return redirect("/login")

    users = User.query.all()

    return render_template(
        "admin/users.html",
        users=users
    )
@app.route(
    "/admin/approve-premium/<int:req_id>"
)
def approve_premium(req_id):

    if session.get("role") != "admin":
        return redirect("/login")

    req = PremiumRequest.query.get_or_404(
        req_id
    )

    user = db.session.get(User,
        req.user_id
    )

    if req.request_type == "verified_owner":

        user.verified_owner = True

        user.premium_plan = req.plan

        if req.plan == "monthly":

            user.premium_until = (
                datetime.utcnow() +
                timedelta(days=30)
            )

        elif req.plan == "yearly":

            user.premium_until = (
                datetime.utcnow() +
                timedelta(days=365)
            )

        elif req.plan == "lifetime":

            user.premium_until = None

    req.status = "approved"

    db.session.commit()

    notify(
        user.id,
        f"Your {req.plan.title()} Premium Plan was approved 🎉",
        "/profile"
    )
    db.session.commit()

    return redirect(
        "/admin/premium-requests"
    )
@app.route(
    "/admin/reject-premium/<int:req_id>"
)
def reject_premium(req_id):

    if session.get("role") != "admin":
        return redirect("/login")

    req = PremiumRequest.query.get_or_404(
        req_id
    )

    req.status = "rejected"
    prices = {
        "monthly": 20,
        "yearly": 199,
        "lifetime": 399
   }

    wallet = Wallet.query.filter_by(
        user_id=req.user_id
    ).first()

    if wallet and req.plan:

        wallet.balance += prices.get(
            req.plan,
            0
        )

    db.session.commit()

    notify(
        req.user_id,
        "Your Premium request was rejected",
        "/premium"
    )
    db.session.commit()

    return redirect(
        "/admin/premium-requests"
    )

@app.route("/request-feature-room/<int:room_id>")
def request_feature_room(room_id):

    if session.get("role") != "owner":
        return redirect("/login")

    room = Room.query.get_or_404(room_id)

    # Security Check
    if room.owner_id != session["user_id"]:

        flash(
            "Unauthorized room.",
            "danger"
        )

        return redirect("/owner/rooms")

    # Already Featured Check
    if room.featured:

        flash(
            "This room is already featured.",
            "warning"
        )

        return redirect("/owner/rooms")

    wallet = Wallet.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if not wallet:

        flash(
            "Wallet not found.",
            "danger"
        )

        return redirect("/owner/wallet")

    if wallet.balance < 299:

        flash(
            "Insufficient wallet balance. Rs.299 required.",
            "warning"
        )

        return redirect("/owner/wallet")

    existing = FeaturedRoomRequest.query.filter_by(
        room_id=room_id,
        status="pending"
    ).first()

    if existing:

        flash(
            "Feature request already pending.",
            "warning"
        )

        return redirect("/owner/rooms")

    wallet.balance -= 299

    req = FeaturedRoomRequest(
        room_id=room_id,
        owner_id=session["user_id"]
    )

    db.session.add(req)

    db.session.commit()

    admins = User.query.filter_by(
        role="admin"
    ).all()

    for admin in admins:

        notify(
            admin.id,
            f"Featured room request for {room.city}",
            "/admin/featured-requests"
        )
    db.session.commit()

    flash(
        "Rs.299 deducted. Featured room request submitted.",
        "success"
    )

    return redirect("/owner/rooms")

@app.route("/admin/wallet-deposits")
def admin_wallet_deposits():

    if session.get("role") != "admin":
        return redirect("/login")

    deposits = (
        db.session.query(
            WalletTransaction,
            User
        )
        .join(
            User,
            WalletTransaction.user_id == User.id
        )
        .order_by(
            WalletTransaction.id.desc()
        )
        .all()
    )

    return render_template(
        "admin/wallet_deposits.html",
        deposits=deposits
    )

@app.route("/admin/featured-requests")
def admin_featured_requests():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    requests = db.session.query(
        FeaturedRoomRequest,
        Room,
        User
    ).join(
        Room,
        FeaturedRoomRequest.room_id == Room.id
    ).join(
        User,
        FeaturedRoomRequest.owner_id == User.id
    ).order_by(
        FeaturedRoomRequest.created_at.desc()
    ).all()

    return render_template(
        "admin/featured_requests.html",
        requests=requests
    )

@app.route("/admin/approve-featured/<int:req_id>")
def approve_featured(req_id):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    req = FeaturedRoomRequest.query.get_or_404(req_id)

    room = db.session.get(Room, req.room_id)

    room.featured = True

    room.featured_until = (
        datetime.utcnow() +
        timedelta(days=7)
    )

    req.status = "approved"

    db.session.commit()

    notify(
        req.owner_id,
        "Your room was featured successfully.",
        "/owner/rooms"
    )
    db.session.commit()

    flash("Featured room approved.")

    return redirect("/admin/featured-requests")

@app.route("/admin/reject-featured/<int:req_id>")
def reject_featured(req_id):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    req = FeaturedRoomRequest.query.get_or_404(req_id)

    req.status = "rejected"
    wallet = Wallet.query.filter_by(
        user_id=req.owner_id
    ).first()

    # wallet.balance += 299

    if wallet:

        wallet.balance += 299

    db.session.commit()

    notify(
        req.owner_id,
        "Featured room request rejected.",
        "/owner/rooms"
    )
    db.session.commit()

    flash("Request rejected.")

    return redirect("/admin/featured-requests")

# ================= OWNER =================
@app.route("/owner/dashboard")
def owner_dashboard():

    if session.get("role") != "owner":
        return redirect(url_for("login"))

    owner_id = session["user_id"]

    total_rooms = Room.query.filter_by(
        owner_id=owner_id
    ).count()

    total_applications = (
        db.session.query(Application)
        .join(Room, Application.room_id == Room.id)
        .filter(Room.owner_id == owner_id)
        .count()
    )

    total_messages = Message.query.filter_by(
        receiver_id=owner_id,
        is_read=False
    ).count()

    recent_rooms = (
    Room.query
    .filter_by(owner_id=owner_id)
    .order_by(Room.id.desc())
    .limit(5)
    .all()
)
    
    wallet = Wallet.query.filter_by(
    user_id=owner_id
).first()

 #  ===== For verson one i.e initial one 
#     return render_template(
#         "owner/dashboard.html",
#         total_rooms=total_rooms,
#         total_applications=total_applications,
#         total_messages=total_messages,
#         recent_rooms=recent_rooms
# )   

# for version 2 dashboard
    return render_template(
    "owner/dashboard_v2.html",
    total_rooms=total_rooms,
    total_applications=total_applications,
    total_messages=total_messages,
    recent_rooms=recent_rooms,
    wallet=wallet
)

@app.route("/owner/add-room", methods=["GET", "POST"])
def add_room():

    if session.get("role") != "owner":
        return redirect(url_for("login"))

    if request.method == "POST":

        print("FILES RECEIVED:", request.files)
        print("FILES LIST:", request.files.getlist("images"))

        # =========================
        # IMAGE UPLOAD
        # =========================

        uploaded_files = request.files.getlist("images")

        image_names = []

        for file in uploaded_files:

            if file and file.filename:

                filename = secure_filename(
                    file.filename
                )

                file.save(
                    os.path.join(
                        ROOM_IMAGE_FOLDER,
                        filename
                    )
                )

                image_names.append(
                    filename
                )

        # =========================
        # SAFE NUMERIC CONVERSION
        # =========================

        rent = int(
            request.form.get("rent")
        ) if request.form.get("rent") else None

        deposit_amount = int(
            request.form.get("deposit_amount")
        ) if request.form.get("deposit_amount") else 0

        room_capacity = int(
            request.form.get("room_capacity")
        ) if request.form.get("room_capacity") else 1

        bathroom_count = int(
            request.form.get("bathroom_count")
        ) if request.form.get("bathroom_count") else 1

        floor_number = int(
            request.form.get("floor_number")
        ) if request.form.get("floor_number") else 0
        room_size = int(
            request.form.get("room_size")
        ) if request.form.get("room_size") else None

        latitude = float(
            request.form.get("latitude")
        ) if request.form.get("latitude") else None

        longitude = float(
            request.form.get("longitude")
        ) if request.form.get("longitude") else None

        # =========================
        # AVAILABLE DATE
        # =========================

        available_from = None

        if request.form.get(
            "available_from"
        ):

            available_from = datetime.strptime(
                request.form.get(
                    "available_from"
                ),
                "%Y-%m-%d"
            ).date()

        # =========================
        # FACILITIES
        # =========================

        facilities = ",".join(
            request.form.getlist(
                "facilities"
            )
        )

        # =========================
        # CREATE ROOM
        # =========================

        room = Room(

            owner_id=session["user_id"],

            # BASIC
            title=request.form.get(
                "title"
            ),

            city=request.form.get(
                "city"
            ),

            area=request.form.get(
                "area"
            ),

            rent=rent,

            deposit_amount=
            deposit_amount,

            room_type=request.form.get(
                "room_type"
            ),

            description=request.form.get(
                "description"
            ),

            available_from=
            available_from,

            # LOCATION
            province=request.form.get(
                "province"
            ),

            district=request.form.get(
                "district"
            ),

            address=request.form.get(
                "address"
            ),

            postal_code=request.form.get(
                "postal_code"
            ),

            latitude=latitude,

            longitude=longitude,

            # DETAILS
            room_capacity=
            room_capacity,

            bathroom_count=
            bathroom_count,

            floor_number=
            floor_number,

            room_size=
            room_size,

            attached_bathroom=
            "attached_bathroom"
            in request.form,

            facing_direction=
            request.form.get(
                "facing_direction"
            ),

            building_type=
            request.form.get(
                "building_type"
            ),

            kitchen_available=
            "kitchen_available"
            in request.form,

            parking_available=
            "parking_available"
            in request.form,

            balcony_available=
            "balcony_available"
            in request.form,

            furnished=
            "furnished"
            in request.form,
            # PREFERENCES
            tenant_preference=
            request.form.get(
                "tenant_preference"
            ),

            gender_preference=
            request.form.get(
                "gender_preference"
            ),

            smoking_allowed=
            "smoking_allowed"
            in request.form,

            alcohol_allowed=
            "alcohol_allowed"
            in request.form,

            pets_allowed=
            "pets_allowed"
            in request.form,

            # CONTACT
            owner_phone=
            request.form.get(
                "owner_phone"
            ),

            facilities=
            facilities,

            approved=False,

            images=",".join(
                image_names
            )

        )

        db.session.add(room)

        # =========================
        # NOTIFY ADMINS
        # =========================

        admins = User.query.filter_by(
            role="admin"
        ).all()

        for admin in admins:

            notify(
                admin.id,
                f"New room submitted in {room.city}",
                "/admin/rooms"
            )
        db.session.commit()

        flash(
            "Room added successfully and sent for approval"
        )

        return redirect(
            url_for(
                "owner_dashboard"
            )
        )

    return render_template(
        "owner/add_room.html"
    )

@app.route("/owner/applications")
def owner_apps():
    if session.get("role") != "owner":
        return redirect(url_for("login"))

    apps = (
        db.session.query(Application, Room, User)
        .join(Room, Application.room_id == Room.id)
        .join(User, Application.renter_id == User.id)
        .filter(Room.owner_id == session["user_id"])
        .all()
    )
    return render_template("owner/applications.html", apps=apps)

@app.route("/owner/rooms")
def owner_rooms():

    if session.get("role") != "owner":
        return redirect(url_for("login"))

    search = request.args.get("search", "")
    city = request.args.get("city", "")

    query = Room.query.filter_by(
        owner_id=session["user_id"]
    )

    if search:

         query = query.filter(
            or_(
                Room.area.ilike(f"%{search}%"),
                Room.city.ilike(f"%{search}%"),
                Room.room_type.ilike(f"%{search}%")
            )
        )

    if city:
        query = query.filter_by(
            city=city
        )

    rooms = query.order_by(
        Room.id.desc()
    ).all()

    total_rooms = Room.query.filter_by(
        owner_id=session["user_id"]
    ).count()

    approved_rooms = Room.query.filter_by(
        owner_id=session["user_id"],
        approved=True
    ).count()

    pending_rooms = Room.query.filter_by(
        owner_id=session["user_id"],
        approved=False
    ).count()

    featured_rooms = Room.query.filter_by(
        owner_id=session["user_id"],
        featured=True
    ).count()

    cities = db.session.query(
        Room.city
    ).filter_by(
        owner_id=session["user_id"]
    ).distinct().all()
    cities = [c[0] for c in cities]

    wallet = Wallet.query.filter_by(
       user_id=session["user_id"]
    ).first()

    wallet_balance = 0

    if wallet:
        wallet_balance = wallet.balance

    return render_template(
        "owner/rooms.html",

        rooms=rooms,

        total_rooms=total_rooms,
        approved_rooms=approved_rooms,
        pending_rooms=pending_rooms,
        featured_rooms=featured_rooms,
        wallet_balance=wallet_balance,

        cities=cities,
        selected_city=city,
        search=search
    )

@app.route("/owner/edit-room/<int:room_id>", methods=["GET", "POST"])
def edit_room(room_id):

    if session.get("role") != "owner":
        return redirect(url_for("login"))

    room = Room.query.get_or_404(room_id)

    if room.owner_id != session["user_id"]:
        return redirect(url_for("owner_rooms"))

    if request.method == "POST":

        # =========================
        # BASIC INFO
        # =========================

        room.title = request.form.get("title")

        room.city = request.form.get("city")

        room.area = request.form.get("area")

        room.rent = int(
            request.form.get("rent")
        ) if request.form.get("rent") else 0

        room.deposit_amount = int(
            request.form.get("deposit_amount")
        ) if request.form.get("deposit_amount") else 0

        room.room_type = request.form.get(
            "room_type"
        )

        room.description = request.form.get(
            "description"
        )

        # =========================
        # LOCATION
        # =========================

        room.province = request.form.get(
            "province"
        )

        room.district = request.form.get(
            "district"
        )

        room.address = request.form.get(
            "address"
        )

        room.latitude = float(
            request.form.get("latitude")
        ) if request.form.get("latitude") else None

        room.longitude = float(
            request.form.get("longitude")
        ) if request.form.get("longitude") else None

        # =========================
        # ROOM DETAILS
        # =========================

        room.room_capacity = int(
            request.form.get("room_capacity")
        ) if request.form.get("room_capacity") else 1

        room.bathroom_count = int(
            request.form.get("bathroom_count")
        ) if request.form.get("bathroom_count") else 1

        room.floor_number = int(
            request.form.get("floor_number")
        ) if request.form.get("floor_number") else 0

        room.room_size = int(
            request.form.get("room_size")
        ) if request.form.get("room_size") else None

        room.facing_direction = request.form.get(
            "facing_direction"
        )

        room.building_type = request.form.get(
            "building_type"
        )

        room.kitchen_available = (
            "kitchen_available"
            in request.form
        )

        room.parking_available = (
            "parking_available"
            in request.form
        )

        room.balcony_available = (
            "balcony_available"
            in request.form
        )

        room.furnished = (
            "furnished"
            in request.form
        )

        room.attached_bathroom = (
            "attached_bathroom"
            in request.form
        )

        # =========================
        # FACILITIES
        # =========================

        room.facilities = ",".join(
            request.form.getlist(
                "facilities"
            )
        )

        # =========================
        # PREFERENCES
        # =========================

        room.tenant_preference = request.form.get(
            "tenant_preference"
        )

        room.gender_preference = request.form.get(
            "gender_preference"
        )

        room.smoking_allowed = (
            "smoking_allowed"
            in request.form
        )

        room.alcohol_allowed = (
            "alcohol_allowed"
            in request.form
        )

        room.pets_allowed = (
            "pets_allowed"
            in request.form
        )

        # =========================
        # CONTACT
        # =========================

        room.owner_phone = request.form.get(
            "owner_phone"
        )

        # =========================
        # IMAGE UPDATE (OPTIONAL)
        # =========================

        uploaded_files = request.files.getlist(
            "images"
        )

        image_names = []

        for file in uploaded_files:

            if file and file.filename:

                filename = secure_filename(
                    file.filename
                )

                file.save(
                    os.path.join(
                        ROOM_IMAGE_FOLDER,
                        filename
                    )
                )

                image_names.append(
                    filename
                )

        if image_names:

            room.images = ",".join(
                image_names
            )

        # =========================
        # REQUIRES RE-APPROVAL
        # =========================

        room.approved = False


        # =========================
        # ADMIN NOTIFICATION
        # =========================

        admins = User.query.filter_by(
            role="admin"
        ).all()

        for admin in admins:

            notify(
                admin.id,
                f"Room updated and awaiting approval: {room.title}",
                "/admin/rooms"
            )
        db.session.commit()

        flash(
            "Room updated successfully and sent for admin approval."
        )

        return redirect(
            url_for("owner_rooms")
        )

    return render_template(
        "owner/add_room.html",
        room=room,
        edit_mode=True
    )

@app.route("/owner/delete-room/<int:room_id>")
def delete_room(room_id):

    if session.get("role") != "owner":
        return redirect(url_for("login"))

    room = Room.query.get_or_404(room_id)

    if room.owner_id != session["user_id"]:
        return redirect(url_for("owner_rooms"))

    db.session.delete(room)
    db.session.commit()

    flash("Room deleted successfully")

    return redirect(url_for("owner_rooms"))

@app.route("/favorites")
def favorites():

    if session.get("role") != "renter":
        return redirect(url_for("login"))

    favorites = (
        db.session.query(Favorite, Room)
        .join(Room, Favorite.room_id == Room.id)
        .filter(
            Favorite.renter_id ==
            session["user_id"]
        )
        .all()
    )

    return render_template(
        "renter/favorites.html",
        favorites=favorites
    )

@app.route("/owner/accept/<int:aid>")
def accept(aid):

    a = Application.query.get_or_404(aid)

    a.status = "accepted"


    notify(
        a.renter_id,
        "Your application has been accepted 🎉",
        f"/chat/{a.room_id}"
    )
    db.session.commit()

    return redirect(url_for("owner_apps"))

@app.route("/owner/reject/<int:aid>")
def reject(aid):

    a = Application.query.get_or_404(aid)

    a.status = "rejected"


    notify(
        a.renter_id,
        "Your application was rejected",
        "/renter/applications"
    )
    db.session.commit()

    return redirect(url_for("owner_apps"))

@app.route("/owner/wallet")
def owner_wallet():

    if session.get("role") != "owner":
        return redirect("/login")

    wallet = Wallet.query.filter_by(
        user_id=session["user_id"]
    ).first()

    transactions = (
        WalletTransaction.query
        .filter_by(user_id=session["user_id"])
        .order_by(
            WalletTransaction.id.desc()
        )
        .all()
    )

    return render_template(
        "owner/wallet.html",
        wallet=wallet,
        transactions=transactions
    )

@app.route("/owner/wallet/load")
def load_wallet():

    if session.get("role") != "owner":
        return redirect("/login")

    return render_template(
        "owner/load_wallet.html"
    )
@app.route(
    "/wallet/deposit",
    methods=["POST"]
)
def wallet_deposit():

    if "user_id" not in session:
        return redirect("/login")

    screenshot = request.files.get(
        "screenshot"
    )

    filename = ""

    if screenshot and screenshot.filename:

        filename = secure_filename(
            screenshot.filename
        )

        screenshot.save(
            os.path.join(
                UPLOAD_FOLDER,
                filename
            )
        )

    txn = WalletTransaction(

        user_id=session["user_id"],

        amount=float(
            request.form["amount"]
        ),

        transaction_code=request.form[
            "transaction_code"
        ],

        screenshot=filename,

        status="pending"
    )

    db.session.add(txn)

    db.session.commit()
    admins = User.query.filter_by(
       role="admin"
    ).all()

    for admin in admins:

        notify(
            admin.id,
            f"New wallet deposit request: Rs. {txn.amount}",
            "/admin/wallet-deposits"
        )
    db.session.commit()

    flash(
        "Deposit request submitted successfully. Waiting for admin approval.",
        "success"
    )

    return redirect(
        "/owner/wallet"
    )

# ================= RENTER =================
@app.route("/renter/dashboard")
def renter_dashboard():

    if session.get("role") != "renter":
        return redirect(url_for("login"))

    renter_id = session["user_id"]

    favorite_count = Favorite.query.filter_by(
        renter_id=renter_id
    ).count()

    application_count = Application.query.filter_by(
        renter_id=renter_id
    ).count()

    unread_messages = Message.query.filter_by(
        receiver_id=renter_id,
        is_read=False
    ).count()

    recommended_rooms = Room.query.filter_by(
        approved=True
    ).order_by(
        Room.featured.desc(),
        Room.id.desc()
    ).limit(6).all()

    cities = (
        db.session.query(Room.city)
        .filter(Room.approved == True)
        .distinct()
        .all()
    )

    return render_template(
        "renter/dashboard.html",
        favorite_count=favorite_count,
        application_count=application_count,
        unread_messages=unread_messages,
        recommended_rooms=recommended_rooms,
        cities=[c[0] for c in cities]
    )

@app.route("/rooms/<city>")
def rooms(city):

    room_type = request.args.get("room_type")
    max_price = request.args.get("max_price")
    print("MAX PRICE =", max_price)

    wifi = request.args.get("wifi")
    parking = request.args.get("parking")
    water = request.args.get("water")

    query = Room.query.filter_by(
        city=city,
        approved=True
    )

    if room_type and room_type != "All":
        query = query.filter(
            Room.room_type == room_type
        )

    if max_price:
        query = query.filter(
            Room.rent <= int(max_price)
        )

    if wifi:
        query = query.filter(
            Room.facilities.ilike("%wifi%")
        )

    if parking:
        query = query.filter(
            Room.facilities.ilike("%parking%")
        )

    if water:
        query = query.filter(
            Room.facilities.ilike("%water%")
        )

    rooms = query.order_by(
        Room.featured.desc(),
        Room.id.desc()
    ).all()

    return render_template(
        "renter/rooms.html",
        rooms=rooms,
        city=city
    )

@app.route("/search")
def search_rooms():

    city = request.args.get("city", "")
    area = request.args.get("area", "")
    room_type = request.args.get("room_type", "")

    query = Room.query.filter_by(approved=True)

    if city:
        query = query.filter(Room.city.ilike(f"%{city}%"))

    if area:
        query = query.filter(Room.area.ilike(f"%{area}%"))

    if room_type:
        query = query.filter(Room.room_type == room_type)

    rooms = query.order_by(
        Room.featured.desc(),
        Room.id.desc()
    ).all()

    return render_template(
        "renter/rooms.html",
        rooms=rooms,
        city=city or "Search Results"
    )

# ================= FAVORITES =================

@app.route("/favorite/<int:room_id>")
def favorite(room_id):

    if session.get("role") != "renter":
        return redirect(url_for("login"))

    existing = Favorite.query.filter_by(
        renter_id=session["user_id"],
        room_id=room_id
    ).first()

    if not existing:

        fav = Favorite(
            renter_id=session["user_id"],
            room_id=room_id
        )

        db.session.add(fav)
        db.session.commit()

        flash("Room saved ❤️")

    return redirect(request.referrer or "/")

@app.route("/room/<int:rid>")
def room_detail(rid):
    room = Room.query.get_or_404(rid)

    print("ROOM IMAGES =", room.images)

    owner = db.session.get(User,room.owner_id)

    app_status = None
    if session.get("role") == "renter":
        app = Application.query.filter_by(
            room_id=rid,
            renter_id=session["user_id"]
        ).first()
        if app:
            app_status = app.status

    return render_template(
        "room/detail.html",
        room=room,
        owner=owner,
        app_status=app_status
    )

@app.route("/apply/<int:rid>")
def apply(rid):

    if session.get("role") != "renter":
        return redirect(url_for("login"))

    room = Room.query.get_or_404(rid)

    existing = Application.query.filter_by(
        room_id=rid,
        renter_id=session["user_id"]
    ).first()

    if existing:
        flash("You already applied for this room.")
        return redirect(url_for("renter_apps"))

    application = Application(
        room_id=rid,
        renter_id=session["user_id"],
        status="pending"
    )

    db.session.add(application)

    notify(
        room.owner_id,
        f"{session['name']} applied for your room",
        "/owner/applications"
    )
    db.session.commit()

    return redirect(url_for("renter_apps"))

@app.route("/renter/applications")
def renter_apps():
    apps = (
        db.session.query(Application, Room)
        .join(Room, Application.room_id == Room.id)
        .filter(Application.renter_id == session["user_id"])
        .all()
    )
    return render_template("renter/applications.html", apps=apps)

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect("/login")

    notes = Notification.query.filter_by(
        user_id=session["user_id"]
    ).all()

    for n in notes:
        n.is_read = True

    db.session.commit()

    return render_template(
        "notifications.html",
        notes=notes
    )

# ================= CHAT =================
@app.route("/chat/<int:rid>", methods=["GET", "POST"])
def chat(rid):
    if "user_id" not in session:
        return redirect(url_for("login"))

    room = Room.query.get_or_404(rid)
    user_id = session["user_id"]
    role = session.get("role")

    if role == "renter":
        app = Application.query.filter_by(
            room_id=rid, renter_id=user_id, status="accepted"
        ).first()
        if not app:
            flash("Chat available only after approval.")
            return redirect(url_for("renter_apps"))
        receiver_id = room.owner_id

    elif role == "owner":
        app = Application.query.filter_by(
            room_id=rid, status="accepted"
        ).first()
        if not app:
            flash("No accepted renter yet.")
            return redirect(url_for("owner_apps"))
        receiver_id = app.renter_id
    else:
        return redirect(url_for("login"))

    if request.method == "POST":
        db.session.add(Message(
            room_id=rid,
            sender_id=user_id,
            receiver_id=receiver_id,
            text=request.form["text"],
            is_read=False
        ))
        notify(
            receiver_id,
            f"New message from {session['name']}",
            f"/chat/{rid}"
        )
        db.session.commit()
        return redirect(url_for("chat", rid=rid))

    Message.query.filter_by(
        room_id=rid,
        receiver_id=user_id,
        is_read=False
    ).update({"is_read": True})
    db.session.commit()

    messages = (
        db.session.query(Message, User)
        .join(User, Message.sender_id == User.id)
        .filter(Message.room_id == rid)
        .order_by(Message.id)
        .all()
    )

    chat_user = db.session.get(User,receiver_id)

    return render_template(
        "chat/chat.html",
        messages=messages,
        room=room,
        chat_user=chat_user
    )

@app.route("/messages")
def messages():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conversations = []

    if session["role"] == "renter":

        apps = Application.query.filter_by(
            renter_id=user_id,
            status="accepted"
        ).all()

        for app in apps:

            room = db.session.get(Room, app.room_id)

            owner = db.session.get(User, room.owner_id)

            last_msg = Message.query.filter_by(
                room_id=room.id
            ).order_by(
                Message.created_at.desc()
            ).first()

            conversations.append(
                (room, owner, last_msg)
            )

    else:

        rooms = Room.query.filter_by(
            owner_id=user_id
        ).all()

        for room in rooms:

            app = Application.query.filter_by(
                room_id=room.id,
                status="accepted"
            ).first()

            if app:

                renter = db.session.get(User,
                    app.renter_id
                )

                last_msg = Message.query.filter_by(
                    room_id=room.id
                ).order_by(
                    Message.created_at.desc()
                ).first()

                conversations.append(
                    (room, renter, last_msg)
                )

    return render_template(
        "chat/inbox.html",
        conversations=conversations
    )

# ================= SOCKET CHAT =================

@socketio.on("join")
def handle_join(data):

    room = str(data["room"])

    join_room(room)


@socketio.on("send_message")
def handle_message(data):

    emit(
        "receive_message",
        data,
        room=str(data["room"])
    )

# ================= PROFILE =================
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    u = db.session.get(User, session["user_id"])

    if request.method == "POST":
        file = request.files.get("photo")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(PROFILE_IMAGE_FOLDER, filename))
            u.profile_image = filename
            db.session.commit()

    return render_template("profile/profile.html", user=u)

# ================= RUN =================
if __name__ == "__main__":

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True
    )