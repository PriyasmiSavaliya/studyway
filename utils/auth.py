from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            role = session.get('role')
            if role not in roles:
                flash('You are not authorized to access this page.', 'danger')
                # Redirect to correct dashboard if logged in
                if role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                if role == 'college':
                    return redirect(url_for('college.dashboard'))
                return redirect(url_for('user.dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

