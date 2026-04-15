# main.py

import sys
import os

# Add the project root to the Python path before any other imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import main

if __name__ == "__main__":
    main()
