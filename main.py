#----------------------------------File Header-------------------------------------------
# main.py
# Purpose: Flask application factory setup, configuration, and blueprint registration

#----------------------------------Imports-------------------------------------------
import os
from datetime import timedelta
from flask import Flask, render_template
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
from extensions import db, jwt, mail
from auth_routes import auth_bp
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User

#----------------------------------Loading Environment Variables-------------------------------------------
load_dotenv() 

#----------------------------------Flask App Factory-------------------------------------------
def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

# ----------------------------------App Configuration-------------------------------------------
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
        minutes=int(os.getenv('ACCESS_TOKEN_EXPIRES_MINUTES', 180))
    )
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(
        days=int(os.getenv('REFRESH_TOKEN_EXPIRES_DAYS', 7))
    )

# ----------------------------------Initializing Extensions-------------------------------------------
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate = Migrate(app, db)

#----------------------------------CORS Configuration-------------------------------------------
    CORS(
        app,
        supports_credentials=True,
        origins=[os.getenv('FRONTEND_URL', 'http://localhost:3000')]
    )

#----------------------------------Registering Blueprints-------------------------------------------
    app.register_blueprint(auth_bp)

#----------------------------------Adding Security Headers-------------------------------------------
    @app.after_request
    def add_security_headers(resp):
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['X-Frame-Options'] = 'DENY'
        resp.headers['X-XSS-Protection'] = '1; mode=block'
        return resp

#----------------------------------Frontend Routes-------------------------------------------
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/admin_dashboard')
    def admin_dashboard():
        return render_template('admin_dashboard.html')

    return app

#----------------------------------Main Entry Point-------------------------------------------
if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", port=5000, debug=True)
