#!/usr/bin/env python3
"""
Fix consolidated parent routes by creating individual routes for each child.
This addresses the Alice Parent and Edward Parent consolidation issues.
"""

import sys
sys.path.append('.')

from app import app, db
from models import Route, Student, Area
import database_store as data_store
import uuid
import logging

logger = logging.getLogger(__name__)

def fix_consolidated_parent_routes():
    """Fix consolidated parent routes by creating individual routes"""
    
    with app.app_context():
        # Find problematic consolidated parent routes
        consolidated_routes = {}
        all_routes = Route.query.all()
        all_students = Student.query.all()
        
        # Group students by route to identify consolidated routes
        for route in all_routes:
            if 'Parent' in route.route_number and route.route_number != 'Parent':
                # Get students on this route
                route_students = [s for s in all_students if s.route_id == route.id]
                
                if len(route_students) > 1:
                    # Check if students have different first names - this indicates consolidation problem
                    first_names = [s.name.split()[0] for s in route_students]
                    unique_first_names = set(first_names)
                    
                    if len(unique_first_names) > 1:
                        logger.info(f"Found consolidated route: {route.route_number} with students: {[s.name for s in route_students]}")
                        consolidated_routes[route.id] = {
                            'route': route,
                            'students': route_students,
                            'first_names': first_names
                        }
        
        # Fix each consolidated route
        for route_id, route_info in consolidated_routes.items():
            route = route_info['route']
            students = route_info['students']
            
            logger.info(f"Fixing consolidated route: {route.route_number}")
            
            # Create individual routes for each student
            for student in students:
                # Create new individual route
                individual_route_id = str(uuid.uuid4())
                individual_route = Route(
                    id=individual_route_id,
                    route_number=f"{student.name.split()[0]} {student.name.split()[1]}'s Parent",
                    status=route.status,
                    area_id=route.area_id,
                    provider_id=route.provider_id,
                    max_capacity=1
                )
                db.session.add(individual_route)
                
                # Assign student to new individual route
                student.route_id = individual_route_id
                
                logger.info(f"Created individual route: {individual_route.route_number} for {student.name}")
            
            # Delete the old consolidated route
            db.session.delete(route)
            logger.info(f"Deleted consolidated route: {route.route_number}")
        
        # Commit all changes
        db.session.commit()
        
        logger.info(f"Fixed {len(consolidated_routes)} consolidated parent routes")
        
        # Verify the fix
        remaining_alice_routes = Route.query.filter(Route.route_number.like('%Alice%')).all()
        remaining_edward_routes = Route.query.filter(Route.route_number.like('%Edward%')).all()
        
        logger.info("Verification after fix:")
        for route in remaining_alice_routes:
            students_on_route = Student.query.filter_by(route_id=route.id).all()
            logger.info(f"- {route.route_number}: {[s.name for s in students_on_route]}")
            
        for route in remaining_edward_routes:
            students_on_route = Student.query.filter_by(route_id=route.id).all()
            logger.info(f"- {route.route_number}: {[s.name for s in students_on_route]}")

if __name__ == '__main__':
    fix_consolidated_parent_routes()