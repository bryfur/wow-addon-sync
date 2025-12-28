"""
System tray integration for WoW Sync.

This module provides system tray functionality with native platform implementations:
1. macOS - PyObjC NSStatusBar (native macOS menu bar integration)
2. Windows - Win32 Shell NotifyIcon API (native Windows system tray)
3. Linux - D-Bus StatusNotifier protocol (Linux system tray standard)

Each implementation provides native OS integration for the best user experience.
"""

from typing import Optional, Callable, Any
import asyncio
import sys
from threading import Thread


class TrayIcon:
    """Unified tray icon interface."""
    
    def __init__(self, on_show: Optional[Callable] = None, 
                 on_quit: Optional[Callable] = None,
                 on_pull: Optional[Callable] = None,
                 on_push: Optional[Callable] = None,
                 on_toggle_monitor: Optional[Callable] = None,
                 tkinter_root: Optional[Any] = None):
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_pull = on_pull
        self.on_push = on_push
        self.on_toggle_monitor = on_toggle_monitor
        self.tkinter_root = tkinter_root
        self._impl = None
        self._impl_type = None
        
    async def setup(self):
        """Setup tray icon with platform-specific implementations."""
        
        # macOS: Use PyObjC (native macOS status bar)
        if sys.platform == 'darwin':
            try:
                from .tray_macos import MacOSTrayImpl
                self._impl = MacOSTrayImpl(
                    self.on_show, self.on_quit, self.on_pull,
                    self.on_push, self.on_toggle_monitor
                )
                await self._impl.setup()
                self._impl_type = "macos"
                return True, "System tray enabled (macOS native)"
            except Exception as e:
                return False, f"System tray not available on macOS: {e}"
        
        # Windows: Use Win32 API (native Windows tray)
        if sys.platform == 'win32':
            try:
                from .tray_windows import WindowsTrayImpl
                self._impl = WindowsTrayImpl(
                    self.on_show, self.on_quit, self.on_pull,
                    self.on_push, self.on_toggle_monitor,
                    self.tkinter_root
                )
                await self._impl.setup()
                self._impl_type = "windows"
                return True, "System tray enabled (Windows native)"
            except Exception as e:
                return False, f"System tray not available on Windows: {e}"
        
        # Linux: Use D-Bus StatusNotifier
        if sys.platform.startswith('linux'):
            try:
                from .tray_linux import DBusTrayImpl
                self._impl = DBusTrayImpl(
                    self.on_show, self.on_quit, self.on_pull,
                    self.on_push, self.on_toggle_monitor
                )
                await self._impl.setup()
                self._impl_type = "linux"
                return True, "System tray enabled (Linux D-Bus StatusNotifier)"
            except Exception as e:
                return False, f"System tray not available: {e}"
        
        return False, "System tray not supported on this platform"
    
    def update_monitor_menu(self, is_enabled: bool):
        """Update the auto-sync menu item."""
        if self._impl and hasattr(self._impl, 'update_monitor_menu'):
            self._impl.update_monitor_menu(is_enabled)
    
    async def cleanup(self):
        """Cleanup tray resources."""
        if self._impl:
            try:
                if asyncio.iscoroutinefunction(self._impl.cleanup):
                    await self._impl.cleanup()
                else:
                    self._impl.cleanup()
            except:
                pass


__all__ = ['TrayIcon']
