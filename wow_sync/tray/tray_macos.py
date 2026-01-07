"""
macOS native implementation using PyObjC.

Uses PyObjC to directly access macOS NSStatusBar APIs for native
status bar icon integration.
"""

from typing import Optional, Callable
import asyncio
from pathlib import Path
import objc
from Foundation import NSObject
from AppKit import (
    NSStatusBar, NSVariableStatusItemLength, NSImage,
    NSMenu, NSMenuItem, NSApp, NSApplication
)
from ..constants import ICON_DIR


class StatusBarDelegate(NSObject):
    """Delegate for handling menu item clicks."""
    
    def initWithCallbacks_(self, callbacks):
        """Initialize with callback dictionary."""
        self = objc.super(StatusBarDelegate, self).init()
        if self is None:
            return None
        self.callbacks = callbacks
        return self
    
    def handleShow_(self, sender):
        """Handle show window menu item."""
        if self.callbacks.get('show'):
            self.callbacks['show']()
    
    def handlePull_(self, sender):
        """Handle pull menu item."""
        if self.callbacks.get('pull'):
            self.callbacks['pull']()
    
    def handlePush_(self, sender):
        """Handle push menu item."""
        if self.callbacks.get('push'):
            self.callbacks['push']()
    
    def handleToggleMonitor_(self, sender):
        """Handle toggle monitor menu item."""
        if self.callbacks.get('toggle_monitor'):
            self.callbacks['toggle_monitor']()
    
    def handleQuit_(self, sender):
        """Handle quit menu item."""
        if self.callbacks.get('quit'):
            self.callbacks['quit']()


class StatusBarController(NSObject):
    """Controller for managing the status bar item."""
    
    def initWithIconPath_andCallbacks_(self, icon_path, callbacks):
        """Initialize with icon path and callbacks."""
        self = objc.super(StatusBarController, self).init()
        if self is None:
            return None
        
        self.icon_path = icon_path
        self.callbacks = callbacks
        self.status_item = None
        self.delegate = None
        self.monitor_menu_item = None  # Track the toggle monitor menu item
        
        return self
    
    def setupStatusBar(self):
        """Setup the status bar (must be called on main thread)."""
        try:
            # Create status bar item
            status_bar = NSStatusBar.systemStatusBar()
            self.status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)
            
            # Load and set icon
            image = NSImage.alloc().initWithContentsOfFile_(self.icon_path)
            if image:
                # Resize to appropriate size for status bar
                image.setSize_((18, 18))
                image.setTemplate_(True)  # Makes it adapt to dark/light mode
                self.status_item.button().setImage_(image)
            
            # Create delegate with callbacks
            self.delegate = StatusBarDelegate.alloc().initWithCallbacks_(self.callbacks)
            
            # Create menu
            menu = NSMenu.alloc().init()
            
            # Show Window
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Show Window", objc.selector(self.delegate.handleShow_, signature=b'v@:@'), ""
            )
            item.setTarget_(self.delegate)
            menu.addItem_(item)
            
            # Separator
            menu.addItem_(NSMenuItem.separatorItem())
            
            # Pull from Remote
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Pull from Remote", objc.selector(self.delegate.handlePull_, signature=b'v@:@'), ""
            )
            item.setTarget_(self.delegate)
            menu.addItem_(item)
            
            # Push to Remote
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Push to Remote", objc.selector(self.delegate.handlePush_, signature=b'v@:@'), ""
            )
            item.setTarget_(self.delegate)
            menu.addItem_(item)
            
            # Separator
            menu.addItem_(NSMenuItem.separatorItem())
            
            # Toggle Monitor (Auto-Sync)
            self.monitor_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Enable Auto-Sync", objc.selector(self.delegate.handleToggleMonitor_, signature=b'v@:@'), ""
            )
            self.monitor_menu_item.setTarget_(self.delegate)
            menu.addItem_(self.monitor_menu_item)
            
            # Separator
            menu.addItem_(NSMenuItem.separatorItem())
            
            # Quit
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Quit", objc.selector(self.delegate.handleQuit_, signature=b'v@:@'), ""
            )
            item.setTarget_(self.delegate)
            menu.addItem_(item)
            
            # Set the menu
            self.status_item.setMenu_(menu)
            
            return True
        except Exception as e:
            print(f"Error in setupStatusBar: {e}")
            return False
    
    def updateMonitorMenuTitle_(self, title):
        """Update the monitor menu item title (must be called on main thread)."""
        if self.monitor_menu_item:
            self.monitor_menu_item.setTitle_(title)
    
    def cleanup(self):
        """Cleanup status bar item."""
        if self.status_item:
            try:
                status_bar = NSStatusBar.systemStatusBar()
                status_bar.removeStatusItem_(self.status_item)
                self.status_item = None
            except:
                pass


class MacOSTrayImpl:
    """PyObjC-based tray icon implementation for macOS."""
    
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
        self.controller = None
        
    async def setup(self):
        """Setup the tray icon using macOS NSStatusBar."""
        # Use ICNS file for macOS (supports multiple resolutions and retina displays)
        icon_path = ICON_DIR / "icon.icns"
        # Fallback to PNG if ICNS not available
        if not icon_path.exists():
            icon_path = ICON_DIR / "icon.png"
        if not icon_path.exists():
            raise RuntimeError(f"Icon not found: {icon_path}")
        
        # Create callbacks dictionary
        callbacks = {
            'show': self.on_show,
            'pull': self.on_pull,
            'push': self.on_push,
            'toggle_monitor': self.on_toggle_monitor,
            'quit': self.on_quit,
        }
        
        # Create controller
        self.controller = StatusBarController.alloc().initWithIconPath_andCallbacks_(
            str(icon_path), callbacks
        )
        
        # Setup status bar directly
        # This is called from async_mainloop which runs on the main thread,
        # satisfying AppKit's requirement for UI operations on the main thread.
        # Callbacks are already wrapped with root.after() for thread safety.
        success = self.controller.setupStatusBar()
        
        if not success:
            raise RuntimeError("Failed to setup status bar")
        
        # Small delay to ensure the menu is fully initialized
        await asyncio.sleep(0.1)
    
    def update_monitor_menu(self, is_enabled: bool):
        """Update the auto-sync menu item label."""
        if self.controller and self.controller.monitor_menu_item:
            label = "Disable Auto-Sync" if is_enabled else "Enable Auto-Sync"
            # Update directly - called from MainWindow which is on the main thread
            self.controller.updateMonitorMenuTitle_(label)
    
    def cleanup(self):
        """Cleanup tray icon."""
        if self.controller:
            try:
                self.controller.cleanup()
            except:
                pass
