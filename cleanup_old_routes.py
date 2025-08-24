#!/usr/bin/env python3
"""
Cleanup old routes that don't follow the new naming convention
"""
import json

def cleanup_old_routes():
    """Remove old routes that don't follow the new naming convention"""
    try:
        with open('/tmp/hamilton_tms_data.json', 'r') as f:
            data = json.load(f)
        
        routes = data.get('routes', {})
        routes_to_delete = []
        
        # Find routes that look like old format (full name instead of "FirstName's Parent")
        for route_id, route in routes.items():
            route_number = route.get('route_number', '')
            provider_name = route.get('provider_name', '')
            
            # Check if it's a parent route with full name (contains space but doesn't end with 's Parent')
            if (provider_name == 'Parent' and 
                ' ' in route_number and 
                not route_number.endswith("'s Parent")):
                print(f"Found old route to delete: {route_number} (ID: {route_id})")
                routes_to_delete.append(route_id)
        
        # Delete the old routes
        for route_id in routes_to_delete:
            del routes[route_id]
            print(f"Deleted route: {route_id}")
        
        # Save the updated data
        if routes_to_delete:
            with open('/tmp/hamilton_tms_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Cleanup complete! Removed {len(routes_to_delete)} old routes.")
        else:
            print("No old routes found to clean up.")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_old_routes()