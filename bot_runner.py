"""
Bot runner with explicit file logging for debugging
"""
import asyncio
import sys
import os
from datetime import datetime

# Redirect all output to file
log_file = open(f"bot_runner_{datetime.now().strftime('%H%M%S')}.log", "w", encoding="utf-8", buffering=1)
sys.stdout = log_file
sys.stderr = log_file

print("="*60)
print(f"Bot Runner Started: {datetime.now()}")
print("="*60)

try:
    # Set arguments
    sys.argv = [
        "run.py",
        "--websocket-uri", "ws://localhost:8000/showdown/websocket",
        "--ps-username", sys.argv[1] if len(sys.argv) > 1 else "TestBot",
        "--ps-password", "testpass",
        "--bot-mode", sys.argv[2] if len(sys.argv) > 2 else "accept_challenge",
        "--pokemon-format", "gen9vgc2026regf",
        "--run-count", "1",
        "--log-level", "INFO"
    ]
    
    if sys.argv[2] == "challenge_user":
        sys.argv.extend(["--user-to-challenge", sys.argv[3] if len(sys.argv) > 3 else "TestBot2"])
    else:
        sys.argv.extend(["--room-name", "lobby"])
    
    print(f"\nArguments: {sys.argv}\n")
    
    # Import run
    import run as run_module
    print("Import successful\n")
    
    # This will call asyncio.run(run_foul_play())
    print("Starting bot...\n")
    
except Exception as e:
    print(f"\n{'='*60}")
    print(f"ERROR: {e}")
    print("="*60)
    import traceback
    traceback.print_exc()
finally:
    log_file.close()

