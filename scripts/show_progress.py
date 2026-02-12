"""Script to show progress of initial load in real-time."""

import sys
import time
from pathlib import Path

# Path to terminal output file
TERMINAL_FILE = Path(__file__).parent.parent / ".cursor" / "projects" / "c-Users-parap-PycharmProjects-auto-parser-back-and-load" / "terminals" / "697811.txt"

# Alternative: read from logs
LOG_FILE = Path(__file__).parent.parent / "logs" / "app.log"


def get_last_progress_line(file_path: Path) -> str:
    """Get last progress line from file."""
    try:
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Look for progress line (contains "Page" and "Records loaded")
        for line in reversed(lines):
            if "Page" in line and "Records loaded" in line:
                return line.strip()
        
        # If no progress line, return last line
        if lines:
            return lines[-1].strip()
        
        return None
    except Exception:
        return None


def main():
    """Show progress in real-time."""
    print("Monitoring progress... (Press Ctrl+C to stop)")
    print("-" * 80)
    
    last_line = None
    
    try:
        while True:
            # Try terminal file first
            progress = get_last_progress_line(TERMINAL_FILE)
            
            # If not found, try log file
            if not progress:
                progress = get_last_progress_line(LOG_FILE)
            
            if progress and progress != last_line:
                # Extract progress info
                if "Page" in progress and "Records loaded" in progress:
                    # Clear line and print new progress
                    sys.stdout.write('\r' + ' ' * 80 + '\r')  # Clear line
                    sys.stdout.write(f"[PROGRESS] {progress}")
                    sys.stdout.flush()
                    last_line = progress
                else:
                    # Show other important messages
                    if any(keyword in progress for keyword in ["ERROR", "WARNING", "completed"]):
                        print(f"\n{progress}")
            
            time.sleep(1)  # Update every second
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


if __name__ == "__main__":
    main()
