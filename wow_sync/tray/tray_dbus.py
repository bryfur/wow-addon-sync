"""
D-Bus StatusNotifier implementation (fallback).

This provides system tray functionality via the D-Bus StatusNotifier protocol,
which is commonly used on Linux desktop environments (KDE, GNOME, etc.).
This is used as a fallback when tray_manager is not available or not supported.

The StatusNotifier specification allows applications to display status icons
in the system tray with menu support and interaction capabilities.
"""

from typing import Callable, Optional
import asyncio
from pathlib import Path
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property, signal, PropertyAccess
from dbus_next import Variant, BusType
from PIL import Image


def _load_icon_from_png(icon_path: Path):
    """Load icon from PNG file and convert to ARGB format for D-Bus."""
    img = Image.open(icon_path).convert('RGBA')
    # Resize to 22x22 for tray icon
    img = img.resize((22, 22), Image.Resampling.LANCZOS)
    
    width, height = img.size
    pixels = []
    
    # Convert RGBA to ARGB
    for y in range(height):
        for x in range(width):
            r, g, b, a = img.getpixel((x, y))
            pixels.extend([a, r, g, b])
    
    return [width, height, bytes(pixels)]


class StatusNotifierItemInterface(ServiceInterface):
    """org.kde.StatusNotifierItem D-Bus interface."""
    
    def __init__(self, service: "TrayService", icon_data):
        super().__init__("org.kde.StatusNotifierItem")
        self._service = service
        self._status = "Active"
        self._icon_data = icon_data
    
    @dbus_property(access=PropertyAccess.READ)
    def Category(self) -> "s":
        return "ApplicationStatus"
    
    @dbus_property(access=PropertyAccess.READ)
    def Id(self) -> "s":
        return "wow-sync"
    
    @dbus_property(access=PropertyAccess.READ)
    def Title(self) -> "s":
        return "WoW Sync"
    
    @dbus_property(access=PropertyAccess.READ)
    def Status(self) -> "s":
        return self._status
    
    @dbus_property(access=PropertyAccess.READ)
    def IconName(self) -> "s":
        return "wow-sync"
    
    @dbus_property(access=PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":
        return [self._icon_data]
    
    @dbus_property(access=PropertyAccess.READ)
    def Menu(self) -> "o":
        return "/MenuBar"
    
    @dbus_property(access=PropertyAccess.READ)
    def ToolTip(self) -> "(sa(iiay)ss)":
        return ["", [], "WoW Sync", "World of Warcraft addon synchronization"]
    
    @method()
    def Activate(self, x: "i", y: "i"):
        self._service._handle_activate()
    
    @signal()
    def NewIcon(self) -> "":
        return None


class DBusMenuInterface(ServiceInterface):
    """com.canonical.dbusmenu D-Bus interface."""
    
    def __init__(self, service: "TrayService"):
        super().__init__("com.canonical.dbusmenu")
        self._service = service
        self._revision = 1
    
    @dbus_property(access=PropertyAccess.READ)
    def Version(self) -> "u":
        return 3
    
    @method()
    def GetLayout(self, parent_id: "i", recursion_depth: "i",
                  property_names: "as") -> "u(ia{sv}av)":
        layout = self._build_layout(parent_id, recursion_depth)
        return [self._revision, layout]
    
    @method()
    def Event(self, id_: "i", event_id: "s", data: "v", timestamp: "u"):
        if event_id == "clicked":
            self._service._handle_click(id_)
    
    @signal()
    def LayoutUpdated(self) -> "ui":
        return [self._revision, 0]
    
    def _build_layout(self, parent_id: int, depth: int = -1):
        if parent_id == 0:
            children = []
            if depth != 0:
                for item_id in self._service._root_items:
                    child = self._build_layout(item_id, depth - 1 if depth > 0 else -1)
                    children.append(Variant("(ia{sv}av)", child))
            return [0, {"children-display": Variant("s", "submenu")}, children]
        else:
            item = self._service._menu_items.get(parent_id)
            props = self._get_item_props(parent_id)
            return [parent_id, props, []]
    
    def _get_item_props(self, item_id: int) -> dict:
        item = self._service._menu_items.get(item_id)
        if not item:
            return {}
        
        label, enabled = item[0], item[1]
        
        if label == "separator":
            return {"type": Variant("s", "separator")}
        
        return {
            "label": Variant("s", label),
            "enabled": Variant("b", enabled),
            "visible": Variant("b", True),
        }


class TrayService:
    """StatusNotifier service for WoW Sync tray integration."""
    
    WATCHER_BUS = "org.kde.StatusNotifierWatcher"
    WATCHER_PATH = "/StatusNotifierWatcher"
    
    def __init__(self, on_show: Optional[Callable] = None,
                 on_quit: Optional[Callable] = None,
                 on_pull: Optional[Callable] = None,
                 on_push: Optional[Callable] = None,
                 on_toggle_monitor: Optional[Callable] = None,
                 icon_path: Optional[Path] = None):
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_pull = on_pull
        self.on_push = on_push
        self.on_toggle_monitor = on_toggle_monitor
        
        icon_data = _load_icon_from_png(icon_path)

        self._bus: Optional[MessageBus] = None
        self._sni_interface = StatusNotifierItemInterface(self, icon_data)
        self._menu_interface = DBusMenuInterface(self)
        
        # Menu: id -> (label, enabled)
        self._menu_items = {
            1: ("Show Window", True),
            2: ("separator", True),
            3: ("Pull from Remote", True),
            4: ("Push to Remote", True),
            5: ("separator", True),
            6: ("Enable Auto-Sync", True),  # Will be toggled dynamically
            7: ("separator", True),
            8: ("Quit", True),
        }
        self._root_items = [1, 2, 3, 4, 5, 6, 7, 8]
    
    def update_menu_item(self, item_id: int, label: str, enabled: bool = True):
        """Update a menu item's label and enabled state."""
        self._menu_items[item_id] = (label, enabled)
        self._menu_interface._revision += 1
    
    async def connect(self):
        """Connect to D-Bus and register interfaces."""
        self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
        unique_name = self._bus.unique_name
        
        self._bus.export("/StatusNotifierItem", self._sni_interface)
        self._bus.export("/MenuBar", self._menu_interface)
        
        try:
            introspection = await self._bus.introspect(
                self.WATCHER_BUS, self.WATCHER_PATH
            )
            proxy = self._bus.get_proxy_object(
                self.WATCHER_BUS, self.WATCHER_PATH, introspection
            )
            watcher = proxy.get_interface(self.WATCHER_BUS)
            await watcher.call_register_status_notifier_item(unique_name)
        except Exception as e:
            print(f"Warning: Failed to register with StatusNotifierWatcher: {e}")
    
    async def disconnect(self):
        if self._bus:
            self._bus.disconnect()
            self._bus = None
    
    def _handle_activate(self):
        if self.on_show:
            self.on_show()
    
    def _handle_click(self, item_id: int):
        if item_id == 1 and self.on_show:
            self.on_show()
        elif item_id == 3 and self.on_pull:
            self.on_pull()
        elif item_id == 4 and self.on_push:
            self.on_push()
        elif item_id == 6 and self.on_toggle_monitor:
            self.on_toggle_monitor()
        elif item_id == 8 and self.on_quit:
            self.on_quit()


class DBusTrayImpl:
    """D-Bus-based tray icon implementation."""
    
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
        self.dbus_tray = None
        
    async def setup(self):
        """Setup the tray icon using D-Bus StatusNotifier."""
        from ..constants import ICON_DIR
        
        self.dbus_tray = TrayService(
            on_show=self.on_show,
            on_quit=self.on_quit,
            on_pull=self.on_pull,
            on_push=self.on_push,
            on_toggle_monitor=self.on_toggle_monitor,
            icon_path=ICON_DIR / "icon.png"
        )
        
        # Connect to D-Bus using the current event loop
        # The connection stays alive as long as the event loop runs
        await self.dbus_tray.connect()
    
    async def cleanup(self):
        """Cleanup D-Bus tray."""
        if self.dbus_tray:
            await self.dbus_tray.disconnect()
    def update_monitor_menu(self, is_enabled: bool):
        """Update the auto-sync menu item label."""
        if self.dbus_tray:
            label = "Disable Auto-Sync" if is_enabled else "Enable Auto-Sync"
            self.dbus_tray.update_menu_item(6, label, True)
