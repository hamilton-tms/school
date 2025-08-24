#!/usr/bin/env python3
"""
Fix Parent route provider assignment and consolidate parent route logic
"""

import data_store
import uuid

def consolidate_parent_routes():
    """Fix parent route provider and ensure proper parent route handling"""
    routes = data_store.get_all_routes()
    providers = data_store.get_all_providers()
    areas = data_store.get_all_areas()
    
    print("Consolidating parent route provider assignment...")
    
    # Ensure "Parent" provider exists
    parent_provider_id = None
    for p_id, provider in providers.items():
        if provider.get('name') == 'Parent':
            parent_provider_id = p_id
            break
    
    if not parent_provider_id:
        # Create Parent provider if it doesn't exist
        parent_provider_id = str(uuid.uuid4())
        providers[parent_provider_id] = {
            'id': parent_provider_id,
            'name': 'Parent',
            'contact': 'Parent Collection Service',
            'phone': 'N/A'
        }
        print("Created 'Parent' provider")
    
    # Find Front of school area
    front_area_id = None
    for a_id, area in areas.items():
        if area.get('name') == 'Front of school':
            front_area_id = a_id
            break
    
    # Update Parent route and all individual parent routes
    updated_count = 0
    for route_id, route in routes.items():
        route_number = route.get('route_number', '')
        
        # Handle main "Parent" route
        if route_number == 'Parent':
            route['provider_id'] = parent_provider_id
            route['provider_name'] = 'Parent'
            if front_area_id:
                route['area_id'] = front_area_id
                route['area_name'] = 'Front of school'
            updated_count += 1
            print(f"Updated main Parent route: Parent / Front of school")
        
        # Handle individual parent routes (format: "FirstName's Parent")
        elif "'s Parent" in route_number:
            route['provider_id'] = parent_provider_id
            route['provider_name'] = 'Parent'
            if front_area_id:
                route['area_id'] = front_area_id
                route['area_name'] = 'Front of school'
            updated_count += 1
            print(f"Updated individual parent route {route_number}: Parent / Front of school")
    
    # Save the updated data
    data_store.save_data_to_file()
    
    print(f"\n✅ Updated {updated_count} parent routes with correct provider assignment")
    print("Parent routes now properly assigned to 'Parent' provider instead of HATS!")

if __name__ == "__main__":
    consolidate_parent_routes()