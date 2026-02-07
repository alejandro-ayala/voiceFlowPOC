#!/usr/bin/env python3
"""
VoiceFlow PoC Web UI Runner
Simple script to run the web interface with proper environment setup.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project directory to Python path
# Since this script is in presentation/, go up one level to project root
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

def setup_environment():
    """Set up environment variables for development."""
    # Set default environment variables if not already set
    env_vars = {
        'ENVIRONMENT': 'development',
        'DEBUG': 'true',
        'HOST': '127.0.0.1',
        'PORT': '8000',
        'LOG_LEVEL': 'info',
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
    
    # Load .env file if it exists
    env_file = project_dir / '.env'
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def check_dependencies():
    """Check if required dependencies are installed."""
    required_imports = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('python-multipart', 'multipart'),
        ('jinja2', 'jinja2'),
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_imports:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("ERROR: Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall them with:")
        print(f"   pip install {' '.join(missing_packages)}")
        print("\nOr install all UI requirements:")
        print(f"   pip install -r {project_dir}/requirements-ui.txt")
        return False
    
    print("All required packages are installed")
    return True

def main():
    parser = argparse.ArgumentParser(
        description="VoiceFlow PoC Web UI Development Server"
    )
    parser.add_argument(
        '--host', 
        default=os.environ.get('HOST', '127.0.0.1'),
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port', 
        type=int,
        default=int(os.environ.get('PORT', '8000')),
        help='Port to bind to (default: 8000)'
    )
    parser.add_argument(
        '--reload', 
        action='store_true',
        default=os.environ.get('DEBUG', 'false').lower() == 'true',
        help='Enable auto-reload for development'
    )
    parser.add_argument(
        '--log-level',
        default=os.environ.get('LOG_LEVEL', 'info'),
        choices=['critical', 'error', 'warning', 'info', 'debug'],
        help='Log level (default: info)'
    )
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Check dependencies and exit'
    )
    
    args = parser.parse_args()
    
    # Set up environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    if args.check_deps:
        print("All dependencies are satisfied")
        sys.exit(0)
    
    print("""
VoiceFlow PoC Web UI
========================""")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print(f"Debug Mode: {os.environ.get('DEBUG', 'false')}")
    print(f"Server URL: http://{args.host}:{args.port}")
    print(f"API Docs: http://{args.host}:{args.port}/api/docs")
    print(f"Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    print("========================\n")
    
    try:
        # Import and run the FastAPI app
        from presentation.fastapi_factory import main as app_main
        
        # Override environment variables with command line args
        os.environ['HOST'] = args.host
        os.environ['PORT'] = str(args.port)
        os.environ['LOG_LEVEL'] = args.log_level
        if args.reload:
            os.environ['RELOAD'] = 'true'
        
        # Run the application
        app_main()
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"\nFailed to start server: {e}")
        if os.environ.get('DEBUG', 'false').lower() == 'true':
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
