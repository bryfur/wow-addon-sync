"""
Windows native implementation using Win32 API.

Uses pywin32 to directly access Windows Shell NotifyIcon APIs for native
system tray icon integration.
"""

from typing import Optional, Callable
import asyncio
from pathlib import Path
import threading

try:
    import win32gui
    import win32con
    import win32api
    import pywintypes
except ImportError:
    # Will fail gracefully if not on Windows
    pass

from ..constants import ICON_DIR


class WindowsTrayImpl:
    """Win32-based tray icon implementation for Windows."""
    
    # Window message constants
    WM_USER = 1024
    WM_TRAYICON = WM_USER + 20
    
    def __init__(self, on_show: Optional[Callable] = None,
                 on_quit: Optional[Callable] = None,
                 on_pull: Optional[Callable] = None,
                 on_push: Optional[Callable] = None,
                 on_toggle_monitor: Optional[Callable] = None):
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_pull = on_pull
        self.on_push = on_push
        self.on_toggle_monitor = on_toggle_monitor
        
        self.hwnd = None
        self.menu = None
        self.monitor_menu_id = None
        self.monitor_enabled = False
        self._pump_thread = None
        self._ready_event = threading.Event()
        
    async def setup(self):
        """Setup the tray icon using Windows Shell NotifyIcon."""
        # Use ICO file for Windows (supports multiple resolutions)
        icon_path = ICON_DIR / "icon.ico"
        if not icon_path.exists():
            raise RuntimeError(f"Icon not found: {icon_path}")
        
        # Run the tray in a separate thread with its own message pump
        self._pump_thread = threading.Thread(target=self._create_tray, args=(str(icon_path),), daemon=True)
        self._pump_thread.start()
        
        # Wait for the tray to be ready
        await asyncio.get_event_loop().run_in_executor(None, self._ready_event.wait)
        
        # Small delay to ensure everything is initialized
        await asyncio.sleep(0.2)
    
    def _create_tray(self, icon_path):
        """Create the tray icon (runs in separate thread)."""
        try:
            # Register window class
            wc = win32gui.WNDCLASS()
            wc.lpszClassName = "WoWSyncTrayIcon"
            wc.lpfnWndProc = self._wnd_proc
            wc.hInstance = win32api.GetModuleHandle(None)
            
            try:
                class_atom = win32gui.RegisterClass(wc)
            except pywintypes.error:
                # Class already registered
                class_atom = win32gui.WNDCLASS()
            
            # Create hidden window for message handling
            self.hwnd = win32gui.CreateWindow(
                "WoWSyncTrayIcon",
                "WoW Sync",
                0, 0, 0, 0, 0, 0, 0,
                wc.hInstance,
                None
            )
            
            # Load icon
            try:
                # Try to load as ICO file first
                hicon = win32gui.LoadImage(
                    0,
                    icon_path,
                    win32con.IMAGE_ICON,
                    0, 0,
                    win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
                )
            except:
                # Fallback to default icon
                hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            
            # Create system tray icon
            flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
            nid = (self.hwnd, 0, flags, self.WM_TRAYICON, hicon, "WoW Sync")
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
            
            # Signal that we're ready
            self._ready_event.set()
            
            # Message pump
            win32gui.PumpMessages()
            
        except Exception as e:
            print(f"Error creating tray icon: {e}")
            self._ready_event.set()  # Unblock even on error
    
    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        """Window procedure for handling messages."""
        if msg == self.WM_TRAYICON:
            if lparam == win32con.WM_RBUTTONUP:
                # Right-click - show menu
                self._show_menu()
            elif lparam == win32con.WM_LBUTTONDBLCLK:
                # Double-click - show window
                if self.on_show:
                    self.on_show()
            return 0
        elif msg == win32con.WM_COMMAND:
            # Menu item selected
            menu_id = win32api.LOWORD(wparam)
            self._handle_menu_command(menu_id)
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
    
    def _show_menu(self):
        """Show the context menu."""
        # Create popup menu
        menu = win32gui.CreatePopupMenu()
        
        # Add menu items (in reverse order for bottom-up display)
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1005, "Quit")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        
        # Toggle monitor item
        self.monitor_menu_id = 1004
        label = "Disable Auto-Sync" if self.monitor_enabled else "Enable Auto-Sync"
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.monitor_menu_id, label)
        
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1003, "Push to Remote")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1002, "Pull from Remote")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1001, "Show Window")
        
        # Get cursor position
        pos = win32gui.GetCursorPos()
        
        # Required for the menu to close when clicking outside
        win32gui.SetForegroundWindow(self.hwnd)
        
        # Show menu
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_BOTTOMALIGN,
            pos[0], pos[1],
            0,
            self.hwnd,
            None
        )
        
        # Clean up
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)
    
    def _handle_menu_command(self, menu_id):
        """Handle menu item selection."""
        if menu_id == 1001:  # Show Window
            if self.on_show:
                self.on_show()
        elif menu_id == 1002:  # Pull from Remote
            if self.on_pull:
                self.on_pull()
        elif menu_id == 1003:  # Push to Remote
            if self.on_push:
                self.on_push()
        elif menu_id == 1004:  # Toggle Monitor
            if self.on_toggle_monitor:
                self.on_toggle_monitor()
        elif menu_id == 1005:  # Quit
            if self.on_quit:
                self.on_quit()
    
    def update_monitor_menu(self, is_enabled: bool):
        """Update the auto-sync menu item label."""
        self.monitor_enabled = is_enabled
        # Menu is recreated each time, so this just updates the state
    
    def cleanup(self):
        """Cleanup tray icon."""
        if self.hwnd:
            try:
                # Remove tray icon
                nid = (self.hwnd, 0)
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
                
                # Destroy window
                win32gui.DestroyWindow(self.hwnd)
            except:
                pass
