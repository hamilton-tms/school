import os
from app import app
import routes  # Import routes to register them with Flask

if __name__ == "__main__":
    # Use debug=False for production safety
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
