"""
Database-backed data store for the school transportation management system.
This module provides CRUD operations using PostgreSQL for persistent storage.
"""

from app import db
from models import School, Route, Student, Provider, Area, Staff
from datetime import datetime
import uuid
import logging
import io
import csv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database operations for schools
def get_all_schools():
    """Get all schools as dictionary"""
    schools = School.query.all()
    return {school.id: {
        'id': school.id,
        'name': school.name,
        'address': school.address or '',
        'phone': school.phone or '',
        'email': school.email or ''
    } for school in schools}

def create_school(name, address='', phone='', email=''):
    """Create a new school"""
    school_id = str(uuid.uuid4())
    school = School(
        id=school_id,
        name=name,
        address=address,
        phone=phone,
        email=email
    )
    db.session.add(school)
    db.session.commit()
    logger.info(f"Created school: {name} ({school_id})")
    return school_id

def update_school(school_id, **updates):
    """Update school information"""
    school = School.query.get(school_id)
    if school:
        for key, value in updates.items():
            if hasattr(school, key):
                setattr(school, key, value)
        school.updated_at = datetime.now()
        db.session.commit()
        logger.info(f"Updated school {school_id}")
        return True
    return False

def delete_school(school_id):
    """Delete a school"""
    school = School.query.get(school_id)
    if school:
        db.session.delete(school)
        db.session.commit()
        logger.info(f"Deleted school {school_id}")
        return True
    return False

# Database operations for routes
def get_all_routes():
    """Get all routes as dictionary"""
    routes = Route.query.all()
    return {route.id: {
        'id': route.id,
        'route_number': route.route_number,
        'status': route.status,
        'area_id': route.area_id,
        'provider_id': route.provider_id,
        'max_capacity': route.max_capacity,
        'hidden_from_admin': getattr(route, 'hidden_from_admin', False)
    } for route in routes}

def get_route(route_id):
    """Get a single route"""
    routes = get_all_routes()
    return routes.get(route_id)

def create_route(route_number, area_id=None, provider_id=None, max_capacity=50, hidden_from_admin=False):
    """Create a new route"""
    route_id = str(uuid.uuid4())
    route = Route(
        id=route_id,
        route_number=route_number,
        status='not_present',
        area_id=area_id,
        provider_id=provider_id,
        max_capacity=max_capacity,
        hidden_from_admin=hidden_from_admin
    )
    db.session.add(route)
    db.session.commit()
    logger.info(f"Created route: {route_number} ({route_id})")
    return route_id

def update_route(route_id, **updates):
    """Update route information"""
    route = Route.query.get(route_id)
    if route:
        for key, value in updates.items():
            if hasattr(route, key):
                setattr(route, key, value)
        route.updated_at = datetime.now()
        db.session.commit()
        logger.info(f"Updated route {route_id}: {updates}")
        return True
    return False

def update_route_status(route_id, status):
    """Update route status specifically"""
    return update_route(route_id, status=status)

def delete_route(route_id):
    """Delete a route"""
    route = Route.query.get(route_id)
    if route:
        db.session.delete(route)
        db.session.commit()
        logger.info(f"Deleted route {route_id}")
        return True
    return False

# Database operations for students
def get_all_students():
    """Get all students as dictionary"""
    students = Student.query.all()
    return {student.id: {
        'id': student.id,
        'name': student.name,
        'class': student.class_name,
        'class_name': student.class_name,  # Include both for compatibility
        'route_id': student.route_id,
        'school_id': student.school_id,
        'parent1_name': student.parent1_name or '',
        'parent1_phone': student.parent1_phone or '',
        'parent2_name': student.parent2_name or '',
        'parent2_phone': student.parent2_phone or '',
        'address': student.address or '',
        'medical_needs': student.medical_needs or '',
        'has_medical_needs': student.medical_needs or '',  # Template compatibility
        'harness_required': student.harness_required or '',
        'harness': student.harness_required or '',  # Add legacy field name for template compatibility
        'badge_required': student.badge_required or '',
        'requires_pediatric_first_aid': student.badge_required or '',  # Template compatibility
        'medical_notes': '',  # Medical notes not implemented in database yet
        'safeguarding_notes': student.safeguarding_notes or ''
    } for student in students}

