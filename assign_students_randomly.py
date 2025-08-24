#!/usr/bin/env python3
"""
Random student assignment script for testing Hamilton TMS
Assigns existing students randomly to all available routes including parent routes
"""

import json
import random
import data_store

def assign_students_randomly():
    """Randomly assign all students to routes for testing purposes"""
    
    # Load current data from the data store
    data_store.load_data_from_file()
    data = {
        'students': data_store.students,
        'routes': data_store.routes
    }
    students = data['students']
    routes = data['routes']
    
    print(f"Found {len(students)} students and {len(routes)} routes")
    
    # Get all route IDs (including parent routes)
    route_ids = list(routes.keys())
    print(f"Available routes: {[routes[rid]['route_number'] for rid in route_ids]}")
    
    # Clear existing assignments
    for route_id in route_ids:
        routes[route_id]['student_ids'] = []
    
    # Clear student route assignments
    for student_id in students:
        students[student_id]['route_id'] = None
    
    # Randomly assign each student to a route
    assignments = {}
    for student_id, student in students.items():
        # Randomly pick a route
        chosen_route_id = random.choice(route_ids)
        chosen_route = routes[chosen_route_id]
        
        # Assign student to route
        student['route_id'] = chosen_route_id
        routes[chosen_route_id]['student_ids'].append(student_id)
        
        # Track for summary
        route_name = chosen_route['route_number']
        if route_name not in assignments:
            assignments[route_name] = []
        assignments[route_name].append(student['name'])
        
        print(f"Assigned {student['name']} to route {route_name}")
    
    # Handle parent route logic - if any students assigned to individual parent routes,
    # also assign them to the main "Parent" route for consolidated view
    parent_route_id = None
    individual_parent_routes = []
    
    for route_id, route in routes.items():
        if route['route_number'] == 'Parent':
            parent_route_id = route_id
        elif route['route_number'].endswith("'s Parent"):
            individual_parent_routes.append(route_id)
    
    # If students were assigned to individual parent routes, also add them to main Parent route
    if parent_route_id and individual_parent_routes:
        parent_student_ids = set(routes[parent_route_id]['student_ids'])
        for individual_route_id in individual_parent_routes:
            for student_id in routes[individual_route_id]['student_ids']:
                parent_student_ids.add(student_id)
        
        routes[parent_route_id]['student_ids'] = list(parent_student_ids)
        print(f"Updated main Parent route with {len(parent_student_ids)} total students")
    
    # Update the global data store
    data_store.students = students
    data_store.routes = routes
    
    # Save the updated data
    data_store.save_data_to_file()
    
    # Print summary
    print("\n=== ASSIGNMENT SUMMARY ===")
    for route_name, student_names in assignments.items():
        print(f"{route_name}: {len(student_names)} students - {', '.join(student_names)}")
    
    print(f"\nTotal students assigned: {len(students)}")
    print("Random assignment completed successfully!")

if __name__ == "__main__":
    assign_students_randomly()