"""Direct test of bot - simplified for debugging"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("="*60)
print("DIRECT BOT TEST")
print("="*60)

# Set command line args
sys.argv = [
    "run.py",
    "--websocket-uri", "ws://localhost:8000/showdown/websocket",
    "--ps-username", "DirectTestBot",
    "--ps-password", "testpass",
    "--bot-mode", "challenge_user",
    "--user-to-challenge", "bankaimike",
    "--pokemon-format", "gen9vgc2026regf",
    "--run-count", "1",
    "--log-level", "DEBUG"
]

print(f"Arguments: {sys.argv}")
print("="*60)
print()

try:
    # Import and run
    import run
    print("\nImport successful, attempting to run...")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

