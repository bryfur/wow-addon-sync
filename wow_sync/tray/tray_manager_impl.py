"""
TrayManager implementation (preferred).

Uses the tray_manager library which provides native system tray integration
across Windows, macOS, and Linux with proper menu support and click handlers.
This is the preferred implementation when the library is available.
"""

from typing import Optional, Callable
from tray_manager import TrayManager, Button, OsSupport
from ..constants import ICON_DIR


class TrayManagerImpl:
    """TrayManager-based tray icon implementation."""
    
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
        self.tray_icon = None
        self.monitor_button = None
        self.pull_button = None
        self.push_button = None
        
    async def setup(self):
        """Setup the tray icon using tray_manager."""
        if not OsSupport.SUPPORT_MENU:
            raise RuntimeError("tray_manager menus not supported on this platform")
        
        icon_path = ICON_DIR / "icon.png"
        if not icon_path.exists():
            raise RuntimeError(f"Icon not found: {icon_path}")
        
        self.tray_icon = TrayManager("WoW Sync", run_in_separate_thread=True)
        self.tray_icon.load_icon(str(icon_path), "app_icon")
        self.tray_icon.set_icon("app_icon")
        
        # Check if platform supports default buttons
        use_default = OsSupport.SUPPORT_DEFAULT if hasattr(OsSupport, 'SUPPORT_DEFAULT') else False
        
        show_button = Button("Show Window", self.on_show, default=use_default)
        self.pull_button = Button("Pull from Remote", self.on_pull)
        self.push_button = Button("Push to Remote", self.on_push)
        self.monitor_button = Button("Enable Auto-Sync", self.on_toggle_monitor)
        quit_button = Button("Quit Application", self.on_quit)
        
        menu = self.tray_icon.menu
        if menu:
            menu.add(show_button)
            menu.add_separator()
            menu.add(self.pull_button)
            menu.add(self.push_button)
            menu.add_separator()
            menu.add(self.monitor_button)
            menu.add_separator()
            menu.add(quit_button)
    
    def update_monitor_menu(self, is_enabled: bool):
        """Update the auto-sync menu item label."""
        if self.monitor_button:
            label = "Disable Auto-Sync" if is_enabled else "Enable Auto-Sync"
            self.monitor_button.text = label
    
    def cleanup(self):
        """Cleanup tray icon."""
        if self.tray_icon:
            self.tray_icon.kill()
