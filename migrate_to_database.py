#!/usr/bin/env python3
"""
Migration script to move data from file-based storage to PostgreSQL database.
This ensures data persistence through deployments.
"""

import sys
import os
sys.path.append('.')

from app import app, db
from models import School, Route, Student, Provider, Area, Staff
import data_store
import uuid
from datetime import datetime

def migrate_data():
    """Migrate all data from file storage to database"""
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        print("Loading data from file storage...")
        data_store.load_data_from_file()
        
        # Clear existing database data to avoid conflicts
        print("Clearing existing database data...")
        Staff.query.delete()
        Student.query.delete()
        Route.query.delete()
        Provider.query.delete()
        Area.query.delete()
        School.query.delete()
        db.session.commit()
        
        # Migrate schools
        print("Migrating schools...")
        school_count = 0
        for school_id, school_data in data_store.schools.items():
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
        print("Migrating providers...")
        provider_count = 0
        for provider_id, provider_data in data_store.providers.items():
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
        print("Migrating areas...")
        area_count = 0
        for area_id, area_data in data_store.areas.items():
            area = Area(
                id=area_id,
                name=area_data.get('name', ''),
                description=area_data.get('description', '')
            )
            db.session.add(area)
            area_count += 1
        
        # Migrate routes
        print("Migrating routes...")
        route_count = 0
        for route_id, route_data in data_store.routes.items():
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
        print("Migrating students...")
        student_count = 0
        for student_id, student_data in data_store.students.items():
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
        
        # Migrate staff
        print("Migrating staff...")
        staff_count = 0
        for staff_id, staff_data in data_store.staff.items():
            staff = Staff(
                id=staff_id,
                username=staff_data.get('username', ''),
                display_name=staff_data.get('display_name', ''),
                account_type=staff_data.get('account_type', 'class'),
                is_active=staff_data.get('is_active', True)
            )
            db.session.add(staff)
            staff_count += 1
        
        # Commit all changes
        print("Committing changes to database...")
        db.session.commit()
        
        print(f"""
Migration completed successfully!

Migrated:
- {school_count} schools
- {provider_count} providers  
- {area_count} areas
- {route_count} routes
- {student_count} students
- {staff_count} staff

The Alice parent routes should now be properly separated:
- Alice Cooper's Parent
- Alice Rowe's Parent

All data is now stored persistently in PostgreSQL and will survive redeployments.
        """)
        
        # Verify Alice students are properly separated
        alice_students = Student.query.filter(Student.name.like('%Alice%')).all()
        print(f"\nAlice student verification:")
        for student in alice_students:
            route = Route.query.get(student.route_id) if student.route_id else None
            route_name = route.route_number if route else "No route"
            print(f"- {student.name} -> {route_name}")

if __name__ == '__main__':
    migrate_data()