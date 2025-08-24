"""
In-memory data store for the school transportation management system.
This module provides fake data and CRUD operations for schools, routes, staff, and students.
"""
import uuid
import csv
import io
import secrets
import string
import json
import os
from datetime import datetime
import profanity_filter

# Global data store - in production this would be replaced with a database
schools = {}
routes = {}  # Previously called 'buses'
staff = {}
students = {}
providers = {}  # Transport providers (HATS, Green Destination, etc.)
areas = {}      # Parking areas at schools

# File-based persistence - use more permanent location in production
PERSISTENCE_FILE = os.environ.get('DATA_PERSISTENCE_FILE', '/tmp/hamilton_tms_data.json')

def save_data_to_file():
    """Save current data to a temporary file"""
    try:
        # Convert datetime objects to strings for JSON serialization
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        data = {
            'schools': schools,
            'routes': routes,
            'staff': staff,
            'students': students,
            'providers': providers,
            'areas': areas
        }
        
        # Convert datetime objects recursively
        import copy
        data_copy = copy.deepcopy(data)
        for category in data_copy.values():
            for item in category.values():
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, datetime):
                            item[key] = value.isoformat()
        
        with open(PERSISTENCE_FILE, 'w') as f:
            json.dump(data_copy, f)
        print(f"Data saved to {PERSISTENCE_FILE}")
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data_from_file():
    """Load data from temporary file if it exists"""
    global schools, routes, staff, students, providers, areas
    
    try:
        if os.path.exists(PERSISTENCE_FILE):
            with open(PERSISTENCE_FILE, 'r') as f:
                data = json.load(f)
            
            schools = data.get('schools', {})
            routes = data.get('routes', {})
            # Clear corrupted staff data - start fresh
            staff = {}
            students = data.get('students', {})
            providers = data.get('providers', {})
            areas = data.get('areas', {})
            
            # Convert datetime strings back to datetime objects
            for category in [schools, routes, staff, students, providers, areas]:
                for item in category.values():
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if key in ['created_at', 'updated_at'] and isinstance(value, str):
                                try:
                                    item[key] = datetime.fromisoformat(value)
                                except:
                                    item[key] = datetime.now()
            
            print(f"Data loaded from {PERSISTENCE_FILE}: {len(schools)} schools, {len(routes)} routes")
            return True
    except Exception as e:
        print(f"Error loading data: {e}")
    
    return False

# Real-time update tracking
_students_updated = False
_routes_updated = False

def clear_students_updated_flag():
    """Clear the students updated flag"""
    global _students_updated
    _students_updated = False

def clear_routes_updated_flag():
    """Clear the routes updated flag"""
    global _routes_updated
    _routes_updated = False

# Bus status constants
BUS_STATUS_NOT_PRESENT = "not_present"  # Red
BUS_STATUS_ARRIVED = "arrived"          # Orange
BUS_STATUS_READY = "ready"              # Green

def generate_id():
    """Generate a unique identifier"""
    return str(uuid.uuid4())

# School Management Functions
def get_all_schools():
    """Get all schools"""
    return schools

def get_school(school_id):
    """Get a specific school by ID"""
    return schools.get(school_id)

