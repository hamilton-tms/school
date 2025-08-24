from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        """Override UserMixin is_active property"""
        return self.active

    def __repr__(self):
        return f'<User {self.username}>'

# Staff Account Management
class StaffAccount(db.Model):
    __tablename__ = 'staff_accounts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    staff_id = db.Column(db.String, nullable=False)  # Links to data_store staff
    account_type = db.Column(db.String, nullable=False)  # 'admin' or 'class'
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = db.relationship(User, backref='staff_accounts')

# Class assignments for staff accounts
class StaffClassAssignment(db.Model):
    __tablename__ = 'staff_class_assignments'
    id = db.Column(db.Integer, primary_key=True)
    staff_account_id = db.Column(db.Integer, db.ForeignKey(StaffAccount.id), nullable=False)
    class_name = db.Column(db.String, nullable=False)  # e.g., "3A", "10B", "Reception"
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    staff_account = db.relationship(StaffAccount, backref='class_assignments')

# Persistent data models to replace file-based storage
class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.String, primary_key=True)  # UUID
    name = db.Column(db.String, nullable=False)
    address = db.Column(db.String)
    phone = db.Column(db.String)
    email = db.Column(db.String)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Route(db.Model):
    __tablename__ = 'routes'
    id = db.Column(db.String, primary_key=True)  # UUID
    route_number = db.Column(db.String, nullable=False)
    status = db.Column(db.String, default='not_present')  # not_present, arrived, ready
    area_id = db.Column(db.String, db.ForeignKey('areas.id'))
    provider_id = db.Column(db.String, db.ForeignKey('providers.id'))
    max_capacity = db.Column(db.Integer, default=50)
    hidden_from_admin = db.Column(db.Boolean, default=False)  # For individual parent routes
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    area = db.relationship('Area', backref='routes')
    provider = db.relationship('Provider', backref='routes')

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.String, primary_key=True)  # UUID
    name = db.Column(db.String, nullable=False)
    class_name = db.Column(db.String)
    route_id = db.Column(db.String, db.ForeignKey('routes.id'))
    school_id = db.Column(db.String, db.ForeignKey('schools.id'))
    
    # Contact details
    parent1_name = db.Column(db.String)
    parent1_phone = db.Column(db.String)
    parent2_name = db.Column(db.String)
    parent2_phone = db.Column(db.String)
    address = db.Column(db.Text)
    
    # Safety requirements
    medical_needs = db.Column(db.String)
    harness_required = db.Column(db.String)
    badge_required = db.Column(db.String)
    safeguarding_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    route = db.relationship('Route', backref='students')
    school = db.relationship('School', backref='students')

class Provider(db.Model):
    __tablename__ = 'providers'
    id = db.Column(db.String, primary_key=True)  # UUID
    name = db.Column(db.String, nullable=False)
    contact_name = db.Column(db.String)
    phone = db.Column(db.String)
    email = db.Column(db.String)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Area(db.Model):
    __tablename__ = 'areas'
    id = db.Column(db.String, primary_key=True)  # UUID
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Staff(db.Model):
    __tablename__ = 'staff_data'
    id = db.Column(db.String, primary_key=True)  # UUID
    username = db.Column(db.String, nullable=False)
    display_name = db.Column(db.String)
    account_type = db.Column(db.String, nullable=False)  # admin or class
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
