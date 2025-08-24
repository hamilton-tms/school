#!/usr/bin/env python3
"""
Auto-migration script that runs on application startup to ensure
database has the correct data structure and migrated data.
"""

import sys
import os
sys.path.append('.')

from app import app, db
from models import School, Route, Student, Provider, Area, Staff
import database_store as data_store
import data_store as file_store
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def auto_migrate():
    """Automatically migrate data if database is empty"""
    
    with app.app_context():
        # Check if database already has data
        existing_students = Student.query.count()
        existing_routes = Route.query.count()
        
        if existing_students > 0 and existing_routes > 0:
            logger.info(f"Database already has data: {existing_students} students, {existing_routes} routes")
            # Still run parent route fix for existing data
            fix_consolidated_parent_routes_in_db()
            return
            
        logger.info("Database appears empty, running migration...")
        
        # Load data from file storage
        try:
            file_store.load_data_from_file()
        except:
            logger.warning("No file data to migrate")
            return
        
        # Clear any existing data to avoid conflicts
        Staff.query.delete()
        Student.query.delete()
        Route.query.delete()
        Provider.query.delete()
        Area.query.delete()
        School.query.delete()
        db.session.commit()
        
        # Migrate schools
        school_count = 0
        for school_id, school_data in file_store.schools.items():
            school = School(
                id=school_id,
                name=school_data.get('name', ''),
                address=school_data.get('address', ''),
                phone=school_data.get('phone', ''),
                email=school_data.get('email', '')
            )
            db.session.add(school)
            school_count += 1
        
        # Migrate providers
        provider_count = 0
        for provider_id, provider_data in file_store.providers.items():
            provider = Provider(
                id=provider_id,
                name=provider_data.get('name', ''),
                contact_name=provider_data.get('contact_name', ''),
                phone=provider_data.get('phone', ''),
                email=provider_data.get('email', '')
            )
            db.session.add(provider)
            provider_count += 1
        
        # Migrate areas
        area_count = 0
        for area_id, area_data in file_store.areas.items():
            area = Area(
                id=area_id,
                name=area_data.get('name', ''),
                description=area_data.get('description', '')
            )
            db.session.add(area)
            area_count += 1
        
        # Migrate routes
        route_count = 0
        for route_id, route_data in file_store.routes.items():
            route = Route(
                id=route_id,
                route_number=route_data.get('route_number', ''),
                status=route_data.get('status', 'not_present'),
                area_id=route_data.get('area_id'),
                provider_id=route_data.get('provider_id'),
                max_capacity=route_data.get('max_capacity', 50)
            )
            db.session.add(route)
            route_count += 1
        
        # Migrate students
        student_count = 0
        for student_id, student_data in file_store.students.items():
            student = Student(
                id=student_id,
                name=student_data.get('name', ''),
                class_name=student_data.get('class', ''),
                route_id=student_data.get('route_id'),
                school_id=student_data.get('school_id'),
                parent1_name=student_data.get('parent1_name', ''),
                parent1_phone=student_data.get('parent1_phone', ''),
                parent2_name=student_data.get('parent2_name', ''),
                parent2_phone=student_data.get('parent2_phone', ''),
                medical_needs=student_data.get('medical_needs', ''),
                harness_required=student_data.get('harness_required', ''),
                badge_required=student_data.get('badge_required', ''),
                safeguarding_notes=student_data.get('safeguarding_notes', '')
            )
            db.session.add(student)
            student_count += 1
        
        # Commit all changes
        db.session.commit()
        
        logger.info(f"Auto-migration completed: {school_count} schools, {provider_count} providers, {area_count} areas, {route_count} routes, {student_count} students")
        
        # Fix consolidated parent routes after migration
        fix_consolidated_parent_routes_in_db()
        
        # Verify Alice students are properly separated
        alice_students = Student.query.filter(Student.name.like('%Alice%')).all()
        logger.info(f"Alice student verification after migration:")
        for student in alice_students:
            route = Route.query.get(student.route_id) if student.route_id else None
            route_name = route.route_number if route else "No route"
            logger.info(f"- {student.name} -> {route_name}")

def fix_consolidated_parent_routes_in_db():
    """Fix consolidated parent routes in database"""
    # Find problematic consolidated parent routes
    all_routes = Route.query.all()
    all_students = Student.query.all()
    
    consolidated_routes = {}
    
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
    
    if consolidated_routes:
        # Commit all changes
        db.session.commit()
        logger.info(f"Fixed {len(consolidated_routes)} consolidated parent routes")

if __name__ == '__main__':
    auto_migrate()