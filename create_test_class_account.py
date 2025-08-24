#!/usr/bin/env python3
"""
Script to create a test class account for testing auto-selection and audio features
"""

from app import app, db
from models import User, StaffAccount, StaffClassAssignment
from werkzeug.security import generate_password_hash

def create_test_class_account():
    with app.app_context():
        # Create a new user for testing class account functionality
        test_username = "TestClass14"
        test_password = "test123"
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=test_username).first()
        if existing_user:
            print(f"User {test_username} already exists. Updating instead...")
            user = existing_user
        else:
            # Create new user
            user = User(username=test_username)
            user.set_password(test_password)
            db.session.add(user)
            db.session.flush()  # Get the user ID
            print(f"Created new user: {test_username}")

        # Check if staff account exists
        existing_staff = StaffAccount.query.filter_by(user_id=user.id).first()
        if existing_staff:
            print(f"Staff account already exists for {test_username}. Updating...")
            staff_account = existing_staff
            staff_account.account_type = 'class'
            staff_account.first_name = 'Test'
            staff_account.last_name = 'Class14'
        else:
            # Create staff account
            staff_account = StaffAccount()
            staff_account.user_id = user.id
            staff_account.staff_id = f"STAFF{user.id:03d}"  # Generate a staff ID
            staff_account.account_type = 'class'
            db.session.add(staff_account)
            db.session.flush()  # Get the staff account ID
            print(f"Created staff account for {test_username}")

        # Clear existing class assignments
        StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).delete()
        
        # Assign to class 14 only
        class_assignment = StaffClassAssignment()
        class_assignment.staff_account_id = staff_account.id
        class_assignment.class_name = '14'
        db.session.add(class_assignment)
        
        db.session.commit()
        print(f"✓ Test class account created: {test_username}/test123")
        print(f"✓ Account type: class")
        print(f"✓ Assigned to class: 14 only")
        print(f"✓ Should auto-select class 14 on login")

if __name__ == '__main__':
    create_test_class_account()