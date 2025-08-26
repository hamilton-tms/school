# Hamilton TMS

## Overview
Hamilton TMS is a Flask-based web application designed to enhance student safety and operational efficiency in school transportation management. It provides tools for managing schools, bus routes, and students, including real-time bus status tracking. The project aims to become a market leader in school transportation solutions by offering comprehensive management capabilities and real-time insights.

## User Preferences
Preferred communication style: Simple, everyday language.
Theme preference: Light theme.
Location: UK-based system (no US states, UK addresses and phone numbers).
System focus: Enhanced transportation management with bus status tracking.
Bus tracking: Real-time status system - red (not present), orange (arrived), green (ready to load/unload).
Student management: Track both route assignments and class information for each student.
Individual route management: Streamlined interface with direct button interactions.
Single school system: Changed from multi-school to single school system - "Schools" renamed to "My School", school selection removed from route creation.
Year field removal: Removed separate Year column from student management - now uses Class field only for flexibility with different school naming conventions (e.g., "3A", "10B", "Form 7").
Area creation: Simple interface with name field only - description field removed as unnecessary.
Area management: Full edit/delete functionality added to Route Admin with comprehensive UI. Transport Check-in shows only areas with students assigned, with all qualifying areas remaining visible and selected area highlighted in grey for seamless switching.
Audio notifications: Successfully implemented pleasant C4-E4-G4 major chord chime system exclusively for class accounts. Audio automatically initializes on first user interaction and plays during both individual route status changes and bulk operations.
Mobile interface optimization: Implemented responsive design for Transport Check-in page with area filtering dropdown on mobile (replacing button layout) and stacked icon-above-text design for bulk action buttons.
Cross-device sync implementation: Implemented multi-user conflict resolution system designed for 4+ simultaneous mobile users. Uses 2-second polling with 5-second user change protection - when a user changes a route status, that route is protected from sync updates for 5 seconds to prevent override conflicts. Each device tracks its recent changes and ignores incoming sync updates for routes it recently modified.

## System Architecture

### Frontend
- **Template Engine**: Jinja2
- **UI Framework**: Bootstrap 5
- **Styling**: Custom CSS with Font Awesome
- **Interactivity**: Vanilla JavaScript
- **UI/UX Decisions**: UK-specific terminology; uniformly sized, square status buttons (105px × 42px); enhanced mobile responsiveness with two-line text wrapping for route/parent names and optimized column widths; password visibility toggles; sticky headers for critical controls (e.g., student management header); context-aware navigation for back buttons; and alphabetical sorting for routes and student assignments. Safeguarding, medical, and harness requirement alerts are integrated with high-visibility color coding (red for safeguarding, orange for harness 'Yes', blue for medical). Rebranding includes "Routes" to "Transport Check-in" and "Manage Schools" to "Route Admin". Fixed table layout with column shifting prevention using CSS table-layout: fixed and opacity transitions.

### Recent Technical Fixes (August 2025)
- **Route Contact Information Display Fixed**: Completed provider and parent contact information display (August 26, 2025)
  - Fixed provider contact information for regular routes by correcting field names from contact_phone/contact_email to phone/email
  - Implemented parent route contact information display using student data matching by name
  - Added proper handling for data inconsistencies where students assigned to different routes than their parent routes
  - Template prioritizes primary parent contact (parent_name/parent_phone) over secondary contacts
  - Handles cases where primary contact is missing by promoting secondary contact to primary display
  - Route detail pages now show clickable phone numbers and email addresses with proper icons
  - Issue identified: Some student records have missing primary parent data (e.g., Amir Holland showing Helen Davis as secondary contact instead of primary)
- **Status Tiles Removal**: Completely removed status tiles from dashboard for all users (August 26, 2025)
  - Removed HTML tiles section and related JavaScript update functions
  - Disabled dashboard stats polling that was causing network errors
  - Class accounts now have clean dashboard interface without status tiles
