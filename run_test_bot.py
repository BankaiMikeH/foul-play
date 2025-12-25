#!/usr/bin/env python
"""
Simple bot runner for testing - runs bot with hardcoded settings
Writes all output to a log file
"""
import sys
import os
from datetime import datetime

def main():
    # Create log file
    bot_name = sys.argv[1] if len(sys.argv) > 1 else "TestBot"
    log_path = f"test_bot_{bot_name}_{datetime.now().strftime('%H%M%S')}.log"
    
    with open(log_path, 'w', encoding='utf-8', buffering=1) as log:
        # Redirect output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log
        sys.stderr = log
        
        try:
            print(f"Starting {bot_name} at {datetime.now()}")
            print("="*60)
            
            # Configure arguments based on bot type
            if "Bot1" in bot_name:
                args = [
                    "--websocket-uri", "ws://localhost:8000/showdown/websocket",
                    "--ps-username", bot_name,
                    "--ps-password", "testpass",
                    "--bot-mode", "challenge_user",
                    "--user-to-challenge", "VGCTestBot2",
                    "--pokemon-format", "gen9vgc2026regf",
                    "--run-count", "1",
                    "--log-level", "DEBUG"
                ]
            else:
                args = [
                    "--websocket-uri", "ws://localhost:8000/showdown/websocket",
                    "--ps-username", bot_name,
                    "--ps-password", "testpass",
                    "--bot-mode", "accept_challenge",
                    "--pokemon-format", "gen9vgc2026regf",
                    "--room-name", "lobby",
                    "--run-count", "1",
                    "--log-level", "DEBUG"
                ]
            
            sys.argv = ["run.py"] + args
            print(f"Arguments: {' '.join(sys.argv)}\n")
            
            # Now import and run
            print("Importing modules...")
            from run import run_foul_play
            import asyncio
            
            print("Starting bot...\n")
            asyncio.run(run_foul_play())
            
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            print(f"Log saved to: {log_path}")

if __name__ == "__main__":
    main()

