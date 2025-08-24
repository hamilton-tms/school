#!/usr/bin/env python3
"""
Script to create admin accounts for Hamilton TMS
Run with: python create_admin.py
"""
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, StaffAccount
import uuid

def create_admin_user(username, password):
    """Create or update an admin user with proper password hashing"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            print(f"User with username {username} already exists. Updating...")
            existing_user.password_hash = generate_password_hash(password)
            existing_user.active = True
            user = existing_user
        else:
            print(f"Creating new user: {username}")
            user = User(
                username=username,
                active=True
            )
            user.set_password(password)
            db.session.add(user)
        
        db.session.flush()  # Get the user ID
        
        # Check if staff account exists
        staff_account = StaffAccount.query.filter_by(user_id=user.id).first()
        
        if staff_account:
            print(f"Staff account exists. Updating to admin...")
            staff_account.account_type = 'admin'
        else:
            print(f"Creating new admin staff account...")
            staff_account = StaffAccount(
                user_id=user.id,
                staff_id=str(uuid.uuid4()),
                account_type='admin'
            )
            db.session.add(staff_account)
        
        db.session.commit()
        
        print(f"✓ Admin user '{username}' created/updated successfully!")
        print(f"  Account Type: admin")
        print(f"  User ID: {user.id}")
        print(f"  Staff ID: {staff_account.staff_id}")
        
        return user, staff_account

if __name__ == "__main__":
    # Create Gabriella's admin account
    create_admin_user(
        username="Gabriella",
        password="Gabika1984!"
    )
    
    print("\nAdmin account setup complete!")
    print("You can now log in with:")
    print("Username: Gabriella")
    print("Password: Gabika1984!")