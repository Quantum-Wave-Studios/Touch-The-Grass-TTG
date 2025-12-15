import sys
import os
import traceback

def log_exception(exc_type, exc_value, exc_traceback):
    # Get the current directory where the exe is running
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
    log_path = os.path.join(exe_dir, 'error.log')
    
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("=== Python Error Log ===\n")
        f.write(f"Python version: {sys.version}\n")
        f.write(f"Executable: {sys.executable}\n")
        f.write(f"Current directory: {os.getcwd()}\n")
        f.write(f"sys.path: {sys.path}\n\n")
        f.write("=== Exception Details ===\n")
        
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        
        # Also print to console
        print(f"\nAn error occurred. Check {log_path} for details.", file=sys.stderr)

# Install the exception handler
sys.excepthook = log_exception

# Set up proper environment for frozen executables
if getattr(sys, 'frozen', False):
    # Get the directory containing the executable
    exe_dir = os.path.dirname(sys.executable)
    
    # Add the assets directory to the path
    assets_dir = os.path.join(exe_dir, 'assets')
    if os.path.exists(assets_dir):
        print(f"Assets directory found: {assets_dir}")
    else:
        print(f"Warning: Assets directory not found at {assets_dir}")
    
    # Print diagnostic information
    print(f"Executable directory: {exe_dir}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"sys.path: {sys.path}")
    
    # Keep console window open if there's an error
    def pause_on_error():
        if sys.stderr.isatty():
            input("\nPress Enter to exit...")