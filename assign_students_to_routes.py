#!/usr/bin/env python3
"""
Randomly assign students to routes with specific requirements
"""
import json
import random
from data_store import save_data_to_file, load_data_from_file

def main():
    # Load current data
    load_data_from_file()
    
    # Import the global data
    from data_store import students, routes
    
    print(f"Starting with {len(students)} students and {len(routes)} routes")
    
    # Find the parent route (contains "Parent" in name)
    parent_route_id = None
    other_routes = []
    
    for route_id, route in routes.items():
        if "Parent" in route.get("route_number", ""):
            parent_route_id = route_id
            print(f"Found parent route: {route['route_number']} (ID: {route_id})")
        else:
            other_routes.append(route_id)
    
    if not parent_route_id:
        print("ERROR: Could not find parent route!")
        return
    
    print(f"Found {len(other_routes)} other routes for assignment")
    
    # Clear all current route assignments
    for student_id in students:
        students[student_id]['route_id'] = None
    
    # Clear all route student lists
    for route_id in routes:
        routes[route_id]['student_ids'] = []
    
    # Get all student IDs as a list for random assignment
    all_student_ids = list(students.keys())
    random.shuffle(all_student_ids)
    
    # Assign first 8 students to parent route
    parent_students = all_student_ids[:8]
    for student_id in parent_students:
        students[student_id]['route_id'] = parent_route_id
        routes[parent_route_id]['student_ids'].append(student_id)
        student_name = students[student_id]['name']
        print(f"Assigned {student_name} to parent route")
    
    # Assign remaining students randomly to other routes
    remaining_students = all_student_ids[8:]
    print(f"\nAssigning {len(remaining_students)} remaining students to {len(other_routes)} other routes...")
    
    for i, student_id in enumerate(remaining_students):
        # Distribute evenly across other routes
        route_index = i % len(other_routes)
        route_id = other_routes[route_index]
        
        students[student_id]['route_id'] = route_id
        routes[route_id]['student_ids'].append(student_id)
        
        student_name = students[student_id]['name']
        route_name = routes[route_id]['route_number']
        print(f"Assigned {student_name} to route {route_name}")
    
    # Show final assignment summary
    print("\n=== ASSIGNMENT SUMMARY ===")
    for route_id, route in routes.items():
        student_count = len(route.get('student_ids', []))
        route_name = route['route_number']
        print(f"{route_name}: {student_count} students")
    
    # Save the updated data
    save_data_to_file()
    print(f"\nAssignment complete! Data saved.")

if __name__ == "__main__":
    main()