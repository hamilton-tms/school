#!/usr/bin/env python3
"""
Fix route data to ensure all routes have proper provider and area information
"""

import data_store

def fix_route_provider_area_data():
    """Fix missing provider and area data for routes"""
    routes = data_store.get_all_routes()
    providers = data_store.get_all_providers()
    areas = data_store.get_all_areas()
    
    print("Fixing route provider and area data...")
    
    # Create provider mapping from the uploaded CSV data
    provider_mapping = {
        'SkyLine Travel': 'SkyLine Travel',
        'Sandwell': 'Sandwell',
        'Green Destination': 'Green Destination', 
        'BrightPath Mobility': 'BrightPath Mobility',
        'HATS': 'HATS'
    }
    
    # Create area mapping from the uploaded CSV data
    area_mapping = {
        'Dawdle': 'Dawdle',
        'Secondary': 'Secondary',
        'Front of school': 'Front of school'
    }
    
    # Ensure providers exist in the system
    for provider_name in provider_mapping.values():
        provider_exists = False
        for p_id, provider in providers.items():
            if provider.get('name') == provider_name:
                provider_exists = True
                break
        
        if not provider_exists:
            import uuid
            new_provider_id = str(uuid.uuid4())
            providers[new_provider_id] = {
                'id': new_provider_id,
                'name': provider_name,
                'contact': f'Contact for {provider_name}',
                'phone': '000-000-0000'
            }
            print(f"Created provider: {provider_name}")
    
    # Ensure areas exist in the system
    for area_name in area_mapping.values():
        area_exists = False
        for a_id, area in areas.items():
            if area.get('name') == area_name:
                area_exists = True
                break
        
        if not area_exists:
            import uuid
            new_area_id = str(uuid.uuid4())
            areas[new_area_id] = {
                'id': new_area_id,
                'name': area_name,
                'description': f'{area_name} pickup/dropoff area'
            }
            print(f"Created area: {area_name}")
    
    # Route-specific provider and area assignments based on uploaded CSV
    route_assignments = {
        '352': {'provider': 'SkyLine Travel', 'area': 'Dawdle'},
        '59': {'provider': 'Sandwell', 'area': 'Secondary'},
        '371': {'provider': 'SkyLine Travel', 'area': 'Secondary'},
        '569': {'provider': 'Green Destination', 'area': 'Front of school'},
        '238': {'provider': 'BrightPath Mobility', 'area': 'Secondary'},
        '533': {'provider': 'Sandwell', 'area': 'Dawdle'},
        '368': {'provider': 'BrightPath Mobility', 'area': 'Front of school'},
        '270': {'provider': 'HATS', 'area': 'Dawdle'},
        '938': {'provider': 'Sandwell', 'area': 'Secondary'},
        '781': {'provider': 'HATS', 'area': 'Secondary'},
        '240': {'provider': 'Green Destination', 'area': 'Dawdle'},
        '207': {'provider': 'Green Destination', 'area': 'Front of school'},
        '646': {'provider': 'Green Destination', 'area': 'Secondary'},
        '159': {'provider': 'SkyLine Travel', 'area': 'Front of school'},
        '703': {'provider': 'BrightPath Mobility', 'area': 'Dawdle'}
    }
    
    # Update routes with correct provider and area data
    updated_count = 0
    for route_id, route in routes.items():
        route_number = route.get('route_number')
        
        if route_number in route_assignments:
            assignment = route_assignments[route_number]
            
            # Find provider ID
            provider_id = None
            for p_id, provider in providers.items():
                if provider.get('name') == assignment['provider']:
                    provider_id = p_id
                    break
            
            # Find area ID
            area_id = None
            for a_id, area in areas.items():
                if area.get('name') == assignment['area']:
                    area_id = a_id
                    break
            
            if provider_id and area_id:
                # Update route data
                route['provider_id'] = provider_id
                route['provider_name'] = assignment['provider']
                route['area_id'] = area_id
                route['area_name'] = assignment['area']
                updated_count += 1
                print(f"Updated Route {route_number}: {assignment['provider']} / {assignment['area']}")
        
        # Handle original test routes with default values
        elif route_number in ['N1', 'S1', 'C1', 'E1', 'W1']:
            # Assign default provider and area for test routes
            default_provider_id = None
            default_area_id = None
            
            for p_id, provider in providers.items():
                if provider.get('name') == 'HATS':
                    default_provider_id = p_id
                    break
            
            for a_id, area in areas.items():
                if area.get('name') == 'Secondary':
                    default_area_id = a_id
                    break
            
            if default_provider_id and default_area_id:
                route['provider_id'] = default_provider_id
                route['provider_name'] = 'HATS'
                route['area_id'] = default_area_id
                route['area_name'] = 'Secondary'
                updated_count += 1
                print(f"Updated test Route {route_number}: HATS / Secondary")
        
        elif route_number == 'Parent':
            # Special handling for Parent route
            default_provider_id = None
            default_area_id = None
            
            for p_id, provider in providers.items():
                if provider.get('name') == 'HATS':
                    default_provider_id = p_id
                    break
            
            for a_id, area in areas.items():
                if area.get('name') == 'Front of school':
                    default_area_id = a_id
                    break
            
            if default_provider_id and default_area_id:
                route['provider_id'] = default_provider_id
                route['provider_name'] = 'HATS'
                route['area_id'] = default_area_id
                route['area_name'] = 'Front of school'
                updated_count += 1
                print(f"Updated Parent route: HATS / Front of school")
    
    # Save the updated data
    data_store.save_data_to_file()
    
    print(f"\n✅ Updated {updated_count} routes with provider and area information")
    print("Provider and area data has been fixed!")

if __name__ == "__main__":
    fix_route_provider_area_data()