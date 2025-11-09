from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from services.db import get_db
from utils.auth import login_required, role_required
from bson import ObjectId
from .ml_recommender import recommender
user_bp = Blueprint('user', __name__, template_folder='templates')


@user_bp.route('/dashboard')
@login_required
@role_required('user')
def dashboard():
    return render_template('user/dashboard.html')


@user_bp.route('/profile')
@login_required
@role_required('user')
def profile():
    """View profile page"""
    db = get_db()
    user_id = session.get('user_id')

    # Get user from users collection
    user = db.users.find_one({'_id': ObjectId(user_id)}) if user_id else None
    if not user:
        flash('User not found. Please login again.', 'danger')
        return redirect(url_for('auth.login'))

    # Get student data from students collection
    student = db.students.find_one({'user_id': user_id})

    # Merge user and student data for the template
    if student:
        user.update({
            'first_name': student.get('first_name', user.get('first_name', '')),
            'last_name': student.get('last_name', user.get('last_name', '')),
            'academic_profile': student.get('academic_profile', {}),
            'desired_course': student.get('desired_course', ''),
            'location_pref': student.get('location_pref', ''),
            'budget': student.get('budget', '')
        })

    # Fetch courses for the dropdown
    courses_cursor = db.courses.find({}, {"courses": 1, "_id": 0})
    all_courses = []
    for doc in courses_cursor:
        if "courses" in doc:
            items = [c.strip() for c in doc["courses"].split(",")]
            all_courses.extend(items)
    unique_courses = sorted(set(all_courses))

    return render_template("user/profile.html", user=user, courses=unique_courses)


@user_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
@role_required('user')
def edit_profile():
    db = get_db()
    user_id = session.get('user_id')

    # Get user from users collection
    user = db.users.find_one({'_id': ObjectId(user_id)}) if user_id else None
    if not user:
        flash('User not found. Please login again.', 'danger')
        return redirect(url_for('auth.login'))

    # Get student data from students collection
    student = db.students.find_one({'user_id': user_id})

    # Merge user and student data for the template
    if student:
        user.update({
            'first_name': student.get('first_name', user.get('first_name', '')),
            'last_name': student.get('last_name', user.get('last_name', '')),
            'academic_profile': student.get('academic_profile', {}),
            'desired_course': student.get('desired_course', ''),
            'location_pref': student.get('location_pref', ''),
            'budget': student.get('budget', '')
        })

    if request.method == 'POST':
        # Update users collection
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name')
            }}
        )

        # Update session data
        session['first_name'] = request.form.get('first_name')
        session['last_name'] = request.form.get('last_name')

        # Prepare academic profile
        academic_profile = {
            'tenth_percent': float(request.form.get('tenth_percent')) if request.form.get('tenth_percent') else None,
            'twelfth_percent': float(request.form.get('twelfth_percent')) if request.form.get(
                'twelfth_percent') else None,
            'graduation_cgpa': float(request.form.get('graduation_cgpa')) if request.form.get(
                'graduation_cgpa') else None,
            'entrance_score': float(request.form.get('entrance_score')) if request.form.get('entrance_score') else None,
        }

        # Prepare other fields
        location_pref = request.form.get('location_pref')
        budget_raw = request.form.get('budget')
        budget = float(budget_raw) if budget_raw and budget_raw.strip() else None
        desired_course = request.form.get('desired_course')

        # Update or insert in students collection
        student_data = {
            'user_id': user_id,
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'academic_profile': academic_profile,
            'location_pref': location_pref,
            'budget': budget,
            'desired_course': desired_course
        }

        if student:
            db.students.update_one({'user_id': user_id}, {'$set': student_data})
        else:
            db.students.insert_one(student_data)

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))  # Redirect to profile page after save

    return render_template('user/edit_profile.html', user=user)


def initialize_recommender():
    """Initialize ML recommender with college data"""
    try:
        db = get_db()
        colleges = list(db.colleges.find({}))

        if not colleges:
            logger.warning("No colleges found in database")
            return False

        recommender.fit(colleges)
        return True

    except Exception as e:
        logger.error(f"Error initializing recommender: {e}")
        return False


@user_bp.route('/recommendations')
@login_required
@role_required('user')
def recommendations():
    db = get_db()
    user_id = session.get('user_id')

    if not user_id:
        flash("Please login again.", "danger")
        return redirect(url_for("auth.login"))

    # Get student profile
    student = db.students.find_one({'user_id': user_id})
    if not student:
        flash("Please complete your profile first.", "warning")
        return redirect(url_for('user.edit_profile'))

    # Initialize recommender on first use
    if not recommender.is_fitted:
        initialize_recommender()

    recommendations_list = []

    # Try ML recommendations first
    if recommender.is_fitted:
        try:
            recommendations_list = recommender.recommend(student, top_n=12)
        except Exception as e:
            logger.error(f"ML recommendation failed: {e}")
            recommendations_list = get_basic_recommendations(db, student)
    else:
        # Fallback to basic recommendations
        recommendations_list = get_basic_recommendations(db, student)
        flash("Using basic matching while we improve our recommendation system.", "info")

    return render_template(
        'user/recommendations.html',
        recommendations=recommendations_list,
        student=student
    )


def get_basic_recommendations(db, student):
    """Fallback basic recommendation system"""
    colleges = list(db.colleges.find({}))
    scored_colleges = []

    for college in colleges:
        score = 0

        # Course match
        if student.get('desired_course') and college.get('courses'):
            college_courses = []
            if isinstance(college['courses'], str):
                college_courses = [c.strip().lower() for c in college['courses'].split(',')]
            elif isinstance(college['courses'], list):
                college_courses = [c.lower() for c in college['courses']]

            if student['desired_course'].lower() in college_courses:
                score += 30

        # Location match
        if student.get('location_pref') and college.get('city'):
            if student['location_pref'].lower() in college['city'].lower():
                score += 20

        # Budget match
        if student.get('budget') and college.get('avg_fee'):
            try:
                student_budget = float(student['budget'])
                college_fee = float(college['avg_fee'])
                if student_budget >= college_fee:
                    score += 10
            except (ValueError, TypeError):
                pass

        if score > 0:
            college['match_score'] = min(score, 100)
            college['match_percentage'] = f"{college['match_score']}%"
            scored_colleges.append(college)

    scored_colleges.sort(key=lambda x: x['match_score'], reverse=True)
    return scored_colleges[:12]