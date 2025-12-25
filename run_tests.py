"""
Test runner that writes results to file
"""
import sys
import pytest
from datetime import datetime

# Run tests and capture output
log_file = f"test_results_{datetime.now().strftime('%H%M%S')}.txt"

with open(log_file, 'w', encoding='utf-8') as f:
    # Redirect stdout
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = f
    sys.stderr = f
    
    try:
        print("="*70)
        print(f"Test Run: {datetime.now()}")
        print("="*70)
        print()
        
        # Run tests
        exit_code = pytest.main([
            'tests/test_doubles_battle_tag.py',
            'tests/test_doubles_team_preview.py',
            '-v',
            '--tb=short'
        ])
        
        print()
        print("="*70)
        print(f"Tests completed with exit code: {exit_code}")
        print("="*70)
        
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

print(f"Test results written to: {log_file}")