def get_student(student_id):
    """Get a single student"""
    students = get_all_students()
    return students.get(student_id)

def create_student(name, class_name='', **kwargs):
    """Create a new student"""
    student_id = str(uuid.uuid4())
    student = Student(
        id=student_id,
        name=name,
        class_name=class_name,
        route_id=kwargs.get('route_id'),
        school_id=kwargs.get('school_id'),
        parent1_name=kwargs.get('parent1_name', ''),
        parent1_phone=kwargs.get('parent1_phone', ''),
        parent2_name=kwargs.get('parent2_name', ''),
        parent2_phone=kwargs.get('parent2_phone', ''),
        address=kwargs.get('address', ''),
        medical_needs=kwargs.get('medical_needs', ''),
        harness_required=kwargs.get('harness_required', ''),
        badge_required=kwargs.get('badge_required', ''),
        safeguarding_notes=kwargs.get('safeguarding_notes', '')
    )
    db.session.add(student)
    db.session.commit()
    logger.info(f"Created student: {name} ({student_id})")
    return student_id

def update_student(student_id, **updates):
    """Update student information"""
    student = Student.query.get(student_id)
    if student:
        # Handle field name mappings between routes.py and models.py
        field_mappings = {
            'class': 'class_name',
            'has_medical_needs': 'medical_needs',
            'requires_pediatric_first_aid': 'badge_required'
        }
        
        # Apply field mappings
        for old_key, new_key in field_mappings.items():
            if old_key in updates:
                updates[new_key] = updates.pop(old_key)
            
        for key, value in updates.items():
            if hasattr(student, key):
                setattr(student, key, value)
        student.updated_at = datetime.now()
        db.session.commit()
        logger.info(f"Updated student {student_id}")
        return True
    return False

def delete_student(student_id):
    """Delete a student"""
    student = Student.query.get(student_id)
    if student:
        db.session.delete(student)
        db.session.commit()
        logger.info(f"Deleted student {student_id}")
        return True
    return False

# Database operations for providers
def get_all_providers():
    """Get all providers as dictionary ordered by name"""
    providers = Provider.query.order_by(Provider.name).all()
    return {provider.id: {
        'id': provider.id,
        'name': provider.name,
        'contact_name': provider.contact_name or '',
        'phone': provider.phone or '',
        'email': provider.email or ''
    } for provider in providers}

def get_provider(provider_id):
    """Get a single provider"""
    providers = get_all_providers()
    return providers.get(provider_id)

def create_provider(name, contact_name='', phone='', email=''):
    """Create a new provider"""
    provider_id = str(uuid.uuid4())
    provider = Provider(
        id=provider_id,
        name=name,
        contact_name=contact_name,
        phone=phone,
        email=email
    )
    db.session.add(provider)
    db.session.commit()
    logger.info(f"Created provider: {name} ({provider_id}) with phone: {phone}, email: {email}")
    
    # Return the full provider data instead of just ID
    return {
        'id': provider_id,
        'name': name,
        'contact_name': contact_name,
        'phone': phone,
        'email': email
    }

def update_provider(provider_id, name=None, contact_name=None, phone=None, email=None):
    """Update provider information"""
    provider = Provider.query.get(provider_id)
    if provider:
        if name is not None:
            provider.name = name
        if contact_name is not None:
            provider.contact_name = contact_name
        if phone is not None:
            provider.phone = phone
        if email is not None:
            provider.email = email
        db.session.commit()
        logger.info(f"Updated provider {provider_id}")
        return get_provider(provider_id)
    return None

def delete_provider(provider_id):
    """Delete a provider"""
    provider = Provider.query.get(provider_id)
    if provider:
        db.session.delete(provider)
        db.session.commit()
        logger.info(f"Deleted provider {provider_id}")
        return True
    return False

# Database operations for areas
def get_all_areas():
    """Get all areas as dictionary"""
    areas = Area.query.all()
    return {area.id: {
        'id': area.id,
        'name': area.name,
        'description': area.description or ''
    } for area in areas}

