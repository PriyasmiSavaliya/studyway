import os
import datetime
from math import ceil

from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from blueprints.college.routes import allowed_file
from services.db import get_db
from utils.auth import login_required, role_required
from blueprints.admin.ml_dashboard import analyze_user_growth, top_courses, top_ranked_colleges, \
    college_distribution_by_state, evaluate_user_growth_accuracy, course_placement_data

admin_bp = Blueprint('admin', __name__, template_folder='templates')

UPLOAD_FOLDER = 'static/image'


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    db = get_db()

    admin_name = "Admin"

    # Fetch from session if admin_id exists
    admin_id = session.get('admin_id')
    if admin_id:
        admin_doc = db.users.find_one({'_id': ObjectId(admin_id), 'role': 'admin'})
        if admin_doc:
            admin_name = admin_doc.get('name', 'Admin')

    users = list(db.users.find({}))
    colleges = list(db.colleges.find({}))
    courses = list(db.courses.find({}))

    # Existing functions
    user_growth = analyze_user_growth(users)
    state_data = college_distribution_by_state(colleges)
    course_data = top_courses(courses)
    top_colleges = top_ranked_colleges(colleges)
    model_metrics = evaluate_user_growth_accuracy(users)
    course_placement_chart = course_placement_data(courses, users)

    # Dynamic card metrics
    total_users = len(users)
    if len(user_growth['counts']) > 1:
        user_growth_percentage = round(
            ((user_growth['counts'][-1] - user_growth['counts'][-2]) / user_growth['counts'][-2]) * 100, 2
        )
    else:
        user_growth_percentage = 0

    total_colleges = len(colleges)
    top_state_colleges = state_data['states'][0] if state_data['states'] else "N/A"

    if top_colleges['colleges']:
        top_college_name = top_colleges['colleges'][0]
        top_college_rank = top_colleges['rankings'][0]
    else:
        top_college_name = "N/A"
        top_college_rank = "N/A"

    return render_template(
        'admin/dashboard.html',
        admin_name=admin_name,
        user_growth=user_growth,
        state_data=state_data,
        course_data=course_data,
        top_colleges=top_colleges,
        model_metrics=model_metrics,
        # Card data
        total_users=total_users,
        users=users,
        enumerate=enumerate,
        user_growth_percentage=user_growth_percentage,
        total_colleges=total_colleges,
        top_state_colleges=top_state_colleges,
        top_college_name=top_college_name,
        top_college_rank=top_college_rank,
        chart4_data=course_placement_chart  # pass to template
    )


