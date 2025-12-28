#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox
from async_tkinter_loop import async_mainloop
from wow_sync.ui.main_window import MainWindow
from wow_sync.single_instance import SingleInstance


def main():
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
