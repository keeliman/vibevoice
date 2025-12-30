"""Main entry point for running vibevoice as a module"""

import sys
import os

# Fix sys.path for PyInstaller bundle and different execution contexts
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    resource_path = os.path.join(sys._MEIPASS, 'Resources')
    if resource_path not in sys.path:
        sys.path.insert(0, resource_path)
    # Use absolute imports for PyInstaller
    from vibevoice.cli import main
else:
    # Normal Python execution - use relative imports
    try:
        from .cli import main
    except ImportError:
        # Fallback to absolute imports
        from vibevoice.cli import main

if __name__ == "__main__":
    main()
