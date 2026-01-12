from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response
)
from config import Config
from models import db, User, Room, Application, Message, Review
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

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
    admin_alerts = 0

    if "user_id" in session:
        current_user = User.query.get(session["user_id"])
        unread_count = Message.query.filter_by(
            receiver_id=session["user_id"],
            is_read=False
        ).count()

        if session.get("role") == "admin":
            admin_alerts = (
                Room.query.filter_by(approved=False).count() +
                Application.query.filter_by(status="pending").count()
            )

    return dict(
        current_user=current_user,
        unread_count=unread_count,
        admin_alerts=admin_alerts
    )

# ================= AUTH =================
@app.route("/")
def home():
    return render_template("home.html")

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
        return redirect(url_for("login"))
    return render_template("auth/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(email=request.form["email"]).first()
        if u and u.check_password(request.form["password"]):
            session["user_id"] = u.id
            session["role"] = u.role
            return redirect(url_for("dashboard"))
        flash("Invalid credentials")
    return render_template("auth/login.html")

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

# ================= ADMIN =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin/dashboard.html")

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
    db.session.commit()
    return redirect(url_for("admin_rooms"))

@app.route("/admin/reject-room/<int:room_id>")
def reject_room(room_id):
    room = Room.query.get_or_404(room_id)
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


# ================= OWNER =================
@app.route("/owner/dashboard")
def owner_dashboard():
    if session.get("role") != "owner":
        return redirect(url_for("login"))
    return render_template("owner/dashboard.html")

@app.route("/owner/add-room", methods=["GET", "POST"])
def add_room():
    if request.method == "POST":
        print("FILES RECEIVED:", request.files)
        print("FILES LIST:", request.files.getlist("images"))


    if session.get("role") != "owner":
        return redirect(url_for("login"))

    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        image_names = []

    
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(ROOM_IMAGE_FOLDER, filename))
                image_names.append(filename)

        room = Room(
            owner_id=session["user_id"],
            city=request.form["city"],
            area=request.form["area"],
            rent=request.form["rent"],
            room_type=request.form["room_type"],
            facilities=request.form["facilities"],
            description=request.form["description"],
            approved=False,
            images=",".join(image_names)
        )

        db.session.add(room)
        db.session.commit()
        flash("Room added successfully and sent for approval")
        return redirect(url_for("owner_dashboard"))

    return render_template("owner/add_room.html")

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

@app.route("/owner/accept/<int:aid>")
def accept(aid):
    a = Application.query.get_or_404(aid)
    a.status = "accepted"
    db.session.commit()
    return redirect(url_for("owner_apps"))

@app.route("/owner/reject/<int:aid>")
def reject(aid):
    a = Application.query.get_or_404(aid)
    a.status = "rejected"
    db.session.commit()
    return redirect(url_for("owner_apps"))

# ================= RENTER =================
@app.route("/renter/dashboard")
def renter_dashboard():
    if session.get("role") != "renter":
        return redirect(url_for("login"))
    return render_template("renter/dashboard.html")

@app.route("/rooms/<city>")
def rooms(city):
    rooms = Room.query.filter_by(city=city, approved=True).all()
    return render_template("renter/rooms.html", rooms=rooms, city=city)

@app.route("/room/<int:rid>")
def room_detail(rid):
    room = Room.query.get_or_404(rid)
    owner = User.query.get(room.owner_id)

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

    db.session.add(Application(
        room_id=rid,
        renter_id=session["user_id"],
        status="pending"
    ))
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

    chat_user = User.query.get(receiver_id)

    return render_template(
        "chat/chat.html",
        messages=messages,
        room=room,
        chat_user=chat_user
    )

# ================= PROFILE =================
@app.route("/profile", methods=["GET", "POST"])
def profile():
    u = User.query.get(session["user_id"])

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
    app.run(debug=True)