def get_area(area_id):
    """Get a single area"""
    areas = get_all_areas()
    return areas.get(area_id)

def get_routes_by_area(area_id):
    """Get all routes for a specific area"""
    routes_data = get_all_routes()
    return {route_id: route_data for route_id, route_data in routes_data.items() 
            if route_data.get('area_id') == area_id}

def create_area(name, school_id=None, description=''):
    """Create a new area"""
    area_id = str(uuid.uuid4())
    area = Area(
        id=area_id,
        name=name,
        description=description
    )
    db.session.add(area)
    db.session.commit()
    logger.info(f"Created area: {name} ({area_id})")
    return area_id

def update_area(area_id, **updates):
    """Update area information"""
    area = Area.query.get(area_id)
    if area:
        for key, value in updates.items():
            if hasattr(area, key):
                setattr(area, key, value)
        area.updated_at = datetime.now()
        db.session.commit()
        logger.info(f"Updated area {area_id}")
        return True
    return False

def delete_area(area_id):
    """Delete an area"""
    area = Area.query.get(area_id)
    if area:
        db.session.delete(area)
        db.session.commit()
        logger.info(f"Deleted area {area_id}")
        return True
    return False

# Database operations for staff
def get_all_staff():
    """Get all staff as dictionary"""
    staff_list = Staff.query.all()
    return {staff.id: {
        'id': staff.id,
        'username': staff.username,
        'display_name': staff.display_name or staff.username,
        'account_type': staff.account_type,
        'is_active': staff.is_active
    } for staff in staff_list}

def create_staff(username, account_type='class', display_name=None):
    """Create a new staff member"""
    staff_id = str(uuid.uuid4())
    staff = Staff(
        id=staff_id,
        username=username,
        display_name=display_name or username,
        account_type=account_type,
        is_active=True
    )
    db.session.add(staff)
    db.session.commit()
    logger.info(f"Created staff: {username} ({staff_id})")
    return staff_id

def update_staff(staff_id, **updates):
    """Update staff information"""
    staff = Staff.query.get(staff_id)
    if staff:
        for key, value in updates.items():
            if hasattr(staff, key):
                setattr(staff, key, value)
        staff.updated_at = datetime.now()
        db.session.commit()
        logger.info(f"Updated staff {staff_id}")
        return True
    return False

def get_staff_account(username):
    """Get staff account by username"""
    staff_list = Staff.query.filter_by(username=username).first()
    if staff_list:
        return {
            'id': staff_list.id,
            'username': staff_list.username,
            'display_name': staff_list.display_name or staff_list.username,
            'account_type': staff_list.account_type,
            'is_active': staff_list.is_active,
            'assigned_classes': []  # Simplified for now - could be expanded
        }
    return None

