import os
from math import ceil

from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from blueprints.college.routes import allowed_file
from services.db import get_db
from utils.auth import login_required, role_required

admin_bp = Blueprint('admin', __name__, template_folder='templates')

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    db = get_db()
    stats = {
        'user_count': db.users.count_documents({}),
        'college_count': db.colleges.count_documents({})
    }
    return render_template('admin/dashboard.html', stats=stats)

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
UPLOAD_FOLDER = 'static/image'   # path inside your project
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

@admin_bp.route('/users')
@login_required
@role_required('admin')
def user_list():
    db = get_db()
    users = list(db.users.find({}))
    return render_template('admin/users_list.html', users=users)