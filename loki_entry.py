import sys
import os

# Ensure the application root is always importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.loki.cli import app

if __name__ == "__main__":
    app()
