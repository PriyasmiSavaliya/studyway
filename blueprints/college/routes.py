import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from services.db import get_db
from utils.auth import login_required, role_required

college_bp = Blueprint('college', __name__, template_folder='templates')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@college_bp.route('/dashboard')
@login_required
@role_required('college')
def dashboard():
    db = get_db()
    college_doc = db.colleges.find_one({'name': session.get('name')}) or {}
    return render_template('college/dashboard.html', college=college_doc)

@college_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('college')
def profile():
    db = get_db()
    name = session.get('name')
    college_doc = db.colleges.find_one({'college_name': name}) or {'college_name': name}

    if request.method == 'POST':
        # Get courses from form
        courses_list = [c.strip() for c in (request.form.get('courses') or '').split(',') if c.strip()]

        # Insert each course into `courses` collection if not already exists
        for course_name in courses_list:
            if not db.courses.find_one({'course_name': course_name}):
                db.courses.insert_one({'course_name': course_name})

        # Prepare update dictionary
        update = {
            'college_name': request.form.get('college_name'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'college_website': request.form.get('college_website'),
            'ranking': request.form.get('ranking', type=int),
            'avg_fee': request.form.get('avg_fee', type=float),
            'exam': request.form.get('exam'),
            'cutoff': request.form.get('cutoff'),
            'placement_rating': request.form.get('placement_rating', type=float),
            'description': request.form.get('description'),
            'facilities': [f.strip() for f in (request.form.get('facilities') or '').split(',') if f.strip()],
            'courses': courses_list  # store selected courses in college document
        }

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_path = os.path.join(current_app.root_path, 'static', 'image', filename)
                file.save(upload_path)
                update['image'] = filename

        # Update or insert college document
        if college_doc.get('_id'):
            db.colleges.update_one({'college_name': name}, {'$set': update})
        else:
            db.colleges.insert_one(update)

        flash('College profile saved successfully.', 'success')
        return redirect(url_for('college.dashboard'))

    return render_template('college/profile.html', item=college_doc)


@college_bp.route('/colleges')
def list_colleges():
    db = get_db()

    # Filters
    search_query = request.args.get('search', '').strip()
    city = request.args.get('city', '').strip()
    state = request.args.get('state', '').strip()
    rating = request.args.get('rating', type=float)
    fee_range = request.args.get('fee', '').strip()
    exam = request.args.get('exam', '').strip()

    query = {}

    # Search
    if search_query:
        query['$or'] = [
            {'college_name': {'$regex': search_query, '$options': 'i'}},
            {'courses': {'$regex': search_query, '$options': 'i'}},
            {'name': {'$regex': search_query, '$options': 'i'}}
        ]

    # Filters
    if city:
        query['city'] = {'$regex': city, '$options': 'i'}
    if state:
        query['state'] = {'$regex': state, '$options': 'i'}
    if exam:
        query['exam'] = {'$regex': exam, '$options': 'i'}

    if rating:
        query['placement_rating'] = {'$gte': rating}
    if fee_range:
        try:
            min_fee, max_fee = map(int, fee_range.split('-'))
            query['avg_fee'] = {'$gte': min_fee, '$lte': max_fee}
        except ValueError:
            pass

    # --- Pagination ---
    page = int(request.args.get("page", 1))  # current page
    per_page = 9
    skip = (page - 1) * per_page

    total_colleges = db.colleges.count_documents(query)
    total_pages = (total_colleges + per_page - 1) // per_page

    colleges = list(
        db.colleges.find(query).skip(skip).limit(per_page)
    )

    # Fetch unique states, cities, exams, ratings
    cities = db.colleges.distinct("city")
    states = db.colleges.distinct("state")
    exams = db.colleges.distinct("exam")
    ratings = db.colleges.distinct("placement_rating")

    # remove page from args to avoid duplicate errors
    request_args = request.args.to_dict(flat=True)
    request_args.pop("page", None)

    return render_template(
        'college/college_list.html',
        colleges=colleges,
        states=states,
        cities=cities,
        exams=exams,
        ratings=ratings,
        page=page,
        total_pages=total_pages,
        request_args=request_args
    )