def create_school(name, address, contact1_name, contact1_role, contact1_email, contact1_phone, 
                 contact2_name=None, contact2_role=None, contact2_email=None, contact2_phone=None):
    """Create a new school"""
    school_id = generate_id()
    school = {
        'id': school_id,
        'name': name,
        'address': address,
        'contact1': {
            'name': contact1_name,
            'role': contact1_role,
            'email': contact1_email,
            'phone': contact1_phone
        },
        'contact2': {
            'name': contact2_name,
            'role': contact2_role,
            'email': contact2_email,
            'phone': contact2_phone
        } if contact2_name else None,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    schools[school_id] = school
    return school

def update_school(school_id, name, address, contact1_name, contact1_role, contact1_email, contact1_phone,
                 contact2_name=None, contact2_role=None, contact2_email=None, contact2_phone=None):
    """Update an existing school"""
    if school_id in schools:
        schools[school_id].update({
            'name': name,
            'address': address,
            'contact1': {
                'name': contact1_name,
                'role': contact1_role,
                'email': contact1_email,
                'phone': contact1_phone
            },
            'contact2': {
                'name': contact2_name,
                'role': contact2_role,
                'email': contact2_email,
                'phone': contact2_phone
            } if contact2_name else None,
            'updated_at': datetime.now()
        })
        return schools[school_id]
    return None

def delete_school(school_id):
    """Delete a school"""
    if school_id in schools:
        # Delete all routes associated with this school
        routes_to_delete = [route_id for route_id, route_data in routes.items() if route_data['school_id'] == school_id]
        for route_id in routes_to_delete:
            delete_route(route_id)
        
        del schools[school_id]
        return True
    return False

# Route Management Functions
def get_all_routes():
    """Get all routes"""
    return routes

def get_route(route_id):
    """Get a specific route by ID"""
    return routes.get(route_id)

def get_school_routes(school_id):
    """Get all routes for a specific school"""
    return {route_id: route_data for route_id, route_data in routes.items() if route_data['school_id'] == school_id}

def create_route(school_id, route_number, provider_id, area_id):
    """Create a new route"""
    route_id = generate_id()
    route = {
        'id': route_id,
        'school_id': school_id,
        'route_number': route_number,
        'provider_id': provider_id,
        'area_id': area_id,
        'guide_present': True,  # Default: guide is present
        'student_ids': [],
        'status': BUS_STATUS_NOT_PRESENT,  # Default status
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    routes[route_id] = route
    return route

def update_route(route_id, updates):
    """Update an existing route with dictionary of updates"""
    if route_id in routes:
        routes[route_id].update(updates)
        routes[route_id]['updated_at'] = datetime.now()
        save_data_to_file()  # Persist changes
        return routes[route_id]
    return None

def delete_route(route_id):
    """Delete a route"""
    if route_id in routes:
        # Remove route from all students
        for student_id in routes[route_id]['student_ids']:
            if student_id in students:
                students[student_id]['route_id'] = None
        
        del routes[route_id]
        return True
    return False

def update_route_status(route_id, status):
    """Update the status of a route"""
    if route_id in routes and status in [BUS_STATUS_NOT_PRESENT, BUS_STATUS_ARRIVED, BUS_STATUS_READY]:
        routes[route_id]['status'] = status
        routes[route_id]['updated_at'] = datetime.now()
        
        # Business logic: If route is marked as Ready, guide must be Present
        if status == BUS_STATUS_READY:
            routes[route_id]['guide_present'] = True
        
        # CRITICAL: Save changes to file for cross-device sync
        save_data_to_file()
        
        return True
    return False

def get_route_status_color(status):
    """Get the color for a route status"""
    status_colors = {
        BUS_STATUS_NOT_PRESENT: 'danger',   # Red
        BUS_STATUS_ARRIVED: 'warning',      # Orange
        BUS_STATUS_READY: 'success'         # Green
    }
    return status_colors.get(status, 'secondary')

def get_route_status_text(status):
    """Get the text for a route status"""
    status_texts = {
        BUS_STATUS_NOT_PRESENT: 'Not Present',
        BUS_STATUS_ARRIVED: 'Arrived',
        BUS_STATUS_READY: 'Ready'
    }
    return status_texts.get(status, 'Unknown')

# Provider Management Functions
def get_all_providers():
    """Get all transport providers"""
    return providers

def get_provider(provider_id):
    """Get a specific provider by ID"""
    return providers.get(provider_id)

def create_provider(name, contact_name, contact_phone, contact_email=None):
    """Create a new transport provider"""
    provider_id = generate_id()
    provider = {
        'id': provider_id,
        'name': name,
        'contact_name': contact_name,
        'contact_phone': contact_phone,
        'contact_email': contact_email,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    providers[provider_id] = provider
    return provider

def update_provider(provider_id, name, contact_name, contact_phone, contact_email=None):
    """Update an existing provider"""
    if provider_id in providers:
        providers[provider_id].update({
            'name': name,
            'contact_name': contact_name,
            'contact_phone': contact_phone,
            'contact_email': contact_email,
            'updated_at': datetime.now()
        })
        return providers[provider_id]
    return None

def delete_provider(provider_id):
    """Delete a provider"""
    if provider_id in providers:
        del providers[provider_id]
        return True
    return False

# Area Management Functions
def get_all_areas():
    """Get all parking areas"""
    return areas

def get_area(area_id):
    """Get a specific area by ID"""
    return areas.get(area_id)

def create_area(name, school_id, description=None):
    """Create a new parking area"""
    area_id = generate_id()
    area = {
        'id': area_id,
        'name': name,
        'school_id': school_id,
        'description': description,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    areas[area_id] = area
    return area

def update_area(area_id, name, school_id, description=None):
    """Update an existing area"""
    if area_id in areas:
        areas[area_id].update({
            'name': name,
            'school_id': school_id,
            'description': description,
            'updated_at': datetime.now()
        })
        return areas[area_id]
    return None

def delete_area(area_id):
    """Delete an area"""
    if area_id in areas:
        del areas[area_id]
        return True
    return False

def get_school_areas(school_id):
    """Get all areas for a specific school"""
    return {area_id: area_data for area_id, area_data in areas.items() if area_data['school_id'] == school_id}

def get_routes_by_area(area_id):
    """Get all routes for a specific area"""
    routes_data = get_all_routes()
    areas_data = get_all_areas()
    area_name = areas_data.get(area_id, {}).get('name', '')
    
    # Match by area_name since routes now store area_name directly
    return {route_id: route_data for route_id, route_data in routes_data.items() 
            if route_data.get('area_name', '') == area_name or route_data.get('area_id') == area_id}

# Staff Management Functions
def get_all_staff():
    """Get all staff members"""
    return staff

def get_unique_class_names():
    """Get all unique class names from students"""
    class_names = set()
    for student in students.values():
        if student.get('class_name'):
            class_names.add(student['class_name'])
    return sorted(list(class_names))

def get_staff(staff_id):
    """Get a specific staff member by ID"""
    return staff.get(staff_id)

def create_staff(name, staff_type, phone, email, license_number=None, first_aid_level=None, languages_spoken=None, account_type=None, has_account=False):
    """Create a new staff member"""
    staff_id = generate_id()
    staff_member = {
        'id': staff_id,
        'name': name,
        'type': staff_type,
        'phone': phone,
        'email': email,
        'license_number': license_number,
        'first_aid_level': first_aid_level,
        'languages_spoken': languages_spoken or [],
        'has_account': has_account,
        'account_type': account_type,  # 'admin' or 'class'
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    staff[staff_id] = staff_member
    save_data_to_file()
    return staff_member

def update_staff(staff_id, name, staff_type, phone, email, license_number=None, first_aid_level=None, languages_spoken=None, account_type=None, has_account=False):
    """Update an existing staff member"""
    if staff_id in staff:
        staff[staff_id].update({
            'name': name,
            'type': staff_type,
            'phone': phone,
            'email': email,
            'license_number': license_number,
            'first_aid_level': first_aid_level,
            'languages_spoken': languages_spoken or [],
            'has_account': has_account,
            'account_type': account_type,
            'updated_at': datetime.now()
        })
        save_data_to_file()
        return staff[staff_id]
    return None

def delete_staff(staff_id):
    """Delete a staff member"""
    if staff_id in staff:
        # Remove staff from all route assignments
        for route_id, route_data in routes.items():
            if route_data['driver_id'] == staff_id:
                routes[route_id]['driver_id'] = None
            if staff_id in route_data['guide_ids']:
                routes[route_id]['guide_ids'].remove(staff_id)
        
        del staff[staff_id]
        return True
    return False

def create_guides_csv_template():
    """Create a CSV template for staff/guides import"""
    csv_data = [
        ['Name', 'Type', 'Phone', 'Email', 'License Number', 'First Aid Level', 'Languages Spoken'],
        ['John Smith', 'Driver', '07700900123', 'john.smith@email.com', 'D1234567', 'Basic', 'English'],
        ['Sarah Jones', 'Guide', '07700900456', 'sarah.jones@email.com', '', 'Pediatric', 'English, Welsh'],
        ['Mike Brown', 'Driver/Guide', '07700900789', 'mike.brown@email.com', 'D7654321', 'Advanced', 'English, Spanish']
    ]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_data)
    return output.getvalue()

# Student Management Functions
def get_all_students():
    """Get all students"""
    return students

def get_student(student_id):
    """Get a specific student by ID"""
    return students.get(student_id)

def create_student(name, grade, class_name, parent_name, parent_phone, address, 
                  has_medical_needs=False, requires_pediatric_first_aid=False, medical_notes=None, harness=None,
                  safeguarding_notes='', parent2_name='', parent2_phone=''):
    """Create a new student with duplicate detection"""
    # Check for duplicate student by name (regardless of class)
    existing_duplicate = check_duplicate_student(name, class_name)
    if existing_duplicate:
        raise ValueError(f"Student '{name}' already exists in class '{existing_duplicate['class_name']}'. Cannot create duplicate.")
    
    # Validate medical data consistency: P badge requires medical needs = Yes
    if requires_pediatric_first_aid and not has_medical_needs:
        has_medical_needs = True  # Auto-correct: set medical needs to Yes if P badge is required
        if not medical_notes:
            medical_notes = "Requires pediatric first aid support"
    
    student_id = generate_id()
    student = {
        'id': student_id,
        'name': name,
        'grade': grade,
        'class_name': class_name,  # New field for class information
        'parent_name': parent_name,
        'parent_phone': parent_phone,
        'parent2_name': parent2_name,
        'parent2_phone': parent2_phone,
        'address': address,
        'has_medical_needs': has_medical_needs,
        'requires_pediatric_first_aid': requires_pediatric_first_aid,
        'medical_notes': medical_notes,
        'harness': harness,
        'safeguarding_notes': safeguarding_notes,
        'route_id': None,  # Route assignment
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    students[student_id] = student
    save_data_to_file()
    return student

def update_student(student_id, name, grade, class_name, parent_name, parent_phone, address,
                  has_medical_needs=False, requires_pediatric_first_aid=False, medical_notes=None, harness=None,
                  safeguarding_notes='', parent2_name='', parent2_phone=''):
    """Update an existing student"""
    if student_id in students:
        # Validate medical data consistency: P badge requires medical needs = Yes
        if requires_pediatric_first_aid and not has_medical_needs:
            has_medical_needs = True  # Auto-correct: set medical needs to Yes if P badge is required
            if not medical_notes:
                medical_notes = "Requires pediatric first aid support"
        students[student_id].update({
            'name': name,
            'grade': grade,
            'class_name': class_name,
            'parent_name': parent_name,
            'parent_phone': parent_phone,
            'parent2_name': parent2_name,
            'parent2_phone': parent2_phone,
            'address': address,
            'has_medical_needs': has_medical_needs,
            'requires_pediatric_first_aid': requires_pediatric_first_aid,
            'medical_notes': medical_notes,
            'harness': harness,
            'safeguarding_notes': safeguarding_notes,
            'updated_at': datetime.now()
        })
        save_data_to_file()  # Persist the changes
        return students[student_id]
    return None



def check_duplicate_student(name, class_name):
    """Check if a student with the same name already exists (regardless of class)"""
    for student in students.values():
        if student['name'].lower() == name.lower():
            return student
    return None

def find_all_duplicates():
    """Find all duplicate students (same name and class)"""
    duplicates = {}
    for student_id, student in students.items():
        key = (student['name'].lower(), student['class_name'])
        if key not in duplicates:
            duplicates[key] = []
        duplicates[key].append((student_id, student))
    
    # Return only groups with more than one student
    return {key: group for key, group in duplicates.items() if len(group) > 1}

def find_name_duplicates():
    """Find all students with duplicate names (regardless of class)"""
    name_groups = {}
    for student_id, student in students.items():
        name_key = student['name'].lower()
        if name_key not in name_groups:
            name_groups[name_key] = []
        name_groups[name_key].append((student_id, student))
    
    # Return only groups with more than one student
    return {name: group for name, group in name_groups.items() if len(group) > 1}

def remove_duplicate_students():
    """Remove duplicate students, keeping only the first occurrence of each name/class combination"""
    duplicates = find_all_duplicates()
    removed_count = 0
    
    for (name, class_name), duplicate_group in duplicates.items():
        # Keep the first student, remove the rest
        to_keep = duplicate_group[0][0]  # First student ID
        to_remove = [student_id for student_id, student in duplicate_group[1:]]
        
        for student_id in to_remove:
            if student_id in students:
                del students[student_id]
                removed_count += 1
        
        print(f"Removed {len(to_remove)} duplicate(s) of '{name}' in class '{class_name}', kept ID: {to_keep}")
    
    if removed_count > 0:
        save_data_to_file()
        print(f"Total duplicates removed: {removed_count}")
    
    return removed_count

def remove_name_duplicates():
    """Remove students with duplicate names across all classes, keeping only the first occurrence"""
    name_duplicates = find_name_duplicates()
    removed_count = 0
    
    for name, duplicate_group in name_duplicates.items():
        print(f"\nFound {len(duplicate_group)} students with name '{name}':")
        for student_id, student in duplicate_group:
            print(f"  ID: {student_id}, Class: {student.get('class_name', 'N/A')}")
        
        # Keep the first student, remove the rest
        to_keep = duplicate_group[0][0]  # First student ID
        to_remove = [student_id for student_id, student in duplicate_group[1:]]
        
        for student_id in to_remove:
            if student_id in students:
                removed_student = students[student_id]
                del students[student_id]
                removed_count += 1
                print(f"  Removed: {removed_student['name']} from class {removed_student.get('class_name', 'N/A')}")
        
        kept_student = students[to_keep]
        print(f"  Kept: {kept_student['name']} in class {kept_student.get('class_name', 'N/A')}")
    
    if removed_count > 0:
        save_data_to_file()
        print(f"\nTotal name duplicates removed: {removed_count}")
    
    return removed_count

def delete_student(student_id):
    """Delete a student"""
    if student_id in students:
        # Remove student from route assignment
        route_id = students[student_id].get('route_id')
        if route_id and route_id in routes:
            if student_id in routes[route_id]['student_ids']:
                routes[route_id]['student_ids'].remove(student_id)
        
        del students[student_id]
        return True
    return False

def assign_student_to_route(student_id, route_id):
    """Assign a student to a route"""
    print(f"DEBUG: Attempting to assign student {student_id} to route {route_id}")
    print(f"DEBUG: Student exists: {student_id in students}, Route exists: {route_id in routes}")
    
    if student_id in students and route_id in routes:
        # Remove from previous route if assigned
        old_route_id = students[student_id].get('route_id')
        if old_route_id and old_route_id in routes:
            if student_id in routes[old_route_id]['student_ids']:
                routes[old_route_id]['student_ids'].remove(student_id)
        
        # Assign to new route
        students[student_id]['route_id'] = route_id
        if student_id not in routes[route_id]['student_ids']:
            routes[route_id]['student_ids'].append(student_id)
        
        print(f"DEBUG: Successfully assigned student {student_id} ({students[student_id]['name']}) to route {route_id}")
        save_data_to_file()  # Save data immediately after assignment
        return True
    
    print(f"DEBUG: Failed to assign student {student_id} to route {route_id}")
    return False

def remove_student_from_route(student_id):
    """Remove a student from their current route"""
    if student_id in students:
        route_id = students[student_id].get('route_id')
        if route_id and route_id in routes:
            if student_id in routes[route_id]['student_ids']:
                routes[route_id]['student_ids'].remove(student_id)
        
        students[student_id]['route_id'] = None
        save_data_to_file()  # Persist changes
        return True
    return False

# CSV Export Functions
def export_schools_to_csv():
    """Export all schools to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Name', 'Address', 'Contact 1 Name', 'Contact 1 Role', 'Contact 1 Email', 'Contact 1 Phone',
                     'Contact 2 Name', 'Contact 2 Role', 'Contact 2 Email', 'Contact 2 Phone'])
    
    # Write data
    for school in schools.values():
        contact2 = school.get('contact2', {}) or {}
        writer.writerow([
            school['name'],
            school['address'],
            school['contact1']['name'],
            school['contact1']['role'],
            school['contact1']['email'],
            school['contact1']['phone'],
            contact2.get('name', ''),
            contact2.get('role', ''),
            contact2.get('email', ''),
            contact2.get('phone', '')
        ])
    
    return output.getvalue()

def import_schools_from_csv(csv_file):
    """Import schools from CSV file"""
    try:
        content = csv_file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        imported_count = 0
        for row in reader:
            create_school(
                name=row['Name'],
                address=row['Address'],
                contact1_name=row['Contact 1 Name'],
                contact1_role=row['Contact 1 Role'],
                contact1_email=row['Contact 1 Email'],
                contact1_phone=row['Contact 1 Phone'],
                contact2_name=row.get('Contact 2 Name') or None,
                contact2_role=row.get('Contact 2 Role') or None,
                contact2_email=row.get('Contact 2 Email') or None,
                contact2_phone=row.get('Contact 2 Phone') or None
            )
            imported_count += 1
        
        return imported_count, None
    except Exception as e:
        return 0, str(e)

# Initialize sample data
def initialize_sample_data():
    """Initialize the system with sample data - only in development"""
    # Skip sample data initialization in production
    import os
    deployment_env = os.environ.get('DEPLOYMENT_ENV', 'development')
    if deployment_env != 'development':
        print("Production mode: Skipping sample data initialization")
        return
        
    # Only clear and initialize if no data exists
    if schools or routes or areas or providers:
        print("Skipping sample data initialization - existing data found")
        return
        
    # Clear existing data
    schools.clear()
    routes.clear()
    staff.clear()
    students.clear()
    providers.clear()
    areas.clear()
    
    # Create sample schools
    school1 = create_school(
        name="Greenwood Primary School",
        address="123 Oak Street, Manchester, M1 2AB",
        contact1_name="Sarah Johnson",
        contact1_role="Headteacher",
        contact1_email="s.johnson@greenwood.sch.uk",
        contact1_phone="0161 234 5678",
        contact2_name="Mark Thompson",
        contact2_role="Deputy Head",
        contact2_email="m.thompson@greenwood.sch.uk",
        contact2_phone="0161 234 5679"
    )
    
    school2 = create_school(
        name="Riverside Secondary School",
        address="456 River Road, Birmingham, B2 3CD",
        contact1_name="Emma Wilson",
        contact1_role="Headteacher",
        contact1_email="e.wilson@riverside.sch.uk",
        contact1_phone="0121 345 6789",
        contact2_name="James Clarke",
        contact2_role="Assistant Head",
        contact2_email="j.clarke@riverside.sch.uk",
        contact2_phone="0121 345 6790"
    )
    
    school3 = create_school(
        name="Hillcrest Academy",
        address="789 Hill View, London, SE1 4EF",
        contact1_name="David Brown",
        contact1_role="Principal",
        contact1_email="d.brown@hillcrest.sch.uk",
        contact1_phone="020 7123 4567"
    )
    
    # Create sample providers including Parent as default
    provider_parent = create_provider(
        name="Parent",
        contact_name="Parent Collection",
        contact_phone="",
        contact_email=""
    )
    
    provider1 = create_provider(
        name="HATS Transport",
        contact_name="Mike Johnson",
        contact_phone="0161 123 4567",
        contact_email="mike@hatstransport.co.uk"
    )
    
    provider2 = create_provider(
        name="Green Destination",
        contact_name="Sarah Williams",
        contact_phone="0121 987 6543",
        contact_email="sarah@greendestination.co.uk"
    )
    
    provider3 = create_provider(
        name="Swift Travel",
        contact_name="David Brown",
        contact_phone="020 8765 4321",
        contact_email="david@swifttravel.co.uk"
    )
    
    # Create sample areas
    area1 = create_area(
        name="Secondary",
        school_id=school1['id'],
        description="Secondary school area"
    )
    
    area2 = create_area(
        name="Dawdle",
        school_id=school1['id'],
        description="Dawdle area"
    )
    
    area3 = create_area(
        name="Front of school",
        school_id=school1['id'],
        description="Front of school area"
    )
    
    area4 = create_area(
        name="Multiple areas",
        school_id=school1['id'],
        description="Used for parent collection across multiple areas"
    )
    
    # Create sample routes
    route1 = create_route(
        school_id=school1['id'],
        route_number="N1",
        provider_id=provider1['id'],
        area_id=area1['id']
    )
    
    route2 = create_route(
        school_id=school1['id'],
        route_number="S1",
        provider_id=provider2['id'],
        area_id=area2['id']
    )
    
    route3 = create_route(
        school_id=school1['id'],
        route_number="C1",
        provider_id=provider1['id'],
        area_id=area3['id']
    )
    
    route4 = create_route(
        school_id=school1['id'],
        route_number="E1",
        provider_id=provider3['id'],
        area_id=area1['id']
    )
    
    route5 = create_route(
        school_id=school1['id'],
        route_number="W1",
        provider_id=provider2['id'],
        area_id=area2['id']
    )
    
    # Create a parent collection route
    route6 = create_route(
        school_id=school1['id'],
        route_number="Parent",
        provider_id=provider_parent['id'],
        area_id=area4['id']
    )
    
    # Set different statuses for demonstration
    update_route_status(route1['id'], BUS_STATUS_READY)
    update_route_status(route2['id'], BUS_STATUS_ARRIVED)
    update_route_status(route3['id'], BUS_STATUS_NOT_PRESENT)
    update_route_status(route4['id'], BUS_STATUS_READY)
    update_route_status(route5['id'], BUS_STATUS_ARRIVED)
    
    # Set some guide presence statuses
    route2['guide_present'] = False  # This route has no guide, so it's in arrived status
    route5['guide_present'] = False  # This route has no guide, so it's in arrived status
    
    # Create sample staff
    staff1 = create_staff(
        name="John Smith",
        staff_type="driver",
        phone="07123 456789",
        email="j.smith@transport.com",
        license_number="DL123456789"
    )
    
    staff2 = create_staff(
        name="Mary Johnson",
        staff_type="guide",
        phone="07234 567890",
        email="m.johnson@transport.com",
        first_aid_level="pediatric",
        languages_spoken=["English", "Spanish"]
    )
    
    staff3 = create_staff(
        name="David Wilson",
        staff_type="driver",
        phone="07345 678901",
        email="d.wilson@transport.com",
        license_number="DL987654321"
    )
    
    staff4 = create_staff(
        name="Sarah Brown",
        staff_type="guide",
        phone="07456 789012",
        email="s.brown@transport.com",
        first_aid_level="basic",
        languages_spoken=["English", "French"]
    )
    
    # Create sample students
    student1 = create_student(
        name="Emily Johnson",
        grade="3",
        class_name="3",
        parent_name="John Johnson",
        parent_phone="07123 456789",
        address="12 Maple Street, Manchester, M2 3EF",
        has_medical_needs=False,
        harness="Yes"
    )
    
    student2 = create_student(
        name="Oliver Williams",
        grade="4",
        class_name="4", 
        parent_name="Sarah Williams",
        parent_phone="07234 567890",
        address="34 Birch Avenue, Manchester, M3 4GH",
        has_medical_needs=True,
        requires_pediatric_first_aid=True,
        medical_notes="Severe nut allergy - EpiPen required",
        harness="Yes"
    )
    
    student3 = create_student(
        name="Sophie Brown",
        grade="10",
        class_name="10",
        parent_name="Michael Brown",
        parent_phone="07345 678901",
        address="56 Cedar Road, Birmingham, B4 5IJ",
        has_medical_needs=False,
        harness="No",
        safeguarding_notes="Special dietary requirements - vegetarian only, no contact with nuts"
    )
    
    student4 = create_student(
        name="James Davis",
        grade="11",
        class_name="11",
        parent_name="Lisa Davis",
        parent_phone="07456 789012",
        address="78 Pine Close, Birmingham, B5 6KL",
        has_medical_needs=True,
        requires_pediatric_first_aid=False,
        medical_notes="Asthma - inhaler available",
        harness="No",
        safeguarding_notes="Not to be collected by father - contact school office if father attempts collection"
    )
    
    student5 = create_student(
        name="Isabella Miller",
        grade="7",
        class_name="7",
        parent_name="Robert Miller",
        parent_phone="07567 890123",
        address="90 Willow Way, London, SE2 7MN",
        has_medical_needs=False
    )
    
    # Assign students to routes
    assign_student_to_route(student1['id'], route1['id'])
    assign_student_to_route(student2['id'], route2['id'])
    assign_student_to_route(student3['id'], route3['id'])
    assign_student_to_route(student4['id'], route6['id'])  # Assign James Davis to parent collection
    assign_student_to_route(student5['id'], route5['id'])
    
    # Initialize students without safeguarding notes
    for student in students.values():
        if 'safeguarding_notes' not in student:
            student['safeguarding_notes'] = ''
    

            
    print("Sample data initialized successfully!")
    print(f"Created {len(schools)} schools, {len(routes)} routes, {len(staff)} staff members, and {len(students)} students")

# Helper functions for sorting and searching
def sort_schools(schools_dict, sort_by):
    """Sort schools by specified field"""
    if sort_by == 'name':
        return dict(sorted(schools_dict.items(), key=lambda x: x[1]['name']))
    elif sort_by == 'address':
        return dict(sorted(schools_dict.items(), key=lambda x: x[1]['address']))
    elif sort_by == 'created_at':
        return dict(sorted(schools_dict.items(), key=lambda x: x[1]['created_at'], reverse=True))
    return schools_dict

def search_schools(search_query):
    """Search schools by name or address"""
    search_query = search_query.lower()
    filtered_schools = {}
    for school_id, school in schools.items():
        if (search_query in school['name'].lower() or 
            search_query in school['address'].lower()):
            filtered_schools[school_id] = school
    return filtered_schools

def sort_routes(routes_dict, sort_by):
    """Sort routes by specified field"""
    if sort_by == 'name':
        return dict(sorted(routes_dict.items(), key=lambda x: x[1]['route_name']))
    elif sort_by == 'number':
        return dict(sorted(routes_dict.items(), key=lambda x: x[1]['route_number']))
    elif sort_by == 'capacity':
        return dict(sorted(routes_dict.items(), key=lambda x: x[1]['capacity'], reverse=True))
    elif sort_by == 'status':
        return dict(sorted(routes_dict.items(), key=lambda x: x[1]['status']))
    return routes_dict

def search_routes(search_query):
    """Search routes by name or number"""
    search_query = search_query.lower()
    filtered_routes = {}
    for route_id, route in routes.items():
        if (search_query in route['route_name'].lower() or 
            search_query in route['route_number'].lower()):
            filtered_routes[route_id] = route
    return filtered_routes

def sort_staff(staff_dict, sort_by):
    """Sort staff by specified field"""
    if sort_by == 'name':
        return dict(sorted(staff_dict.items(), key=lambda x: x[1]['name']))
    elif sort_by == 'type':
        return dict(sorted(staff_dict.items(), key=lambda x: x[1]['type']))
    elif sort_by == 'email':
        return dict(sorted(staff_dict.items(), key=lambda x: x[1]['email']))
    return staff_dict

def search_staff(search_query):
    """Search staff by name or email"""
    search_query = search_query.lower()
    filtered_staff = {}
    for staff_id, staff_member in staff.items():
        if (search_query in staff_member['name'].lower() or 
            search_query in staff_member['email'].lower()):
            filtered_staff[staff_id] = staff_member
    return filtered_staff

def sort_students(students_dict, sort_by):
    """Sort students by specified field"""
    if sort_by == 'name':
        return dict(sorted(students_dict.items(), key=lambda x: x[1]['name']))
    elif sort_by == 'grade':
        return dict(sorted(students_dict.items(), key=lambda x: x[1]['grade']))
    elif sort_by == 'class':
        return dict(sorted(students_dict.items(), key=lambda x: x[1]['class_name']))
    return students_dict

def search_students(search_query):
    """Search students by name or parent name"""
    search_query = search_query.lower()
    filtered_students = {}
    for student_id, student in students.items():
        if (search_query in student['name'].lower() or 
            search_query in student['parent_name'].lower()):
            filtered_students[student_id] = student
    return filtered_students

def get_staff_by_type(staff_type):
    """Get staff members by type (driver, guide, etc.)"""
    return {staff_id: staff_member for staff_id, staff_member in staff.items() if staff_member['type'] == staff_type}

def get_available_drivers():
    """Get available drivers (placeholder - returns all drivers for now)"""
    return get_staff_by_type('driver')

def toggle_guide_presence(route_id):
    """Toggle guide presence for a route"""
    route = get_route(route_id)
    if route:
        route['guide_present'] = not route['guide_present']
        route['updated_at'] = datetime.now()
        
        # Note: Guide presence is independent of route status
        # Route status should only change through explicit status updates
        
        return route
    return None

def get_parking_areas():
    """Get all unique parking areas"""
    areas = set()
    for route in routes.values():
        if route.get('parking_area'):
            areas.add(route['parking_area'])
    
    # Add some default areas if none exist
    if not areas:
        areas = {'Main Area', 'North Parking', 'South Parking', 'East Parking', 'West Parking'}
    
    return sorted(list(areas))

# CSV Template and Processing Functions for Routes

def create_routes_csv_template():
    """Create a CSV template for route uploads"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row - all fields are optional except route_number
    writer.writerow(['route_number', 'provider_name', 'provider_contact', 'provider_phone', 'area_name'])
    
    # Single example row
    writer.writerow(['R001', 'HATS Transport', 'John Smith', '01234 567890', 'Secondary'])
    
    return output.getvalue()

def process_routes_csv(csv_content):
    """Process CSV content and create routes with providers and students"""
    results = {'success': [], 'errors': []}
    
    try:
        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # Get default school (first school in the system)
        schools_list = list(schools.values())
        if not schools_list:
            results['errors'].append('No schools found in the system. Please add a school first.')
            return results
        
        default_school = schools_list[0]
        
        # Track routes and students to group them
        route_data = {}
        
        # Process each row
        for row_num, row in enumerate(reader, start=2):
            try:
                # Try different column name formats
                route_number = (row.get('route_number', '') or 
                              row.get('Route Name', '') or 
                              row.get('route_name', '')).strip()
                
                provider_name = (row.get('provider_name', '') or 
                               row.get('Provider Name', '') or 
                               'Default Provider').strip()
                
                provider_contact = (row.get('provider_contact', '') or 
                                  row.get('Provider Contact', '')).strip()
                
                provider_phone = (row.get('provider_phone', '') or 
                                row.get('Provider Phone', '')).strip()
                
                area_name = (row.get('area_name', '') or 
                           row.get('Area', '') or 
                           row.get('area', '')).strip()
                
                # Skip completely empty rows
                if not route_number and not provider_name and not area_name:
                    continue
                
                # Validate required fields - only route_number is absolutely required
                if not route_number:
                    results['errors'].append(f'Row {row_num}: Route number is required')
                    continue
                
                # Group routes and students - use route_number as unique key
                route_key = route_number
                
                if route_key not in route_data:
                    route_data[route_key] = {
                        'route_number': route_number,
                        'provider_name': provider_name or 'To Be Assigned',
                        'provider_contact': provider_contact,
                        'provider_phone': provider_phone,
                        'area_name': area_name or 'To Be Assigned'
                    }
                
            except Exception as e:
                results['errors'].append(f'Row {row_num}: Error processing row - {str(e)}')
        
        # Now create the routes from the grouped data
        for route_key, route_info in route_data.items():
            try:
                route_number = route_info['route_number']
                provider_name = route_info['provider_name']
                provider_contact = route_info['provider_contact']
                provider_phone = route_info['provider_phone']
                area_name = route_info['area_name']
                
                # Check if route number already exists
                existing_route = None
                for route in routes.values():
                    if route['route_number'] == route_number:
                        existing_route = route
                        break
                
                if existing_route:
                    results['errors'].append(f'Route number "{route_number}" already exists')
                    continue
                
                # Find or create provider
                provider_id = None
                for pid, provider in providers.items():
                    if provider['name'].lower() == provider_name.lower():
                        provider_id = pid
                        break
                
                if not provider_id:
                    # Create new provider if it doesn't exist
                    if provider_contact and provider_phone:
                        new_provider = create_provider(
                            name=provider_name,
                            contact_name=provider_contact,
                            contact_phone=provider_phone,
                            contact_email=None
                        )
                        provider_id = new_provider['id']
                        results['success'].append(f'Created new provider: "{provider_name}"')
                    else:
                        # Create default provider if none specified
                        new_provider = create_provider(
                            name=provider_name,
                            contact_name='Contact Required',
                            contact_phone='Phone Required',
                            contact_email=None
                        )
                        provider_id = new_provider['id']
                        results['success'].append(f'Created new provider: "{provider_name}" (please update contact details)')
                
                # Find area by name - handle optional area
                area_id = None
                if area_name and area_name != 'To Be Assigned':
                    for aid, area in areas.items():
                        if area['name'].lower() == area_name.lower():
                            area_id = aid
                            break
                    
                    if not area_id:
                        # Create new area if it doesn't exist
                        new_area = create_area(area_name, default_school['id'])
                        area_id = new_area['id']
                        results['success'].append(f'Created new area: "{area_name}"')
                else:
                    # Use a default area if none specified
                    default_areas = list(areas.values())
                    if default_areas:
                        area_id = default_areas[0]['id']
                    else:
                        # Create a default area if none exist
                        new_area = create_area('Main Area', default_school['id'])
                        area_id = new_area['id']
                        results['success'].append('Created default area: "Main Area"')
                
                # Create route
                route = create_route(
                    school_id=default_school['id'],
                    route_number=route_number,
                    provider_id=provider_id,
                    area_id=area_id
                )
                
                # Store the area_name and provider_name directly in route data for display
                if provider_name and provider_name != 'To Be Assigned':
                    route['provider_name'] = provider_name
                elif provider_id and provider_id in providers:
                    route['provider_name'] = providers[provider_id]['name']
                    
                if area_name and area_name != 'To Be Assigned':
                    route['area_name'] = area_name
                elif area_id and area_id in areas:
                    route['area_name'] = areas[area_id]['name']
                
                results['success'].append(f'Route "{route_number}" created successfully')
                    
            except Exception as e:
                results['errors'].append(f'Error creating route "{route_number}": {str(e)}')
                
    except Exception as e:
        results['errors'].append(f'Error reading CSV file: {str(e)}')
    
    # Set flag to indicate routes were updated
    global _routes_updated
    if results['success']:
        _routes_updated = True
        print(f"Routes CSV processed: {len(results['success'])} successful operations, {len(results['errors'])} errors")
        print(f"Total routes now in system: {len(routes)}")
        # Save data to persistence file
        save_data_to_file()
    
    return results

def create_schools_csv_template():
    """Create a CSV template for school uploads"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow(['name', 'address', 'contact1_name', 'contact1_role', 'contact1_email', 'contact1_phone', 'contact2_name', 'contact2_role', 'contact2_email', 'contact2_phone'])
    
    # Sample data rows
    writer.writerow(['Greenwood Primary School', '123 High Street, Manchester, M1 2AB', 'John Smith', 'Principal', 'j.smith@greenwood.edu', '0161 234 5678', 'Mary Johnson', 'Vice Principal', 'm.johnson@greenwood.edu', '0161 234 5679'])
    writer.writerow(['Oakview High School', '456 Oak Avenue, Birmingham, B2 3CD', 'David Brown', 'Head Teacher', 'd.brown@oakview.edu', '0121 345 6789', '', '', '', ''])
    
    return output.getvalue()

def process_schools_csv(csv_content):
    """Process CSV content and create schools"""
    results = {'success': [], 'errors': []}
    
    try:
        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # Process each row
        for row_num, row in enumerate(reader, start=2):
            try:
                name = row.get('name', '').strip()
                address = row.get('address', '').strip()
                contact1_name = row.get('contact1_name', '').strip()
                contact1_role = row.get('contact1_role', '').strip()
                contact1_email = row.get('contact1_email', '').strip()
                contact1_phone = row.get('contact1_phone', '').strip()
                contact2_name = row.get('contact2_name', '').strip()
                contact2_role = row.get('contact2_role', '').strip()
                contact2_email = row.get('contact2_email', '').strip()
                contact2_phone = row.get('contact2_phone', '').strip()
                
                # Validate required fields
                if not name:
                    results['errors'].append(f'Row {row_num}: School name is required')
                    continue
                
                if not address:
                    results['errors'].append(f'Row {row_num}: Address is required')
                    continue
                
                if not contact1_name:
                    results['errors'].append(f'Row {row_num}: Primary contact name is required')
                    continue
                
                if not contact1_role:
                    results['errors'].append(f'Row {row_num}: Primary contact role is required')
                    continue
                
                if not contact1_email:
                    results['errors'].append(f'Row {row_num}: Primary contact email is required')
                    continue
                
                if not contact1_phone:
                    results['errors'].append(f'Row {row_num}: Primary contact phone is required')
                    continue
                
                # Check if school already exists
                existing_school = None
                for school in schools.values():
                    if school['name'].lower() == name.lower():
                        existing_school = school
                        break
                
                if existing_school:
                    results['errors'].append(f'Row {row_num}: School "{name}" already exists')
                    continue
                
                # Create school
                school = create_school(
                    name=name,
                    address=address,
                    contact1_name=contact1_name,
                    contact1_role=contact1_role,
                    contact1_email=contact1_email,
                    contact1_phone=contact1_phone,
                    contact2_name=contact2_name if contact2_name else None,
                    contact2_role=contact2_role if contact2_role else None,
                    contact2_email=contact2_email if contact2_email else None,
                    contact2_phone=contact2_phone if contact2_phone else None
                )
                
                results['success'].append(f'School "{name}" created successfully')
                
            except Exception as e:
                results['errors'].append(f'Row {row_num}: Error processing row - {str(e)}')
                
    except Exception as e:
        results['errors'].append(f'Error reading CSV file: {str(e)}')
    
    return results

def get_routes_by_parking_area(parking_area):
    """Get routes filtered by parking area"""
    if not parking_area:
        return routes
    
    filtered_routes = {}
    for route_id, route in routes.items():
        if route.get('parking_area') == parking_area:
            filtered_routes[route_id] = route
    
    return filtered_routes

# CSV Template and Processing Functions for Students
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
                
                grade = class_name  # Set grade to be the same as class name
                # Support both old and new column names for backward compatibility
                parent_name = row.get('Parent/Carer Name', row.get('Parent Name', '')).strip()
                parent_phone = row.get('Parent/Carer Phone', row.get('Parent Phone', '')).strip()
                
                # Extract optional Parent 2 contact details
                parent2_name = row.get('Parent/Carer 2 Name', '').strip()
                parent2_phone = row.get('Parent/Carer 2 Phone', '').strip()
                
                address = row['Address'].strip()
                
                # Validate required fields
                if not all([name, class_name, parent_name, parent_phone, address]):
                    results['errors'].append(f'Row {row_num}: Missing required fields')
                    continue
                
                # Validate text inputs for profanity
                text_fields = [
                    (name, "student name"),
                    (class_name, "class name"),
                    (parent_name, "parent name"),
                    (address, "address")
                ]
                
                profanity_found = False
                for text, field_name in text_fields:
                    if text:
                        is_valid, error_msg = profanity_filter.validate_educational_content(text, field_name)
                        if not is_valid:
                            results['errors'].append(f'Row {row_num}: {error_msg}')
                            profanity_found = True
                            break
                
                if profanity_found:
                    continue
                
                # Extract optional medical fields
                has_medical_needs_str = row.get('Has Medical Needs', 'No').strip().lower()
                has_medical_needs = has_medical_needs_str in ['yes', 'y', 'true', '1']
                
                requires_pediatric_first_aid_str = row.get('Requires Pediatric First Aid', 'No').strip().lower()
                requires_pediatric_first_aid = requires_pediatric_first_aid_str in ['yes', 'y', 'true', '1']
                
                medical_notes = row.get('Medical Notes', '').strip()
                harness = row.get('Harness', '').strip()
                
                # Extract optional safeguarding notes
                safeguarding_notes = row.get('Safeguarding Notes', '').strip()
                
                # Validate medical notes and safeguarding notes for profanity if present
                if medical_notes:
                    is_valid, error_msg = profanity_filter.validate_educational_content(medical_notes, "medical notes")
                    if not is_valid:
                        results['errors'].append(f'Row {row_num}: {error_msg}')
                        continue
                
                if safeguarding_notes:
                    is_valid, error_msg = profanity_filter.validate_educational_content(safeguarding_notes, "safeguarding notes")
                    if not is_valid:
                        results['errors'].append(f'Row {row_num}: {error_msg}')
                        continue
                
                # Create student with duplicate detection
                try:
                    student = create_student(
                        name=name,
                        grade=grade,
                        class_name=class_name,  # Now uses the Class column when available
                        parent_name=parent_name,
                        parent_phone=parent_phone,
                        parent2_name=parent2_name,
                        parent2_phone=parent2_phone,
                        address=address,
                        has_medical_needs=has_medical_needs,
                        requires_pediatric_first_aid=requires_pediatric_first_aid,
                        medical_notes=medical_notes,
                        harness=harness,
                        safeguarding_notes=safeguarding_notes
                    )
                    
                    results['success'].append(f'Added student: {name} (Class {class_name})')
                    
                except ValueError as e:
                    # Handle duplicate student error
                    results['errors'].append(f'Row {row_num}: {str(e)}')
                
            except Exception as e:
                results['errors'].append(f'Row {row_num}: Error processing student - {str(e)}')
                continue
                
    except Exception as e:
        results['errors'].append(f'Error reading CSV file: {str(e)}')
    
    # Set flag to indicate students were updated
    global _students_updated
    if results['success']:
        _students_updated = True
        # Save data to persistence file
        save_data_to_file()
    
    return results

# Initialize data with persistence
def initialize_data():
    """Initialize data from file or create sample data"""
    # First try to load from file
    if load_data_from_file():
        print(f"Found existing data: {len(schools)} schools, {len(routes)} routes, {len(students)} students")
    else:
        print("No existing data found, initializing sample data...")
        initialize_sample_data()
        save_data_to_file()

# Initialize on module import
initialize_data()