def process_students_csv(csv_content):
    """Process a CSV file with students data"""
    results = {
        'success': [],
        'errors': []
    }
    
    try:
        # Parse CSV content
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Check if required columns exist
        required_columns = ['Name', 'Class', 'Parent/Carer Name', 'Parent/Carer Phone', 'Address']
        
        # Check for Class column (now required)
        if 'Class' not in csv_reader.fieldnames:
            results['errors'].append('Missing required columns. Expected: Name, Class, Parent/Carer Name, Parent/Carer Phone, Address')
            return results
        
        # Validate all required columns exist (support both old and new formats)
        missing_columns = []
        for col in required_columns:
            if col not in csv_reader.fieldnames:
                # Check for backward compatibility
                if col == 'Parent/Carer Name' and 'Parent Name' in csv_reader.fieldnames:
                    continue
                elif col == 'Parent/Carer Phone' and 'Parent Phone' in csv_reader.fieldnames:
                    continue
                else:
                    missing_columns.append(col)
        
        if missing_columns:
            results['errors'].append(f'Missing required columns: {", ".join(missing_columns)}. Expected: Name, Class, Parent/Carer Name, Parent/Carer Phone, Address')
            return results
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because header is row 1
            try:
                # Extract required fields
                name = row['Name'].strip()
                class_name = row['Class'].strip()
                
                # Clean class name: Remove "Class " prefix if present to prevent duplicates
                if class_name.lower().startswith('class '):
                    class_name = class_name[6:].strip()  # Remove "Class " (6 characters)
                
                # Support both old and new column names for backward compatibility
                parent_name = row.get('Parent/Carer Name', row.get('Parent Name', '')).strip()
                parent_phone = row.get('Parent/Carer Phone', row.get('Parent Phone', '')).strip()
                
                # Extract optional Parent 2 contact details
                parent2_name = row.get('Parent/Carer 2 Name', '').strip()
                parent2_phone = row.get('Parent/Carer 2 Phone', '').strip()
                
                address = row['Address'].strip()
                
                # Optional fields
                medical_needs = row.get('Has Medical Needs', 'No').strip()
                harness_required = row.get('Harness', 'No').strip()
                pediatric_first_aid = row.get('Requires Pediatric First Aid', 'No').strip()
                medical_notes = row.get('Medical Notes', '').strip()
                safeguarding_notes = row.get('Safeguarding Notes', '').strip()
                
                # Validate required fields
                if not all([name, class_name, parent_name, parent_phone, address]):
                    results['errors'].append(f'Row {row_num}: Missing required fields (Name, Class, Parent/Carer Name, Parent/Carer Phone, Address)')
                    continue
                
                # Create student using create_student function
                student_id = create_student(
                    name=name,
                    class_name=class_name,
                    parent1_name=parent_name,
                    parent1_phone=parent_phone,
                    parent2_name=parent2_name if parent2_name else None,
                    parent2_phone=parent2_phone if parent2_phone else None,
                    address=address,
                    medical_needs=medical_needs,
                    harness_required=harness_required,
                    pediatric_first_aid=pediatric_first_aid,
                    medical_notes=medical_notes,
                    safeguarding_notes=safeguarding_notes
                )
                
                results['success'].append(f'Added student: {name} (Class {class_name})')
                logger.info(f"CSV: Created student {name} in class {class_name}")
                
            except Exception as e:
                results['errors'].append(f'Row {row_num}: Error processing row - {str(e)}')
                logger.error(f"CSV row {row_num} error: {e}")
                
    except Exception as e:
        results['errors'].append(f'Error reading CSV file: {str(e)}')
        logger.error(f"CSV processing error: {e}")
    
    return results

def delete_staff(staff_id):
    """Delete a staff member"""
    staff = Staff.query.get(staff_id)
    if staff:
        db.session.delete(staff)
        db.session.commit()
        logger.info(f"Deleted staff {staff_id}")
        return True
    return False

# Route status constants
BUS_STATUS_NOT_PRESENT = 'not_present'
BUS_STATUS_ARRIVED = 'arrived'
BUS_STATUS_READY = 'ready'

# Utility functions
def get_route_status_text(status):
    """Get the text for a route status"""
    status_texts = {
        BUS_STATUS_NOT_PRESENT: 'Not Present',
        BUS_STATUS_ARRIVED: 'Arrived',
        BUS_STATUS_READY: 'Ready'
    }
    return status_texts.get(status, 'Unknown')

def get_route_status_class(status):
    """Get CSS class for route status"""
    status_classes = {
        BUS_STATUS_NOT_PRESENT: 'btn-danger',
        BUS_STATUS_ARRIVED: 'btn-warning',
        BUS_STATUS_READY: 'btn-success'
    }
    return status_classes.get(status, 'btn-secondary')

# Global flag to force database mode - CRITICAL FIX
USE_DATABASE = True

def get_route_status_color(status):
    """Get color for route status (alias for get_route_status_class)"""
    return get_route_status_class(status)

def get_students_for_route(route_id):
    """Get all students assigned to a specific route"""
    students = get_all_students()
    return {s_id: student for s_id, student in students.items() if student.get('route_id') == route_id}

def assign_student_to_route(student_id, route_id):
    """Assign a student to a route"""
    return update_student(student_id, route_id=route_id)

def unassign_student_from_route(student_id):
    """Remove student from route assignment"""
    return update_student(student_id, route_id=None)

