#!/usr/bin/env python3
import sys
import tkinter as tk
from tkinter import messagebox
from async_tkinter_loop import async_mainloop
from wow_sync.ui.main_window import MainWindow
from wow_sync.single_instance import SingleInstance


def enable_dpi_awareness():
    """Enable DPI awareness on Windows to prevent blurry UI."""
    if sys.platform == 'win32':
        try:
            import ctypes
            
            # Define DPI awareness constants
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
            PROCESS_PER_MONITOR_DPI_AWARE = 2
            
            try:
                # Try the newest API first (Windows 10 1703+)
                ctypes.windll.user32.SetProcessDpiAwarenessContext(
                    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
                )
            except (AttributeError, OSError):
                # Fall back to SetProcessDpiAwareness (Windows 8.1+)
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
                except (AttributeError, OSError):
                    # Final fallback to SetProcessDPIAware (Windows Vista+)
                    try:
                        ctypes.windll.user32.SetProcessDPIAware()
                    except (AttributeError, OSError):
                        pass  # DPI awareness not available
        except Exception:
            pass  # Silently fail if DPI awareness cannot be set


def main():
    # Enable DPI awareness before creating any windows
    enable_dpi_awareness()
    # Enforce single instance
    instance_lock = SingleInstance()
    if not instance_lock.acquire():
        # Show error dialog - another instance is running
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        messagebox.showerror(
            "WoW Sync Already Running",
            "Another instance of WoW Sync is already running.\n\n"
            "Please check your system tray or close the existing instance first."
        )
        root.destroy()
        return
    
    try:
        root = tk.Tk()
        app = MainWindow(root)
        async_mainloop(root)
    finally:
        # Release lock when application exits
        instance_lock.release()


if __name__ == "__main__":
    main()
