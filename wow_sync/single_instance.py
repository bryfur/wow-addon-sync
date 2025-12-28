"""Single instance enforcement for WoW Sync."""

import sys
import os
from pathlib import Path
from .constants import LOCK_FILE, WOW_SYNC_DIR


class SingleInstance:
    """Ensures only one instance of the application runs at a time."""
    
    def __init__(self):
        self.lock_file = None
        self.fd = None
        
    def acquire(self):
        """Acquire the single instance lock. Returns True if successful, False if another instance is running."""
        # Ensure the directory exists
        WOW_SYNC_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            if sys.platform == 'win32':
                # Windows: try to open file exclusively
                import msvcrt
                self.fd = os.open(str(LOCK_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC)
                # Write PID to lock file
                os.write(self.fd, str(os.getpid()).encode())
                return True
            else:
                # Unix/Linux/macOS: use fcntl
                import fcntl
                self.fd = os.open(str(LOCK_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                try:
                    fcntl.lockf(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Write PID to lock file
                    os.write(self.fd, str(os.getpid()).encode())
                    return True
                except (IOError, OSError):
                    os.close(self.fd)
                    self.fd = None
                    return False
        except (IOError, OSError, FileExistsError):
            return False
    
    def release(self):
        """Release the single instance lock."""
        if self.fd is not None:
            try:
                if sys.platform != 'win32':
                    import fcntl
                    fcntl.lockf(self.fd, fcntl.LOCK_UN)
                os.close(self.fd)
                self.fd = None
            except:
                pass
        
        # Clean up lock file
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
        except:
            pass
    
    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("Another instance of WoW Sync is already running")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