def get_available_students():
    """Get students not assigned to any route"""
    students = get_all_students()
    return {s_id: student for s_id, student in students.items() if not student.get('route_id')}

def get_route_student_count(route_id):
    """Get count of students assigned to a route"""
    students = get_students_for_route(route_id)
    return len(students)

def is_route_empty(route_id):
    """Check if a route has no students"""
    return get_route_student_count(route_id) == 0

def get_routes_by_status(status):
    """Get all routes with specific status"""
    routes = get_all_routes()
    return {r_id: route for r_id, route in routes.items() if route.get('status') == status}

def get_unique_class_names():
    """Get list of unique class names from all students"""
    students = get_all_students()
    class_names = set()
    for student in students.values():
        if student.get('class'):
            class_names.add(student['class'])
    return sorted(list(class_names))

def get_all_staff():
    """Get all staff members from both data store and database"""
    # For now, return empty dict since we're using database staff accounts
    # This maintains compatibility with existing code
    return {}

def get_staff(staff_id):
    """Get a specific staff member"""
    # Check if it's a StaffAccount in database
    try:
        from models import StaffAccount
        staff_account = StaffAccount.query.filter_by(staff_id=staff_id).first()
        if staff_account and staff_account.user:
            return {
                'id': staff_id,
                'name': staff_account.user.username,
                'username': staff_account.user.username,
                'account_type': staff_account.account_type,
                'has_account': True,
                'is_active': staff_account.is_active
            }
    except Exception as e:
        logger.error(f"Error getting staff {staff_id}: {e}")
    
    return None

def delete_staff_account(staff_id):
    """Delete a staff member and associated user account"""
    try:
        from models import StaffAccount, User
        from app import db
        
        # Find the staff account
        staff_account = StaffAccount.query.filter_by(staff_id=staff_id).first()
        if not staff_account:
            logger.warning(f"Staff account {staff_id} not found")
            return False
            
        # Get the associated user
        user = staff_account.user
        
        # Delete staff class assignments first
        from models import StaffClassAssignment
        StaffClassAssignment.query.filter_by(staff_account_id=staff_account.id).delete()
        
        # Delete the staff account
        db.session.delete(staff_account)
        
        # Delete the user account if it exists
        if user:
            db.session.delete(user)
        
        db.session.commit()
        logger.info(f"Deleted staff account {staff_id} and associated user")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting staff {staff_id}: {e}")
        db.session.rollback()
        return False

def update_staff(staff_id, **kwargs):
    """Update a staff member"""
    try:
        from models import StaffAccount, User
        from app import db
        
        staff_account = StaffAccount.query.filter_by(staff_id=staff_id).first()
        if not staff_account:
            return False
            
        # Update staff account fields
        if 'account_type' in kwargs:
            staff_account.account_type = kwargs['account_type']
            
        # Update user fields if user exists
        if staff_account.user:
            if 'username' in kwargs:
                staff_account.user.username = kwargs['username']
            if 'password' in kwargs and kwargs['password']:
                staff_account.user.set_password(kwargs['password'])
                
        db.session.commit()
        logger.info(f"Updated staff {staff_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating staff {staff_id}: {e}")
        db.session.rollback()
        return False

def bulk_update_route_status(route_ids, status):
    """Update status for multiple routes"""
    success_count = 0
    for route_id in route_ids:
        if update_route_status(route_id, status):
            success_count += 1
    return success_count

def get_route_capacity_info(route_id):
    """Get route capacity information"""
    route = get_route(route_id)
    if not route:
        return None
    
    student_count = get_route_student_count(route_id)
    max_capacity = route.get('max_capacity', 50)
    
    return {
        'current': student_count,
        'max': max_capacity,
        'available': max_capacity - student_count,
        'is_full': student_count >= max_capacity
    }

# Initialize sample data functions - these are no-ops for database version  
def initialize_sample_data():
    """No-op - sample data should be loaded via migration"""
    logger.info("Sample data initialization skipped - use migration script instead")

def initialize_data():
    """No-op - data is managed by database"""
    logger.info("Database-backed data store initialized")

