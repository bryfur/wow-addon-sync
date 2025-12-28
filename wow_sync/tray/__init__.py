"""
System tray integration for WoW Sync.

This module provides system tray functionality with two implementations:
1. tray_manager (preferred) - Cross-platform library with native support
2. dbus (fallback, Linux only) - D-Bus StatusNotifier protocol for Linux systems

Why two implementations?
- tray_manager provides the best user experience with native OS integration
- D-Bus is a fallback specifically for Linux systems where tray_manager may not be available
- D-Bus StatusNotifier is Linux-specific and not used on Windows/macOS
- This ensures tray functionality works across different environments
"""

from typing import Optional, Callable
import asyncio
import sys
from threading import Thread


class TrayIcon:
    """Unified tray icon interface."""
    
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
        self._impl = None
        self._impl_type = None
        
    async def setup(self):
        """Setup tray icon, trying tray_manager first, then D-Bus (Linux only)."""
        # Try tray_manager first (preferred implementation)
        try:
            from .tray_manager_impl import TrayManagerImpl
            self._impl = TrayManagerImpl(
                self.on_show, self.on_quit, self.on_pull, 
                self.on_push, self.on_toggle_monitor
            )
            await self._impl.setup()
            self._impl_type = "tray_manager"
            return True, "System tray enabled (tray_manager)"
        except Exception as e:
            # Fallback to D-Bus StatusNotifier (Linux only)
            if sys.platform.startswith('linux'):
                try:
                    from .tray_dbus import DBusTrayImpl
                    self._impl = DBusTrayImpl(
                        self.on_show, self.on_quit, self.on_pull,
                        self.on_push, self.on_toggle_monitor
                    )
                    await self._impl.setup()
                    self._impl_type = "dbus"
                    return True, "System tray enabled (D-Bus StatusNotifier)"
                except Exception as e2:
                    return False, f"System tray not available: {e}, {e2}"
            else:
                return False, f"System tray not available: {e}"
    
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
