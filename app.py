from flask import Flask, request, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

# Configure logging - use INFO level for production
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
import os
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# Database configuration
import os
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# No need to call db.init_app(app) here, it's already done in the constructor.
db = SQLAlchemy(app, model_class=Base)

# Add cache-busting headers for all HTML responses
@app.after_request
def add_cache_headers(response):
    if request.endpoint and response.content_type.startswith('text/html'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Flask-Login setup
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta

# Configure session duration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.session_protection = 'strong'

# CSRF Protection
csrf = CSRFProtect(app)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Create tables and default admin user
# Need to put this in module-level to make it work with Gunicorn.
with app.app_context():
    import models  # noqa: F401
    
    # Create tables if they don't exist
    db.create_all()
    
    # Create default admin user only if no admin exists
    admin_user = models.User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create admin user for both development and deployment
        admin_user = models.User(username='admin')
        admin_user.set_password('password123')
        db.session.add(admin_user)
        db.session.flush()  # Get the ID
        
        # Create admin staff account
        import uuid
        admin_staff = models.StaffAccount(
            user_id=admin_user.id,
            staff_id=str(uuid.uuid4()),
            account_type='admin',
            is_active=True
        )
        db.session.add(admin_staff)
        db.session.commit()
        logging.info("Default admin user and staff account created: admin/password123")
    else:
        # Ensure existing admin has staff account
        admin_staff = models.StaffAccount.query.filter_by(user_id=admin_user.id).first()
        if not admin_staff:
            import uuid
            admin_staff = models.StaffAccount(
                user_id=admin_user.id,
                staff_id=str(uuid.uuid4()),
                account_type='admin',
                is_active=True
            )
            db.session.add(admin_staff)
            db.session.commit()
            logging.info("Admin staff account created for existing admin user")
    
    logging.info("Database tables created")
    
    # Run auto-migration to ensure correct data structure
    try:
        from auto_migrate import auto_migrate
        auto_migrate()
        
        # Force database storage mode
        import database_store
        database_store.USE_DATABASE = True
        logging.info("Forced database storage mode")
    except Exception as e:
        logging.warning(f"Auto-migration failed: {e}")
        # Still force database mode
        try:
            import database_store
            database_store.USE_DATABASE = True
        except:
            pass

# Template context processor to provide is_admin to all templates
@app.context_processor
def inject_admin_status():
    from flask_login import current_user
    is_admin = False
    
    if current_user.is_authenticated:
        try:
            from models import StaffAccount
            staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
            
            if staff_account and staff_account.account_type == 'admin':
                is_admin = True
            elif hasattr(current_user, 'username') and current_user.username == 'admin':
                is_admin = True
        except Exception as e:
            # Fallback check for special users
            if hasattr(current_user, 'username') and current_user.username == 'admin':
                is_admin = True
    
    return dict(is_admin=is_admin)
