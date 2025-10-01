from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from services.db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ------------------- REGISTER -------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    db = get_db()
    if request.method == "POST":
        role = request.form.get("role", "user")  # default 'user'
        email = request.form.get("email")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)

        # Check if email already exists
        if db.users.find_one({"email": email}):
            flash("Email already registered!", "danger")
            return redirect(url_for("auth.register"))

        if role == "user":
            # Student registration
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")

            # Insert into users collection
            user_id = db.users.insert_one({
                "email": email,
                "password": hashed_password,
                "role": "user",
                "first_name": first_name,
                "last_name": last_name
            }).inserted_id

            # Insert into students collection
            db.students.insert_one({
                "user_id": str(user_id),
                "first_name": first_name,
                "last_name": last_name,
                "academic_profile": {},
                "location_pref": "",
                "budget": None,
                "desired_course": ""
            })

        elif role == "college":
            # College registration
            college_name = request.form.get("college_name")
            location = request.form.get("location")
            exam_accepted = request.form.get("exam")
            courses_raw = request.form.get("courses", "")
            courses_list = [c.strip() for c in courses_raw.split(",") if c.strip()]

            # Insert into users collection
            user_id = db.users.insert_one({
                "email": email,
                "password": hashed_password,
                "role": "college",
                "college_name": college_name
            }).inserted_id

            # Insert into colleges collection
            db.colleges.insert_one({
                "user_id": str(user_id),
                "college_name": college_name,
                "location": location,
                "exam_accepted": exam_accepted,
                "courses": courses_list
            })

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ------------------- LOGIN -------------------
# ------------------- LOGIN -------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    db = get_db()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.users.find_one({"email": email})

        if user and check_password_hash(user["password"], password):
            # Store session
            session["user_id"] = str(user["_id"])
            session["role"] = user.get("role", "user")

            # Store name in session correctly
            if session["role"] == "user":
                session["first_name"] = user.get("first_name", "")
                session["last_name"] = user.get("last_name", "")
            elif session["role"] == "college":
                session["college_name"] = user.get("college_name", "")

            flash("Login successful!", "success")

            # Redirect based on role
            if session["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            elif session["role"] == "college":
                return redirect(url_for("college.dashboard"))
            else:  # student
                return redirect(url_for("user.dashboard"))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.login"))

    return render_template("auth/login.html")


# ------------------- LOGOUT -------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