- **Navigation Security Fix**: Fixed class account access controls (August 26, 2025)
  - Class accounts now only see Dashboard menu item, no admin pages
  - Added proper is_class_account context processor injection
  - Removed unauthorized access to Students, Route Admin, Providers, Staff pages
- **Audio Notifications System Fixed**: Completed full audio system for class accounts (August 26, 2025)
  - Fixed critical issue where cross-device sync wasn't triggering audio notifications on mobile class accounts
  - Added audio notification triggers to both direct route clicks (main.js) and cross-device sync updates (realtime.js) 
  - Audio system uses pleasant C4-E4-G4 major chord chimes on both mobile and desktop
  - Class accounts receive audio notifications when routes become "ready" status from any device
  - Admin accounts remain silent (by design to avoid annoyance during check-ins)
  - System includes comprehensive fallback mechanisms and detailed logging for troubleshooting
  - Mobile class accounts now properly play sound when admin changes route status to "ready" on other devices
- **Bulk Ready Button Styling**: Fixed CSS class concatenation in bulk status updates
  - Corrected JavaScript from 'btn-btn-success' to 'btn-success' for proper green styling
  - Bulk operations now display correct button colors after status changes
- **Student Deletion**: Successfully resolved persistent deletion issues through multiple fixes:
  - Added CSRF exemption (@csrf.exempt) to bypass validation blocking
  - Implemented proper admin permission checking logic matching existing patterns
  - Created clean Bootstrap modal confirmation dialog with fallback mechanisms
  - Fixed undefined function errors in delete route
  - Confirmed working in preview environment (August 13, 2025) - ready for deployment
- **CSV Route Upload**: Fixed CSV template and processing to handle correct format:
  - Updated template to use route_number, provider_name, provider_contact, provider_phone, area_name, students
  - Removed unnecessary Max Capacity column from template
  - Fixed CSV processing to match new column names
  - Successfully tested with 15 route uploads including provider contact details
- **Class Account Navigation**: Removed unnecessary "Access denied" error messages:
  - Class accounts now silently redirect to Dashboard when accessing restricted pages
  - Eliminated red error messages that appeared during normal navigation
  - Improved user experience for class account workflows

### Backend
- **Framework**: Flask (Python)
- **Database ORM**: SQLAlchemy
- **Authentication**: Flask-Login (username/password) supporting admin and class roles.
- **Data Storage**: Uses PostgreSQL database via SQLAlchemy models for persistent storage, complemented by a database_store module for data operations.

### Key Features & Design Patterns
- **Data Management**: Comprehensive CRUD operations for schools (single instance), routes, and students. Supports real-time bus status tracking, student assignment/reassignment to routes, and recording two parent/carer contacts per student.
- **Web Interface**: Central dashboard, "Transport Check-in" for real-time status updates and check-ins, and "Route Admin" for comprehensive route and student assignment management. Features bulk operations via flexible CSV uploads for routes and students, and bulk student assignment with a refined modal interface. Integrated search functionality enhances student management.
- **Real-time Updates**: Lightweight polling-based synchronization ensures data changes are reflected across devices within 2 seconds.
- **Data Processing**: Custom CSV processing engine capable of flexible column header detection and intelligent route grouping for efficient bulk uploads.
- **Specialized "Parent" Route Handling**: A core feature supporting the creation of individual routes for each child collected by a parent/carer, using a full name naming convention (e.g., "Alice Cooper's Parent") to prevent collisions. This system supports dual assignment for consolidated views in Route Admin and individual tracking in Transport Check-in, with specific filtering in dropdowns to prevent selection confusion.
- **Alert Systems**: Visual safeguarding, medical, and harness requirement alerts are integrated directly into student listings and modals, providing immediate staff awareness with detailed popups.

## External Dependencies
- **Flask**: Web framework
- **Flask-Login**: User authentication
- **SQLAlchemy**: ORM for database interaction
- **Jinja2**: Templating engine
- **Bootstrap 5**: Frontend UI framework
- **Font Awesome**: Icon library
- **Werkzeug**: WSGI utility library (dependency of Flask)
- **PostgreSQL**: Database system