@admin_bp.route('/colleges')
@login_required
@role_required('admin')
def list_colleges():
    db = get_db()
    page = int(request.args.get('page', 1))  # current page
    per_page = 10

    total_count = db.colleges.count_documents({})
    total_pages = ceil(total_count / per_page)

    items = list(
        db.colleges.find({})
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    return render_template(
        'admin/colleges_list.html',
        items=items,
        page=page,
        total_pages=total_pages
    )


@admin_bp.route('/colleges/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_college():
    db = get_db()
    if request.method == 'POST':
        image_file = request.files.get('image')
        image_filename = None

        if image_file and image_file.filename != '' and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
            image_file.save(image_path)
            image_filename = filename

        courses_list = [c.strip() for c in request.form.get('courses', '').split(',') if c.strip()]
        facilities_list = [f.strip() for f in request.form.get('facilities', '').split(',') if f.strip()]

        # Insert college first to get its ID
        college_doc = {
            'college_name': request.form.get('college_name'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'college_website': request.form.get('college_website'),
            'ranking': request.form.get('ranking', type=int),
            'avg_fee': request.form.get('avg_fee', type=float),
            'placement_rating': request.form.get('placement_rating', type=float),
            'exam': request.form.get('exam'),
            'cutoff': request.form.get('cutoff'),
            'description': request.form.get('description'),
            'facilities': facilities_list,
            'courses': courses_list,  # store course names here
            'image': image_filename
        }
        result = db.colleges.insert_one(college_doc)
        college_id = result.inserted_id

        # Insert courses in courses collection with college_id
        for course_name in courses_list:
            if not db.courses.find_one({'course_name': course_name, 'college_id': college_id}):
                db.courses.insert_one({
                    'course_name': course_name,
                    'college_id': college_id
                })

        flash('College added with courses.', 'success')
        return redirect(url_for('admin.list_colleges'))

    return render_template('admin/college_form.html', item=None)


@admin_bp.route('/colleges/<id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_college(id):
    db = get_db()
    item = db.colleges.find_one({'_id': ObjectId(id)})
    if not item:
        flash('College not found.', 'warning')
        return redirect(url_for('admin.list_colleges'))

    if request.method == 'POST':
        image_file = request.files.get('image')
        image_filename = item.get('image')

        if image_file and image_file.filename != '' and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
            image_file.save(image_path)
            image_filename = filename

        courses_list = [c.strip() for c in request.form.get('courses', '').split(',') if c.strip()]
        facilities_list = [f.strip() for f in request.form.get('facilities', '').split(',') if f.strip()]

        # Insert new courses in courses collection with college_id if not exists
        for course_name in courses_list:
            if not db.courses.find_one({'course_name': course_name, 'college_id': ObjectId(id)}):
                db.courses.insert_one({
                    'course_name': course_name,
                    'college_id': ObjectId(id)
                })

        update = {
            'college_name': request.form.get('college_name'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'college_website': request.form.get('college_website'),
            'ranking': request.form.get('ranking', type=int),
            'avg_fee': request.form.get('avg_fee', type=float),
            'placement_rating': request.form.get('placement_rating', type=float),
            'exam': request.form.get('exam'),
            'cutoff': request.form.get('cutoff'),
            'description': request.form.get('description'),
            'facilities': facilities_list,
            'courses': courses_list,  # update course names
            'image': image_filename
        }
        db.colleges.update_one({'_id': ObjectId(id)}, {'$set': update})
        flash('College updated with courses.', 'success')
        return redirect(url_for('admin.list_colleges'))

    return render_template('admin/college_form.html', item=item)


@admin_bp.route('/colleges/<id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_college(id):
    db = get_db()
    db.colleges.delete_one({'_id': ObjectId(id)})
    flash('College deleted.', 'info')
    return redirect(url_for('admin.list_colleges'))


# USER MANAGEMENT ROUTES

@admin_bp.route('/users')
@login_required
@role_required('admin')
def list_users():
    db = get_db()
    page = int(request.args.get('page', 1))
    per_page = 10

    total_count = db.users.count_documents({})
    total_pages = (total_count + per_page - 1) // per_page

    users = list(
        db.users.find({})
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    return render_template(
        'admin/users_list.html',
        users=users,
        page=page,
        total_pages=total_pages
    )


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_user():
    db = get_db()
    if request.method == 'POST':
        # Validate required fields
        required_fields = ['name', 'email', 'password', 'role']
        for field in required_fields:
            if not request.form.get(field):
                flash(f'{field.capitalize()} is required.', 'error')
                return render_template('admin/user_form.html', user=None)

        # Check if email already exists
        if db.users.find_one({'email': request.form.get('email')}):
            flash('Email already exists.', 'error')
            return render_template('admin/user_form.html', user=None)

        # Create user document
        user_doc = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'password': generate_password_hash(request.form.get('password')),
            'role': request.form.get('role'),
            'phone': request.form.get('phone', ''),
            'address': request.form.get('address', ''),
            'created_at': datetime.datetime.utcnow()
        }

        db.users.insert_one(user_doc)
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/user_form.html', user=None)


@admin_bp.route('/users/<id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(id):
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(id)})

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.list_users'))

    if request.method == 'POST':
        # Validate required fields
        if not request.form.get('name') or not request.form.get('email') or not request.form.get('role'):
            flash('Name, email, and role are required.', 'error')
            return render_template('admin/user_form.html', user=user)

        # Check if email already exists (excluding current user)
        existing_user = db.users.find_one({
            'email': request.form.get('email'),
            '_id': {'$ne': ObjectId(id)}
        })
        if existing_user:
            flash('Email already exists.', 'error')
            return render_template('admin/user_form.html', user=user)

        update_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'role': request.form.get('role'),
            'phone': request.form.get('phone', ''),
            'address': request.form.get('address', '')
        }

        # Update password only if provided
        if request.form.get('password'):
            update_data['password'] = generate_password_hash(request.form.get('password'))

        db.users.update_one(
            {'_id': ObjectId(id)},
            {'$set': update_data}
        )

        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/user_form.html', user=user)


@admin_bp.route('/users/<id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(id):
    db = get_db()

    # Prevent admin from deleting their own account
    current_user_id = session.get('user_id')
    if str(current_user_id) == id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.list_users'))

    result = db.users.delete_one({'_id': ObjectId(id)})

    if result.deleted_count:
        flash('User deleted successfully.', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('admin.list_users'))


# COURSE MANAGEMENT ROUTES

@admin_bp.route('/courses')
@login_required
@role_required('admin')
def list_courses():
    db = get_db()
    page = int(request.args.get('page', 1))
    per_page = 10

    total_count = db.courses.count_documents({})
    total_pages = (total_count + per_page - 1) // per_page

    courses = list(
        db.courses.find({})
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    # Get college names for each course
    for course in courses:
        college = db.colleges.find_one({'_id': course.get('college_id')})
        course['college_name'] = college.get('college_name', 'N/A') if college else 'N/A'

    return render_template(
        'admin/courses_list.html',
        courses=courses,
        page=page,
        total_pages=total_pages
    )


@admin_bp.route('/profile')
@login_required
@role_required('admin')
def admin_profile():
    db = get_db()
    admin_id = session.get('user_id')

    if not admin_id:
        flash('Please log in again.', 'error')
        return redirect(url_for('auth.login'))

    admin = db.users.find_one({'_id': ObjectId(admin_id), 'role': 'admin'})

    if not admin:
        flash('Admin profile not found.', 'error')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/profile.html', admin=admin)


@admin_bp.route('/profile/update', methods=['POST'])
@login_required
@role_required('admin')
def update_profile():
    db = get_db()
    admin_id = session.get('user_id')

    if not admin_id:
        flash('Please log in again.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        update_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone', ''),
            'address': request.form.get('address', '')
        }

        # Check if email already exists (excluding current admin)
        existing_user = db.users.find_one({
            'email': request.form.get('email'),
            '_id': {'$ne': ObjectId(admin_id)}
        })
        if existing_user:
            flash('Email already exists.', 'error')
            return redirect(url_for('admin.admin_profile'))

        # Update password only if provided
        if request.form.get('password'):
            update_data['password'] = generate_password_hash(request.form.get('password'))

        db.users.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': update_data}
        )

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('admin.admin_profile'))