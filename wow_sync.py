#!/usr/bin/env python3
"""
WoW Addon & Settings Sync Application
Cross-platform GUI application for syncing World of Warcraft addons and settings using Git.
"""

import os
import sys
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from threading import Thread
import git
from git import Repo, GitCommandError
import sv_ttk
from tray_manager import TrayManager, Button, OsSupport
import darkdetect



class WoWSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WoW Addon & Settings Sync")
        self.root.geometry("1000x700")
        
        # Set application icon
        self.set_icon()
        
        # Apply Sun Valley theme based on system preference
        theme = self.detect_system_theme()
        sv_ttk.set_theme(theme)
        
        # Configuration file path
        self.config_file = Path.home() / ".wow_sync_config.json"
        self.config = self.load_config()
        
        # Initialize variables
        self.wow_path = tk.StringVar(value=self.config.get("wow_path", ""))
        self.git_repo_url = tk.StringVar(value=self.config.get("git_repo_url", ""))
        self.sync_config_wtf = tk.BooleanVar(value=self.config.get("sync_config_wtf", False))
        
        # Version selection
        self.sync_retail = tk.BooleanVar(value=self.config.get("sync_retail", True))
        self.sync_classic = tk.BooleanVar(value=self.config.get("sync_classic", True))
        self.sync_classic_era = tk.BooleanVar(value=self.config.get("sync_classic_era", True))
        
        # Discovered WoW data
        self.available_versions = {}
        self.available_accounts = {}
        self.available_characters = {}
        
        # Account/Character selection (dict of version -> list of selected items)
        self.selected_accounts = self.config.get("selected_accounts", {})
        self.selected_characters = self.config.get("selected_characters", {})
        
        self.local_repo_path = Path.home() / ".wow_sync_repo"
        
        # System tray
        self.tray_icon = None
        self.tray_enabled = False
        
        # Theme listener
        self.theme_listener = None
        
        # Auto-save when settings change
        self.wow_path.trace_add('write', lambda *args: self.auto_save_config())
        self.git_repo_url.trace_add('write', lambda *args: self.auto_save_config())
        self.sync_config_wtf.trace_add('write', lambda *args: self.auto_save_config())
        self.sync_retail.trace_add('write', lambda *args: self.auto_save_config())
        self.sync_classic.trace_add('write', lambda *args: self.auto_save_config())
        self.sync_classic_era.trace_add('write', lambda *args: self.auto_save_config())
        
        self.create_widgets()
        
        # Setup theme change listener
        self.setup_theme_listener()
        
        # Setup system tray after widgets are created (helps with some Linux DEs)
        self.root.after(500, self.setup_tray_delayed)
    
    def detect_system_theme(self):
        """Detect system theme preference (dark or light)"""
        theme = darkdetect.theme()
        # darkdetect returns 'Dark', 'Light', or None
        if theme:
            return theme.lower()
        return "dark"  # Default to dark if detection fails
    
    def setup_theme_listener(self):
        """Setup listener for system theme changes"""
        try:
            self.theme_listener = darkdetect.Listener(self.on_theme_change)
            # Start listening in a separate thread
            Thread(target=self.theme_listener.listen, daemon=True).start()
            self.log("Theme change listener enabled")
        except Exception as e:
            # Listener not available or failed to start
            pass
    
    def on_theme_change(self, theme):
        """Callback for theme changes"""
        # Schedule theme update in main thread
        self.root.after(0, lambda: self.update_theme(theme.lower()))
    
    def update_theme(self, theme):
        """Update the application theme"""
        try:
            sv_ttk.set_theme(theme)
            self.log(f"Theme changed to: {theme}")
        except Exception as e:
            pass
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # WoW Installation Path
        ttk.Label(main_frame, text="WoW Installation Path:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.wow_path).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_wow_path).grid(row=0, column=2, pady=5)
        
        # Git Repository URL
        ttk.Label(main_frame, text="Git Repository URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.git_repo_url).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Sync options frame
        options_frame = ttk.LabelFrame(main_frame, text="Sync Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        options_frame.columnconfigure(1, weight=1)
        
        # Game version selection
        ttk.Label(options_frame, text="Game Versions:").grid(row=0, column=0, sticky=tk.W, pady=2)
        versions_frame = ttk.Frame(options_frame)
        versions_frame.grid(row=0, column=1, sticky=tk.W, pady=2)
        ttk.Checkbutton(versions_frame, text="Retail", variable=self.sync_retail).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(versions_frame, text="Classic", variable=self.sync_classic).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(versions_frame, text="Classic Era", variable=self.sync_classic_era).pack(side=tk.LEFT, padx=5)
        
        # Account and Character selection
        ttk.Label(options_frame, text="Characters:").grid(row=1, column=0, sticky=tk.W, pady=2)
        select_button_frame = ttk.Frame(options_frame)
        select_button_frame.grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Button(select_button_frame, text="Select Characters...", command=self.open_selection_dialog).pack(side=tk.LEFT, padx=5)
        self.selection_status_label = ttk.Label(select_button_frame, text="(All characters)", font=('', 8))
        self.selection_status_label.pack(side=tk.LEFT, padx=5)
        
        # Config.wtf option
        ttk.Checkbutton(options_frame, text="Sync Config.wtf files (game settings)", 
                       variable=self.sync_config_wtf).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="Initialize Repo", command=self.init_repo).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Pull from Remote", command=self.pull_from_remote).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Push to Remote", command=self.push_to_remote).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Config", command=self.save_current_config).pack(side=tk.LEFT, padx=5)
        
        # Status/Log area
        ttk.Label(main_frame, text="Status Log:").grid(row=5, column=0, sticky=tk.W, pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80, state='disabled')
        self.log_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        main_frame.rowconfigure(6, weight=1)
        
        self.log("WoW Sync Application started")
        
        # Update selection status label
        self.update_selection_status()
        
        if self.wow_path.get():
            self.log(f"Loaded WoW path: {self.wow_path.get()}")
        if self.git_repo_url.get():
            self.log(f"Loaded Git repo URL: {self.git_repo_url.get()}")
    
    def setup_tray_delayed(self):
        """Setup system tray with delay (helps with Linux DE compatibility)"""
        try:
            self.setup_tray()
            if self.tray_icon:
                self.tray_enabled = True
                self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
                self.log("System tray enabled")
        except Exception as e:
            self.log(f"System tray not available: {e}")
            self.tray_enabled = False
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
    
    def setup_tray(self):
        """Setup system tray icon"""
        # Check if menu is supported on this OS
        if not OsSupport.SUPPORT_MENU:
            self.log("System tray menu not supported on this OS/backend - tray disabled")
            return
        
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            # Create tray manager with separate thread (required for Linux/KDE)
            self.tray_icon = TrayManager("WoW Sync", run_in_separate_thread=True)
            
            # Load and set icon
            self.tray_icon.load_icon(str(icon_path), "app_icon")
            self.tray_icon.set_icon("app_icon")
            
            # Check if default button style is supported
            use_default = OsSupport.SUPPORT_DEFAULT if hasattr(OsSupport, 'SUPPORT_DEFAULT') else False
            
            # Create menu items
            show_button = Button("Show Window", self.tray_show_window, default=use_default)
            quit_button = Button("Quit Application", self.tray_quit_app)
            
            # Add items to menu
            menu = self.tray_icon.menu
            if menu:
                menu.add(show_button)
                menu.add(quit_button)
                self.log("System tray menu created")
    
    def on_window_close(self):
        """Handle window close button"""
        if self.tray_enabled and self.tray_icon:
            # Minimize to tray
            self.minimize_to_tray()
        else:
            # No working tray, just quit
            self.quit_app()
    
    def minimize_to_tray(self):
        """Minimize window to system tray"""
        self.root.withdraw()
    
    def tray_show_window(self):
        """Thread-safe wrapper for showing window from tray"""
        self.root.after(0, self.show_window)
    
    def show_window(self):
        """Restore window from system tray"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def tray_quit_app(self):
        """Thread-safe wrapper for quitting from tray"""
        self.root.after(0, self.quit_app)
    
    def quit_app(self):
        """Quit the application"""
        # Stop theme listener
        if self.theme_listener:
            try:
                self.theme_listener.stop(timeout=1)
            except:
                pass
        
        # Stop tray icon
        if self.tray_icon:
            try:
                self.tray_icon.kill()
            except:
                pass
        
        self.root.destroy()
        sys.exit(0)
    
    def set_icon(self):
        """Set the application icon"""
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
            except Exception as e:
                # Silently fail if icon can't be loaded
                pass
    
    def log(self, message):
        """Add a message to the log area"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
    
    def browse_wow_path(self):
        """Browse for WoW installation directory"""
        path = filedialog.askdirectory(title="Select WoW Installation Directory")
        if path:
            self.wow_path.set(path)
            self.log(f"WoW path set to: {path}")
    
    def auto_save_config(self):
        """Automatically save configuration when settings change"""
        config = {
            "wow_path": self.wow_path.get(),
            "git_repo_url": self.git_repo_url.get(),
            "sync_config_wtf": self.sync_config_wtf.get(),
            "sync_retail": self.sync_retail.get(),
            "sync_classic": self.sync_classic.get(),
            "sync_classic_era": self.sync_classic_era.get(),
            "selected_accounts": self.selected_accounts,
            "selected_characters": self.selected_characters
        }
        self.save_config(config)
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return {}
        return {}
    
    def save_config(self, config):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.log(f"Error saving config: {e}")
    
    def save_current_config(self):
        """Manually save current settings to config file"""
        self.auto_save_config()
        self.log("Configuration saved")
        messagebox.showinfo("Success", "Configuration saved successfully!")
    
    def scan_wow_directory(self):
        """Scan WoW directory for versions, accounts, and characters"""
        if not self.wow_path.get() or not Path(self.wow_path.get()).exists():
            messagebox.showerror("Error", "Please set a valid WoW installation path first")
            return False
        
        wow_base = Path(self.wow_path.get())
        self.available_versions = {}
        self.available_accounts = {}
        self.available_characters = {}
        
        version_map = {
            '_retail_': 'Retail',
            '_classic_': 'Classic',
            '_classic_era_': 'Classic Era'
        }
        
        for version_dir, version_name in version_map.items():
            version_path = wow_base / version_dir
            if version_path.exists():
                self.available_versions[version_dir] = version_name
                
                # Scan for accounts
                wtf_path = version_path / 'WTF' / 'Account'
                if wtf_path.exists():
                    accounts = []
                    for account_dir in wtf_path.iterdir():
                        if account_dir.is_dir() and not account_dir.name.startswith('.'):
                            accounts.append(account_dir.name)
                            
                            # Scan for characters in this account
                            for server_dir in account_dir.iterdir():
                                if server_dir.is_dir() and not server_dir.name.startswith('.'):
                                    # Check if this looks like a server directory
                                    if server_dir.name not in ['SavedVariables']:
                                        for char_dir in server_dir.iterdir():
                                            if char_dir.is_dir() and not char_dir.name.startswith('.'):
                                                char_key = f"{version_dir}:{account_dir.name}:{server_dir.name}:{char_dir.name}"
                                                self.available_characters[char_key] = {
                                                    'version': version_dir,
                                                    'account': account_dir.name,
                                                    'server': server_dir.name,
                                                    'character': char_dir.name
                                                }
                    
                    if accounts:
                        self.available_accounts[version_dir] = accounts
        
        return True
    
    def open_selection_dialog(self):
        """Open dialog to select accounts and characters"""
        if not self.scan_wow_directory():
            return
        
        if not self.available_versions:
            messagebox.showinfo("No Data", "No WoW versions found in the installation directory")
            return
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Characters to Sync")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame with scrollbar
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas and scrollbar for scrolling
        canvas = tk.Canvas(main_frame, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_canvas_configure(event):
            # Make the scrollable_frame match canvas width
            canvas.itemconfig(canvas_window, width=event.width)
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Store checkbox variables and collapse states
        character_vars = {}
        collapse_states = {}
        
        # Version selection mapping
        version_enabled = {
            '_retail_': self.sync_retail.get(),
            '_classic_': self.sync_classic.get(),
            '_classic_era_': self.sync_classic_era.get()
        }
        
        # Create checkboxes for each version
        for version_dir, version_name in self.available_versions.items():
            # Skip if version is not enabled
            if not version_enabled.get(version_dir, False):
                continue
                
            # Characters section
            version_chars = {k: v for k, v in self.available_characters.items() if v['version'] == version_dir}
            if version_chars:
                version_frame = ttk.LabelFrame(scrollable_frame, text=version_name, padding="10")
                version_frame.pack(fill=tk.X, padx=5, pady=5)
                
                # Group by account and server
                chars_by_account = {}
                for char_key, char_data in version_chars.items():
                    account_server = f"{char_data['account']} - {char_data['server']}"
                    if account_server not in chars_by_account:
                        chars_by_account[account_server] = []
                    chars_by_account[account_server].append((char_key, char_data['character']))
                
                for account_server, characters in sorted(chars_by_account.items()):
                    # Create collapsible section
                    section_frame = ttk.Frame(version_frame)
                    section_frame.pack(fill=tk.X, pady=2)
                    
                    # Collapse state
                    collapse_key = f"{version_dir}:{account_server}"
                    collapse_states[collapse_key] = tk.BooleanVar(value=False)
                    
                    # Header frame with toggle button
                    header_frame = ttk.Frame(section_frame)
                    header_frame.pack(fill=tk.X)
                    
                    # Characters container (collapsible)
                    chars_container = ttk.Frame(section_frame)
                    
                    def make_toggle(container, state_var, btn):
                        def toggle():
                            if state_var.get():
                                container.pack_forget()
                                btn.config(text="▶")
                                state_var.set(False)
                            else:
                                container.pack(fill=tk.X, padx=20)
                                btn.config(text="▼")
                                state_var.set(True)
                        return toggle
                    
                    toggle_btn = ttk.Button(header_frame, text="▼", width=3)
                    toggle_btn.pack(side=tk.LEFT)
                    
                    ttk.Label(header_frame, text=account_server, font=('', 9, 'bold')).pack(side=tk.LEFT, padx=5)
                    
                    toggle_btn.config(command=make_toggle(chars_container, collapse_states[collapse_key], toggle_btn))
                    
                    # Add characters to container
                    for char_key, char_name in sorted(characters, key=lambda x: x[1]):
                        # Check if user has made an explicit selection before
                        has_explicit_selection = '_explicit_selection' in self.selected_characters
                        
                        if has_explicit_selection:
                            # User has made a selection before, respect it
                            default_selected = version_dir in self.selected_characters and char_key in self.selected_characters[version_dir]
                        else:
                            # First time, default to all selected
                            default_selected = True
                        
                        var = tk.BooleanVar(value=default_selected)
                        character_vars[char_key] = var
                        ttk.Checkbutton(chars_container, text=char_name, variable=var).pack(anchor=tk.W, padx=5)
                    
                    # Start expanded
                    chars_container.pack(fill=tk.X, padx=20)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def select_all():
            for var in character_vars.values():
                var.set(True)
        
        def deselect_all():
            for var in character_vars.values():
                var.set(False)
        
        def save_selection():
            # Extract accounts from selected characters and save both
            # Use a marker to indicate explicit selection has been made
            self.selected_accounts = {}
            self.selected_characters = {}
            
            # Mark that user has made an explicit selection
            # Empty dict with special marker means "explicitly selected none"
            self.selected_characters['_explicit_selection'] = True
            
            for key, var in character_vars.items():
                if var.get():
                    char_data = self.available_characters[key]
                    version_dir = char_data['version']
                    account = char_data['account']
                    
                    # Add to selected characters
                    if version_dir not in self.selected_characters:
                        self.selected_characters[version_dir] = []
                    self.selected_characters[version_dir].append(key)
                    
                    # Also track which accounts have selected characters
                    if version_dir not in self.selected_accounts:
                        self.selected_accounts[version_dir] = []
                    if account not in self.selected_accounts[version_dir]:
                        self.selected_accounts[version_dir].append(account)
            
            # Update status label
            self.update_selection_status()
            
            # Auto-save the updated selection
            self.auto_save_config()
            
            dialog.destroy()
        
        ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", command=deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="OK", command=save_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def update_selection_status(self):
        """Update the status label showing current selection"""
        # Remove the marker for counting
        chars_dict = {k: v for k, v in self.selected_characters.items() if k != '_explicit_selection'}
        total_chars = sum(len(chars) for chars in chars_dict.values())
        
        # Check if user has made an explicit selection
        has_explicit_selection = '_explicit_selection' in self.selected_characters
        
        if not has_explicit_selection:
            status = "(All characters)"
        elif total_chars == 0:
            status = "(No characters selected)"
        else:
            status = f"({total_chars} character(s) selected)"
        
        self.selection_status_label.config(text=status)
    
    def validate_inputs(self):
        """Validate that required paths and URLs are set"""
        if not self.wow_path.get():
            messagebox.showerror("Error", "Please set the WoW installation path")
            return False
        
        if not Path(self.wow_path.get()).exists():
            messagebox.showerror("Error", "WoW installation path does not exist")
            return False
        
        if not self.git_repo_url.get():
            messagebox.showerror("Error", "Please set the Git repository URL")
            return False
        
        return True
    
    def get_wow_sync_paths(self):
        """Get the paths to sync from WoW installation"""
        wow_base = Path(self.wow_path.get())
        
        # Common paths to sync (works for both retail and classic)
        paths_to_sync = []
        
        # Version selection mapping
        version_map = {
            '_retail_': self.sync_retail.get(),
            '_classic_': self.sync_classic.get(),
            '_classic_era_': self.sync_classic_era.get()
        }
        
        # Check for different WoW versions
        for version in ['_retail_', '_classic_', '_classic_era_']:
            # Skip if version is not selected
            if not version_map[version]:
                continue
                
            version_path = wow_base / version
            if version_path.exists():
                wtf_path = version_path / 'WTF'
                addons_path = version_path / 'Interface' / 'AddOns'
                
                if wtf_path.exists():
                    paths_to_sync.append(('WTF', wtf_path, version))
                if addons_path.exists():
                    paths_to_sync.append(('AddOns', addons_path, version))
        
        return paths_to_sync
    
    def copy_wow_to_repo(self):
        """Copy WoW addons and settings to the local repo"""
        paths_to_sync = self.get_wow_sync_paths()
        
        if not paths_to_sync:
            self.log("Warning: No WoW directories found to sync")
            return
        
        for sync_type, source_path, version in paths_to_sync:
            dest_path = self.local_repo_path / version / sync_type
            
            self.log(f"Syncing {sync_type} from {version}...")
            
            # Remove old data and copy new
            if dest_path.exists():
                shutil.rmtree(dest_path)
            
            # Define ignore function for Config.wtf and filtering
            def ignore_function(dir, files):
                ignored = []
                
                # Filter Config.wtf if not syncing
                if not self.sync_config_wtf.get() and sync_type == 'WTF':
                    ignored.extend([f for f in files if f.lower() == 'config.wtf'])
                
                # Filter accounts if selections exist
                if sync_type == 'WTF' and version in self.selected_accounts:
                    selected_accounts = self.selected_accounts[version]
                    # Check if we're in the Account directory
                    if Path(dir).name == 'Account':
                        # Keep only specified accounts
                        ignored.extend([f for f in files if f not in selected_accounts and Path(dir, f).is_dir()])
                
                # Filter characters if selections exist
                if sync_type == 'WTF' and version in self.selected_characters:
                    selected_char_keys = self.selected_characters[version]
                    dir_path = Path(dir)
                    
                    # Extract account and server from current path
                    parts = dir_path.parts
                    if 'Account' in parts:
                        account_idx = parts.index('Account')
                        if len(parts) > account_idx + 2:
                            account = parts[account_idx + 1]
                            server = parts[account_idx + 2]
                            
                            # Check if we're at the server level (where character folders are)
                            if dir_path.name == server:
                                # Get selected characters for this account/server combo
                                selected_chars = []
                                for char_key in selected_char_keys:
                                    char_data = self.available_characters.get(char_key)
                                    if char_data and char_data['account'] == account and char_data['server'] == server:
                                        selected_chars.append(char_data['character'])
                                
                                if selected_chars:
                                    # Only keep selected characters
                                    char_folders = [f for f in files if Path(dir, f).is_dir() and f not in ['.', '..']]
                                    ignored.extend([f for f in char_folders if f not in selected_chars])
                
                return ignored
            
            shutil.copytree(source_path, dest_path, ignore=ignore_function)
            self.log(f"Copied {source_path} to {dest_path}")
            
            # Log what was filtered
            filters_applied = []
            if not self.sync_config_wtf.get() and sync_type == 'WTF':
                filters_applied.append("Config.wtf excluded")
            if version in self.selected_accounts and sync_type == 'WTF':
                filters_applied.append(f"{len(self.selected_accounts[version])} account(s)")
            if version in self.selected_characters and version != '_explicit_selection' and sync_type == 'WTF':
                filters_applied.append(f"{len(self.selected_characters[version])} character(s)")
            
            if filters_applied:
                self.log(f"  Filters: {', '.join(filters_applied)}")
    
    def copy_repo_to_wow(self):
        """Copy addons and settings from repo to WoW installation"""
        wow_base = Path(self.wow_path.get())
        
        # Version selection mapping
        version_map = {
            '_retail_': self.sync_retail.get(),
            '_classic_': self.sync_classic.get(),
            '_classic_era_': self.sync_classic_era.get()
        }
        
        # Iterate through versions in the repo
        for version_dir in self.local_repo_path.iterdir():
            if version_dir.is_dir() and version_dir.name.startswith('_'):
                # Skip if version is not selected
                if not version_map.get(version_dir.name, False):
                    self.log(f"Skipping {version_dir.name} (not selected)")
                    continue
                    
                version_path = wow_base / version_dir.name
                
                if not version_path.exists():
                    self.log(f"Warning: {version_path} does not exist in your WoW installation, skipping...")
                    continue
                
                # Copy WTF
                wtf_source = version_dir / 'WTF'
                if wtf_source.exists():
                    wtf_dest = version_path / 'WTF'
                    self.log(f"Copying WTF to {version_dir.name}...")
                    if wtf_dest.exists():
                        shutil.rmtree(wtf_dest)
                    
                    # Define ignore function for Config.wtf and filtering
                    def ignore_function(dir, files):
                        ignored = []
                        
                        # Filter Config.wtf if not syncing
                        if not self.sync_config_wtf.get():
                            ignored.extend([f for f in files if f.lower() == 'config.wtf'])
                        
                        # Filter accounts if selections exist
                        if version_dir.name in self.selected_accounts:
                            selected_accounts = self.selected_accounts[version_dir.name]
                            if Path(dir).name == 'Account':
                                ignored.extend([f for f in files if f not in selected_accounts and Path(dir, f).is_dir()])
                        
                        # Filter characters if selections exist
                        if version_dir.name in self.selected_characters:
                            selected_char_keys = self.selected_characters[version_dir.name]
                            dir_path = Path(dir)
                            
                            # Extract account and server from current path
                            parts = dir_path.parts
                            if 'Account' in parts:
                                account_idx = parts.index('Account')
                                if len(parts) > account_idx + 2:
                                    account = parts[account_idx + 1]
                                    server = parts[account_idx + 2]
                                    
                                    # Check if we're at the server level
                                    if dir_path.name == server:
                                        # Get selected characters for this account/server combo
                                        selected_chars = []
                                        for char_key in selected_char_keys:
                                            char_data = self.available_characters.get(char_key)
                                            if char_data and char_data['account'] == account and char_data['server'] == server:
                                                selected_chars.append(char_data['character'])
                                        
                                        if selected_chars:
                                            char_folders = [f for f in files if Path(dir, f).is_dir() and f not in ['.', '..']]
                                            ignored.extend([f for f in char_folders if f not in selected_chars])
                        
                        return ignored
                    
                    shutil.copytree(wtf_source, wtf_dest, ignore=ignore_function)
                    
                    # Log what was filtered
                    filters_applied = []
                    if not self.sync_config_wtf.get():
                        filters_applied.append("Config.wtf excluded")
                    if version_dir.name in self.selected_accounts:
                        filters_applied.append(f"{len(self.selected_accounts[version_dir.name])} account(s)")
                    if version_dir.name in self.selected_characters and version_dir.name != '_explicit_selection':
                        filters_applied.append(f"{len(self.selected_characters[version_dir.name])} character(s)")
                    
                    if filters_applied:
                        self.log(f"  Filters: {', '.join(filters_applied)}")
                
                # Copy AddOns
                addons_source = version_dir / 'AddOns'
                if addons_source.exists():
                    addons_dest = version_path / 'Interface' / 'AddOns'
                    self.log(f"Copying AddOns to {version_dir.name}...")
                    if addons_dest.exists():
                        shutil.rmtree(addons_dest)
                    addons_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(addons_source, addons_dest)
    
    def init_repo(self):
        """Initialize or clone the git repository"""
        if not self.validate_inputs():
            return
        
        def init_thread():
            try:
                self.log("Initializing repository...")
                
                if self.local_repo_path.exists():
                    self.log(f"Local repo already exists at {self.local_repo_path}")
                    try:
                        repo = Repo(self.local_repo_path)
                        self.log("Existing repository loaded")
                    except Exception:
                        self.log("Directory exists but is not a git repo, removing...")
                        shutil.rmtree(self.local_repo_path)
                        self.clone_repo()
                else:
                    self.clone_repo()
                
                messagebox.showinfo("Success", "Repository initialized successfully!")
                
            except Exception as e:
                self.log(f"Error initializing repo: {str(e)}")
                messagebox.showerror("Error", f"Failed to initialize repository:\n{str(e)}")
        
        Thread(target=init_thread, daemon=True).start()
    
    def clone_repo(self):
        """Clone the remote repository"""
        self.log(f"Cloning repository from {self.git_repo_url.get()}...")
        try:
            Repo.clone_from(self.git_repo_url.get(), self.local_repo_path)
            self.log("Repository cloned successfully")
        except GitCommandError as e:
            if "already exists and is not an empty directory" in str(e):
                self.log("Repository already exists")
            else:
                # If repo doesn't exist remotely, create a new one
                self.log("Remote repository not found, creating new local repository...")
                self.local_repo_path.mkdir(parents=True, exist_ok=True)
                repo = Repo.init(self.local_repo_path)
                
                # Create initial commit
                gitignore_path = self.local_repo_path / '.gitignore'
                with open(gitignore_path, 'w') as f:
                    f.write("# WoW Sync\n*.bak\n*.tmp\n")
                
                repo.index.add(['.gitignore'])
                repo.index.commit("Initial commit")
                
                # Add remote
                try:
                    repo.create_remote('origin', self.git_repo_url.get())
                    self.log("Remote 'origin' added")
                except Exception:
                    self.log("Remote 'origin' already exists")
                
                self.log("New repository created")
    
    def pull_from_remote(self):
        """Pull changes from remote repository and apply to WoW"""
        if not self.validate_inputs():
            return
        
        def pull_thread():
            try:
                self.log("Pulling from remote repository...")
                
                if not self.local_repo_path.exists():
                    self.log("Local repo not found, initializing first...")
                    self.clone_repo()
                
                repo = Repo(self.local_repo_path)
                
                # Check for uncommitted local changes
                if repo.is_dirty() or repo.untracked_files:
                    self.log("Local changes detected, stashing before pull...")
                    repo.git.stash('save', 'Auto-stash before pull')
                    had_stash = True
                else:
                    had_stash = False
                
                # Try to pull
                origin = repo.remote('origin')
                try:
                    origin.pull()
                    self.log("Pull successful")
                    
                    # Restore stash if we had one
                    if had_stash:
                        try:
                            repo.git.stash('pop')
                            self.log("Restored local changes")
                        except GitCommandError as e:
                            if 'CONFLICT' in str(e):
                                self.handle_merge_conflict(repo)
                                return
                            
                except GitCommandError as e:
                    if 'CONFLICT' in str(e) or 'Merge conflict' in str(e):
                        self.log("Merge conflict detected")
                        self.handle_merge_conflict(repo)
                        return
                    else:
                        raise
                
                self.log("Applying changes to WoW installation...")
                self.copy_repo_to_wow()
                
                self.log("Pull and sync completed successfully!")
                messagebox.showinfo("Success", "Successfully pulled changes from remote and updated WoW!")
                
            except Exception as e:
                self.log(f"Error during pull: {str(e)}")
                messagebox.showerror("Error", f"Failed to pull from remote:\n{str(e)}")
        
        Thread(target=pull_thread, daemon=True).start()
    
    def handle_merge_conflict(self, repo):
        """Handle merge conflicts with user choice"""
        self.log("Merge conflict detected - user intervention required")
        
        # Ask user how to resolve
        response = messagebox.askyesnocancel(
            "Merge Conflict",
            "Conflict detected between local and remote changes.\n\n"
            "YES: Use remote changes (discard local)\n"
            "NO: Keep local changes (discard remote)\n"
            "CANCEL: Abort (manual resolution needed)"
        )
        
        if response is True:  # Use remote (theirs)
            self.log("Resolving conflict: using remote changes...")
            try:
                repo.git.reset('--hard', 'origin/' + repo.active_branch.name)
                self.log("Applied remote changes")
                self.copy_repo_to_wow()
                self.log("Conflict resolved - remote changes applied")
                messagebox.showinfo("Success", "Remote changes applied successfully!")
            except Exception as e:
                self.log(f"Error applying remote changes: {str(e)}")
                messagebox.showerror("Error", f"Failed to apply remote changes:\n{str(e)}")
                
        elif response is False:  # Keep local (ours)
            self.log("Resolving conflict: keeping local changes...")
            try:
                repo.git.reset('--merge')
                repo.git.reset('--hard')
                self.log("Kept local changes")
                messagebox.showinfo("Success", "Local changes kept. You may want to push your changes.")
            except Exception as e:
                self.log(f"Error keeping local changes: {str(e)}")
                messagebox.showerror("Error", f"Failed to resolve:\n{str(e)}")
                
        else:  # Cancel
            self.log("Conflict resolution cancelled by user")
            messagebox.showwarning(
                "Manual Resolution Required",
                f"Merge conflict not resolved.\n\n"
                f"Repository location: {self.local_repo_path}\n\n"
                f"You may need to resolve conflicts manually or delete the local repository to start fresh."
            )
    
    def push_to_remote(self):
        """Copy WoW data to repo and push to remote"""
        if not self.validate_inputs():
            return
        
        def push_thread():
            try:
                self.log("Copying WoW data to repository...")
                
                if not self.local_repo_path.exists():
                    self.log("Local repo not found, initializing first...")
                    self.clone_repo()
                
                self.copy_wow_to_repo()
                
                self.log("Committing changes...")
                repo = Repo(self.local_repo_path)
                
                # Add all changes
                repo.git.add(A=True)
                
                # Check if there are changes to commit
                if repo.is_dirty() or repo.untracked_files:
                    repo.index.commit("Update WoW addons and settings")
                    self.log("Changes committed")
                    
                    self.log("Pushing to remote...")
                    origin = repo.remote('origin')
                    origin.push()
                    
                    self.log("Push completed successfully!")
                    messagebox.showinfo("Success", "Successfully pushed changes to remote!")
                else:
                    self.log("No changes to commit")
                    messagebox.showinfo("Info", "No changes to push - everything is up to date")
                
            except Exception as e:
                self.log(f"Error during push: {str(e)}")
                messagebox.showerror("Error", f"Failed to push to remote:\n{str(e)}")
        
        Thread(target=push_thread, daemon=True).start()


def main():
    root = tk.Tk()
    app = WoWSyncApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
