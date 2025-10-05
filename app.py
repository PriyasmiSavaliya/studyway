from flask import Flask, render_template, session, redirect, url_for
from services.db import get_db, close_db, SECRET_KEY
import os


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Set secret key
    app.config['SECRET_KEY'] = SECRET_KEY

    # Upload folder config
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'image')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Optional limit 2MB

    # Blueprints
    from blueprints.auth.routes import auth_bp
    from blueprints.user.routes import user_bp
    from blueprints.admin.routes import admin_bp
    from blueprints.college.routes import college_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(college_bp, url_prefix='/college')

    # Main Pages
    @app.route('/')
    def home():
        db = get_db()
        colleges = list(db.colleges.find().limit(6))
        for college in colleges:
            college['_id'] = str(college['_id'])
        return render_template('home.html', colleges=colleges)

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    @app.route('/dashboard')
    def dashboard_redirect():
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        if role == 'college':
            return redirect(url_for('college.dashboard'))
        if role == 'user':
            return redirect(url_for('college.list_colleges'))
        return redirect(url_for('auth.login'))

    # Teardown DB
    @app.teardown_appcontext
    def teardown_db(exception):
        close_db()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
