#!/usr/bin/env python3
"""
Create individual parent routes for check-in purposes.
For each student in the consolidated Parent route, create an individual 
"Child's Parent" route for check-in tracking.
"""

import sys
sys.path.append('.')
import data_store

def recreate_individual_parent_routes():
    """Create individual parent routes for each child assigned to parent pickup"""
    print("=== RECREATING INDIVIDUAL PARENT ROUTES FOR CHECK-IN ===")
    
    # Load current data
    data_store.load_data_from_file()
    
    # Get all routes and students
    routes = data_store.get_all_routes()
    students = data_store.get_all_students()
    
    # Find the main Parent route
    main_parent_route_id = None
    main_parent_route = None
    
    for route_id, route in routes.items():
        if route.get('route_number') == 'Parent':
            main_parent_route_id = route_id
            main_parent_route = route
            break
    
    if not main_parent_route_id:
        print("ERROR: Main Parent route not found!")
        return False
    
    # Find students assigned to the main Parent route
    parent_students = [s for s in students.values() if s.get('route_id') == main_parent_route_id]
    
    print(f"Found {len(parent_students)} students in main Parent route:")
    for student in parent_students:
        print(f"  - {student.get('name', 'Unknown')}")
    
    # Create individual routes for each student
    created_routes = 0
    
    for student in parent_students:
        student_id = student.get('id')
        student_name = student.get('name', 'Unknown')
        # Use full name to completely avoid collisions
        child_route_number = f"{student_name}'s Parent"
        
        # Check if individual route already exists
        existing_route_id = None
        for route_id, route in routes.items():
            if (route.get('route_number') == child_route_number and 
                route.get('provider_id') == main_parent_route['provider_id']):
                existing_route_id = route_id
                break
        
        if existing_route_id:
            print(f"Individual route '{child_route_number}' already exists")
            # Ensure student is assigned to individual route
            data_store.assign_student_to_route(student_id, existing_route_id)
            # Mark as hidden from admin but visible for check-in
            individual_route = data_store.get_route(existing_route_id)
            individual_route['hidden_from_admin'] = True
        else:
            # Create new individual route
            child_route = data_store.create_route(
                school_id=main_parent_route['school_id'],
                route_number=child_route_number,
                provider_id=main_parent_route['provider_id'],
                area_id=main_parent_route['area_id']
            )
            child_route['hidden_from_admin'] = True  # Mark as hidden from Route Admin
            data_store.assign_student_to_route(student_id, child_route['id'])
            print(f"Created individual route: {child_route_number}")
            created_routes += 1
    
    # Save updated data
    data_store.save_data_to_file()
    
    print(f"\n=== INDIVIDUAL ROUTE CREATION COMPLETE ===")
    print(f"Individual routes created: {created_routes}")
    print(f"Students remain in main Parent route for admin purposes")
    print(f"Individual routes available for check-in tracking")
    
    return True

if __name__ == "__main__":
    recreate_individual_parent_routes()