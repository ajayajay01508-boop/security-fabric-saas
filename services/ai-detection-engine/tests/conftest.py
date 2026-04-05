"""
Shared pytest configuration for service tests.
Ensures the service root is on sys.path so imports work correctly.
"""
import sys
import os

# Add the service root to path so 'from worker import ...' etc. work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
