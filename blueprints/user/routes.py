from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from services.db import get_db
from utils.auth import login_required, role_required
from bson import ObjectId

# ✅ Blueprint for user module
user_bp = Blueprint('user', __name__, template_folder='templates')

@user_bp.route('/dashboard')
@login_required
@role_required('user')
def dashboard():
    return render_template('user/dashboard.html')


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('user')
def profile():
    db = get_db()
    user_id = session.get('user_id')  # Get user_id from session
    user = db.users.find_one({'_id': ObjectId(user_id)}) if user_id else None

    if not user:
        flash('User not found. Please login again.', 'danger')
        return redirect(url_for('auth.login'))

    # Fetch all courses from courses collection
    # Fetch unique course names from courses collection
    # Fetch and normalize unique courses
    courses_cursor = db.courses.find({}, {"courses": 1, "_id": 0})
    all_courses = []

    for doc in courses_cursor:
        if "courses" in doc:
            # Split by comma, strip spaces
            items = [c.strip() for c in doc["courses"].split(",")]
            all_courses.extend(items)

    # Deduplicate and sort
    unique_courses = sorted(set(all_courses))

    if request.method == 'POST':
        academic_profile = {
            'tenth_percent': request.form.get('tenth_percent'),
            'twelfth_percent': request.form.get('twelfth_percent'),
            'graduation_cgpa': request.form.get('graduation_cgpa'),
            'entrance_score': request.form.get('entrance_score'),
        }
        location_pref = request.form.get('location_pref')
        budget_raw = request.form.get('budget')
        budget = float(budget_raw) if budget_raw not in (None, '',) else None
        desired_course = request.form.get('desired_course')

        # Insert or update in students collection only
        student_doc = db.students.find_one({'user_id': user_id})
        student_data = {
            'user_id': user_id,
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'academic_profile': academic_profile,
            'location_pref': location_pref,
            'budget': budget,
            'desired_course': desired_course
        }
        if student_doc:
            db.students.update_one({'user_id': user_id}, {'$set': student_data})
        else:
            db.students.insert_one(student_data)

        flash('Student profile saved successfully!', 'success')
        return redirect(url_for('user.profile'))

    return render_template("user/profile.html", user=user, courses=unique_courses)


@user_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
@role_required('user')
def edit_profile():
    db = get_db()
    user_id = session.get('user_id')  # Use user_id instead of email
    user = db.users.find_one({'_id': ObjectId(user_id)}) if user_id else None

    if not user:
        flash('User not found. Please login again.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        return profile()  # reuse save logic

    return render_template('user/edit_profile.html', user=user)

@user_bp.route('/recommendations')
@login_required
@role_required('user')
def recommendations():
    db = get_db()
    user_id = session.get('user_id')

    if not user_id:
        flash("Please login again.", "danger")
        return redirect(url_for("auth.login"))

    student = db.students.find_one({'user_id': user_id})
    if not student:
        return "Student profile not found!", 404

    colleges = list(db.colleges.find({}))
    recommended = []

    for college in colleges:
        score = 0

        # Desired course match
        if student.get('desired_course') and college.get('courses'):
            if student['desired_course'].lower() in [c.lower() for c in college['courses']]:
                score += 3

        # Location match
        if student.get('location_pref') and college.get('city'):
            if student['location_pref'].lower() in college['city'].lower():
                score += 2

        # Budget match
        if student.get('budget') and college.get('avg_fee'):
            if student['budget'] >= college['avg_fee']:
                score += 1

        # Academic profile match
        if student.get('academic_profile'):
            grad_cgpa = student['academic_profile'].get('graduation_cgpa', 0)
            if college.get('cutoff') and grad_cgpa >= college['cutoff']:
                score += 2

        if score > 0:
            # Set default image if not present
            if not college.get('image'):
                college['image'] = 'default_college.jpg'  # make sure this file exists in static/image/
            # Generate URL for template
            college['image_url'] = url_for('static', filename=f'image/{college["image"]}')
            recommended.append((college, score))

    # Fallback: only desired course
    if not recommended and student.get('desired_course'):
        for college in colleges:
            if student['desired_course'].lower() in [c.lower() for c in college.get('courses', [])]:
                if not college.get('image'):
                    college['image'] = 'default_college.jpg'
                college['image_url'] = url_for('static', filename=f'image/{college["image"]}')
                recommended.append((college, 3))

    # Sort by score descending
    recommended.sort(key=lambda x: x[1], reverse=True)
    recommended_colleges = [col[0] for col in recommended]

    return render_template(
        'user/recommendations.html',
        recommendations=recommended_colleges,
        student=student
    )
