#!/usr/bin/env python3
"""
Script to create class login accounts for Hamilton TMS
Creates accounts for Class 1-20, Oak 1-3, and Ext 1-2
"""

import os
import sys
import uuid
sys.path.append('.')
from app import app, db
from models import User, StaffAccount, StaffClassAssignment
from werkzeug.security import generate_password_hash

def create_class_accounts():
    """Create class login accounts"""
    
    with app.app_context():
        # Get password from environment variable for security
        password = os.environ.get("CLASS_ACCOUNTS_PASSWORD")
        if not password:
            print("Error: CLASS_ACCOUNTS_PASSWORD environment variable not set")
            print("Please set the CLASS_ACCOUNTS_PASSWORD secret in Replit")
            sys.exit(1)
        
        password_hash = generate_password_hash(password)
        
        # List of all class accounts to create
        class_accounts = []
        
        # Class 1-20
        for i in range(1, 21):
            class_accounts.append(f"Class {i}")
        
        # Oak 1-3
        for i in range(1, 4):
            class_accounts.append(f"Oak {i}")
        
        # Ext 1-2
        for i in range(1, 3):
            class_accounts.append(f"Ext {i}")
        
        created_count = 0
        updated_count = 0
        
        for class_name in class_accounts:
            # Check if user already exists
            existing_user = User.query.filter_by(username=class_name).first()
            
            if existing_user:
                # Update password if user exists
                existing_user.password_hash = password_hash
                
                # Check if staff account exists
                staff_account = StaffAccount.query.filter_by(user_id=existing_user.id).first()
                if not staff_account:
                    # Create staff account if it doesn't exist
                    staff_id = str(uuid.uuid4())
                    staff_account = StaffAccount(
                        user_id=existing_user.id,
                        staff_id=staff_id,
                        account_type='class'
                    )
                    db.session.add(staff_account)
                
                # Update class assignment
                # Extract numeric class for assignment (e.g., "Class 1" -> "1")
                if class_name.startswith("Class "):
                    assigned_class = class_name.replace("Class ", "")
                elif class_name.startswith("Oak "):
                    assigned_class = class_name.replace("Oak ", "Oak ")
                elif class_name.startswith("Ext "):
                    assigned_class = class_name.replace("Ext ", "Ext ")
                else:
                    assigned_class = class_name
                
                # Remove existing assignments and add new one
                StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).delete()
                assignment = StaffClassAssignment(
                    staff_account_id=staff_account.id,
                    class_name=assigned_class
                )
                db.session.add(assignment)
                
                updated_count += 1
                print(f"Updated: {class_name} -> assigned to class {assigned_class}")
            else:
                # Create new user
                user = User(
                    username=class_name,
                    password_hash=password_hash
                )
                db.session.add(user)
                db.session.flush()  # Get the user ID
                
                # Create staff account with unique staff_id
                staff_id = str(uuid.uuid4())
                staff_account = StaffAccount(
                    user_id=user.id,
                    staff_id=staff_id,
                    account_type='class'
                )
                db.session.add(staff_account)
                db.session.flush()  # Get the staff account ID
                
                # Create class assignment
                # Extract numeric class for assignment
                if class_name.startswith("Class "):
                    assigned_class = class_name.replace("Class ", "")
                elif class_name.startswith("Oak "):
                    assigned_class = class_name.replace("Oak ", "Oak ")
                elif class_name.startswith("Ext "):
                    assigned_class = class_name.replace("Ext ", "Ext ")
                else:
                    assigned_class = class_name
                
                assignment = StaffClassAssignment(
                    staff_account_id=staff_account.id,
                    class_name=assigned_class
                )
                db.session.add(assignment)
                
                created_count += 1
                print(f"Created: {class_name} -> assigned to class {assigned_class}")
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✓ Class accounts setup complete:")
        print(f"  - Created: {created_count} new accounts")
        print(f"  - Updated: {updated_count} existing accounts")
        print(f"  - Total accounts: {len(class_accounts)}")
        print(f"  - Password set from environment variable")
        
        # List all created accounts
        print(f"\nAccounts created/updated:")
        for class_name in class_accounts:
            print(f"  - Username: {class_name}")

if __name__ == "__main__":
    create_class_accounts()