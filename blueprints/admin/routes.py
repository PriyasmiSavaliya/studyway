from flask import Blueprint, render_template, request, redirect, url_for, flash
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
    items = list(db.colleges.find({}))
    return render_template('admin/colleges_list.html', items=items)

@admin_bp.route('/colleges/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_college():
    db = get_db()
    if request.method == 'POST':
        doc = {
            'name': request.form.get('name'),
            'location': request.form.get('location'),
            'ranking': request.form.get('ranking', type=int),
            'avg_fee': request.form.get('avg_fee', type=float),
            'facilities': [f.strip() for f in (request.form.get('facilities') or '').split(',') if f.strip()],
            'courses': [c.strip() for c in (request.form.get('courses') or '').split(',') if c.strip()],
        }
        db.colleges.insert_one(doc)
        flash('College added.', 'success')
        return redirect(url_for('admin.list_colleges'))
    return render_template('admin/college_form.html', item=None)

@admin_bp.route('/colleges/<string:name>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_college(name):
    db = get_db()
    item = db.colleges.find_one({'name': name})
    if not item:
        flash('College not found.', 'warning')
        return redirect(url_for('admin.list_colleges'))
    if request.method == 'POST':
        update = {
            'location': request.form.get('location'),
            'ranking': request.form.get('ranking', type=int),
            'avg_fee': request.form.get('avg_fee', type=float),
            'facilities': [f.strip() for f in (request.form.get('facilities') or '').split(',') if f.strip()],
            'courses': [c.strip() for c in (request.form.get('courses') or '').split(',') if c.strip()],
        }
        db.colleges.update_one({'name': name}, {'$set': update})
        flash('College updated.', 'success')
        return redirect(url_for('admin.list_colleges'))
    return render_template('admin/college_form.html', item=item)

@admin_bp.route('/colleges/<string:name>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_college(name):
    db = get_db()
    db.colleges.delete_one({'name': name})
    flash('College deleted.', 'info')
    return redirect(url_for('admin.list_colleges'))