# CSV processing functions - these need to be implemented if used
def create_routes_csv_template():
    """Create a CSV template for routes"""
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['route_number', 'provider_name', 'provider_contact', 'provider_phone', 'area_name', 'students'])
    writer.writerow(['352', 'SkyLine Travel', 'Lori Shields', '001-338-055-3189x354', 'Dawdle', ''])
    writer.writerow(['59', 'Sandwell', 'Marcus Jackson', '965.669.4883x115', 'Secondary', ''])
    return output.getvalue()

def process_routes_csv(csv_content):
    """Process CSV content and create routes"""
    import csv
    import io
    
    results = {'success': [], 'errors': []}
    
    try:
        # Parse the CSV content
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Get the default school
        schools = get_all_schools()
        if not schools:
            results['errors'].append('No school found. Please create a school first.')
            return results
            
        default_school_id = list(schools.keys())[0]
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because header is row 1
            try:
                # Extract data from CSV row using new format
                route_number = row.get('route_number', '').strip()
                area_name = row.get('area_name', '').strip()
                provider_name = row.get('provider_name', '').strip()
                provider_contact = row.get('provider_contact', '').strip()
                provider_phone = row.get('provider_phone', '').strip()
                students = row.get('students', '').strip()
                
                if not route_number:
                    results['errors'].append(f'Row {row_num}: route_number is required')
                    continue
                    
                # Create or get area
                area_id = None
                if area_name:
                    # Check if area already exists
                    areas = get_all_areas()
                    existing_area = None
                    for aid, area_data in areas.items():
                        if area_data['name'].lower() == area_name.lower():
                            existing_area = aid
                            break
                    
                    if existing_area:
                        area_id = existing_area
                    else:
                        area_id = create_area(area_name, default_school_id)
                
                # Create or get provider
                provider_id = None
                if provider_name:
                    # Check if provider already exists
                    providers = get_all_providers()
                    existing_provider = None
                    for pid, provider_data in providers.items():
                        if provider_data['name'].lower() == provider_name.lower():
                            existing_provider = pid
                            break
                    
                    if existing_provider:
                        provider_id = existing_provider
                    else:
                        # Create new provider with contact details
                        provider_data = create_provider(
                            name=provider_name,
                            contact_name=provider_contact or provider_name,
                            phone=provider_phone or ''
                        )
                        provider_id = provider_data['id']
                
                # Create the route (default max_capacity to 50)
                route_id = create_route(
                    route_number=route_number,
                    area_id=area_id,
                    provider_id=provider_id,
                    max_capacity=50
                )
                
                results['success'].append(f'Created route: {route_number}')
                
            except Exception as e:
                results['errors'].append(f'Row {row_num}: Error processing route - {str(e)}')
                continue
                
    except Exception as e:
        results['errors'].append(f'Error parsing CSV: {str(e)}')
    
    return results

def create_students_csv_template():
    """Create a CSV template for students"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row - includes optional Parent 2 contact details
    writer.writerow(['Name', 'Class', 'Parent/Carer Name', 'Parent/Carer Phone', 'Parent/Carer 2 Name', 'Parent/Carer 2 Phone', 'Address', 'Has Medical Needs', 'Requires Pediatric First Aid', 'Medical Notes', 'Harness', 'Safeguarding Notes'])
    
    # Add sample data rows to show format
    writer.writerow(['Emma Johnson', '3A', 'Sarah Johnson', '01234567890', 'Michael Johnson', '07987654321', '123 High Street, London, W1A 1AA', 'Yes', 'Yes', 'Asthma, requires inhaler', 'Yes', ''])
    writer.writerow(['Oliver Smith', '5B', 'Claire Smith', '02076543210', '', '', '45 Victoria Road, Manchester, M1 2AB', 'No', 'No', '', 'No', 'Dietary requirements - vegetarian only'])
    
    return output.getvalue()

# Compatibility functions to maintain existing API
def save_data_to_file():
    """No-op for compatibility - data is automatically saved to database"""
    pass

def load_data_from_file():
    """No-op for compatibility - data is loaded from database"""
    logger.info("Using persistent database storage")