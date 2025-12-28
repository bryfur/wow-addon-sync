import sys
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from threading import Thread
import sv_ttk
import darkdetect
from async_tkinter_loop import async_handler

from ..config import ConfigManager
from ..directory_manager import DirectoryManager
from ..process_monitor import ProcessMonitor
from ..sync_controller import SyncController
from ..tray import TrayIcon
from ..constants import ICON_DIR, LOCAL_REPO_PATH
from .character_dialog import CharacterDialog


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("WoW Addon & Settings Sync")
        self.root.geometry("1000x700")
        
        self._setup_icon()
        self._setup_theme()
        
        self.config = ConfigManager()
        
        self.wow_path = tk.StringVar(value=self.config.get("wow_path", ""))
        self.git_repo_url = tk.StringVar(value=self.config.get("git_repo_url", ""))
        self.sync_config_wtf = tk.BooleanVar(value=self.config.get("sync_config_wtf", False))
        self.sync_retail = tk.BooleanVar(value=self.config.get("sync_retail", True))
        self.sync_classic = tk.BooleanVar(value=self.config.get("sync_classic", True))
        self.sync_classic_era = tk.BooleanVar(value=self.config.get("sync_classic_era", True))
        self.auto_sync = tk.BooleanVar(value=self.config.get("auto_sync", True))
        
        self.available_versions = {}
        self.available_accounts = {}
        self.available_characters = {}
        self.selected_accounts = self.config.get("selected_accounts", {})
        self.selected_characters = self.config.get("selected_characters", {})
        
        self.tray_icon = None
        self.tray_enabled = False
        self.theme_listener = None
        self.process_monitor = None
        self.sync_controller = None
        
        for var in [self.wow_path, self.git_repo_url, self.sync_config_wtf,
                   self.sync_retail, self.sync_classic, self.sync_classic_era, self.auto_sync]:
            var.trace_add('write', lambda *args: self._auto_save())
        
        self._create_widgets()
        self._setup_theme_listener()

        self.root.after(0, self._setup_tray)
        self.root.after(0, self._start_process_monitor)
    
    def _setup_icon(self):
        icon_path = ICON_DIR / "icon.png"
        if icon_path.exists():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
            except Exception:
                pass
    
    def _setup_theme(self):
        theme = darkdetect.theme()
        sv_ttk.set_theme(theme.lower() if theme else "dark")
    
    def _setup_theme_listener(self):
        try:
            self.theme_listener = darkdetect.Listener(self._on_theme_change)
            Thread(target=self.theme_listener.listen, daemon=True).start()
            self.log("Theme change listener enabled")
        except Exception:
            pass
    
    def _on_theme_change(self, theme):
        self.root.after(0, lambda: self._update_theme(theme.lower()))
    
    def _update_theme(self, theme):
        try:
            sv_ttk.set_theme(theme)
            self.log(f"Theme changed to: {theme}")
        except Exception:
            pass
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        ttk.Label(main_frame, text="WoW Installation Path:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.wow_path).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(main_frame, text="Browse", command=self._browse_wow_path).grid(row=0, column=2, pady=5)
        
        ttk.Label(main_frame, text="Git Repository URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.git_repo_url).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        options_frame = ttk.LabelFrame(main_frame, text="Sync Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        options_frame.columnconfigure(1, weight=1)
        
        ttk.Label(options_frame, text="Game Versions:").grid(row=0, column=0, sticky=tk.W, pady=2)
        versions_frame = ttk.Frame(options_frame)
        versions_frame.grid(row=0, column=1, sticky=tk.W, pady=2)
        ttk.Checkbutton(versions_frame, text="Retail", variable=self.sync_retail).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(versions_frame, text="Classic", variable=self.sync_classic).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(versions_frame, text="Classic Era", variable=self.sync_classic_era).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(options_frame, text="Characters:").grid(row=1, column=0, sticky=tk.W, pady=2)
        select_button_frame = ttk.Frame(options_frame)
        select_button_frame.grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Button(select_button_frame, text="Select Characters...", 
                  command=self._open_character_dialog).pack(side=tk.LEFT, padx=5)
        self.selection_status_label = ttk.Label(select_button_frame, text="(All characters)", font=('', 8))
        self.selection_status_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(options_frame, text="Sync Config.wtf files (game settings)", 
                       variable=self.sync_config_wtf).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        
        ttk.Checkbutton(options_frame, text="Auto-sync when WoW starts/stops", 
                       variable=self.auto_sync, command=self._toggle_auto_sync).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        self.init_button = ttk.Button(self.button_frame, text="Initialize Repo", command=self._init_repo)
        self.pull_button = ttk.Button(self.button_frame, text="Pull from Remote", command=self._pull_from_remote)
        self.push_button = ttk.Button(self.button_frame, text="Push to Remote", command=self._push_to_remote)
        
        self._update_button_visibility()
        
        ttk.Label(main_frame, text="Status Log:").grid(row=5, column=0, sticky=tk.W, pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80, state='disabled')
        self.log_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        main_frame.rowconfigure(6, weight=1)
        
        self.log("WoW Sync Application started")
        self._update_selection_status()
        
        if self.wow_path.get():
            self.log(f"Loaded WoW path: {self.wow_path.get()}")
        if self.git_repo_url.get():
            self.log(f"Loaded Git repo URL: {self.git_repo_url.get()}")
    
    @async_handler
    async def _setup_tray(self):
        """Setup system tray icon with automatic fallback between implementations."""
        try:
            self.tray_icon = TrayIcon(
                on_show=self._show_window,
                on_quit=self.quit_app,
                on_pull=self._pull_from_remote,
                on_push=self._push_to_remote,
                on_toggle_monitor=self._tray_toggle_monitor
            )
            success, message = await self.tray_icon.setup()
            
            if success:
                self.tray_enabled = True
                self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
                self.log(message)
                # Update monitor menu to reflect current state
                self._update_monitor_menu()
            else:
                self.log(message)
                self.tray_enabled = False
                self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        except Exception as e:
            self.log(f"System tray setup failed: {e}")
            self.tray_enabled = False
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
    
    def _on_window_close(self):
        if self.tray_enabled and self.tray_icon:
            self.root.withdraw()
        else:
            self.quit_app()
    
    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    @async_handler
    async def quit_app(self):
        if self.process_monitor:
            await self.process_monitor.stop()
        
        if self.theme_listener:
            try:
                self.theme_listener.stop(timeout=1)
            except:
                pass
        
        if self.tray_icon:
            await self.tray_icon.cleanup()
        
        self.root.quit()
        self.root.destroy()
    
    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
    
    def _browse_wow_path(self):
        path = filedialog.askdirectory(title="Select WoW Installation Directory")
        if path:
            self.wow_path.set(path)
            self.log(f"WoW path set to: {path}")
    
    def _auto_save(self):
        config = {
            "wow_path": self.wow_path.get(),
            "git_repo_url": self.git_repo_url.get(),
            "sync_config_wtf": self.sync_config_wtf.get(),
            "sync_retail": self.sync_retail.get(),
            "sync_classic": self.sync_classic.get(),
            "sync_classic_era": self.sync_classic_era.get(),
            "auto_sync": self.auto_sync.get(),
            "selected_accounts": self.selected_accounts,
            "selected_characters": self.selected_characters,
        }
        self.config.update(config)
    
    @async_handler
    async def _start_process_monitor(self):
        if not self._validate_inputs():
            self.log("Process monitor disabled: configuration incomplete")
            return
        
        if not self.auto_sync.get():
            return
        
        if self.process_monitor:
            return  # Already running
        
        try:
            self.process_monitor = ProcessMonitor(
                on_start_callback=self._on_wow_start,
                on_stop_callback=self._on_wow_stop,
                log_callback=self.log
            )
            await self.process_monitor.start()
        except Exception as e:
            self.log(f"Failed to start process monitor: {e}")
        
        self._update_monitor_menu()
    
    def _tray_toggle_monitor(self):
        """Toggle auto-sync from tray menu."""
        self.auto_sync.set(not self.auto_sync.get())
        self._toggle_auto_sync()
    
    def _update_monitor_menu(self):
        """Update the tray menu to reflect monitor state."""
        if self.tray_icon:
            self.tray_icon.update_monitor_menu(self.auto_sync.get())
    
    def _toggle_auto_sync(self):
        if self.auto_sync.get():
            # _start_process_monitor has @async_handler, so just call it directly
            self._start_process_monitor()
        else:
            if self.process_monitor:
                # _stop_process_monitor is a regular async function, so use create_task
                asyncio.create_task(self._stop_process_monitor())
        # Update the menu after toggling
        self._update_monitor_menu()
    
    async def _stop_process_monitor(self):
        if self.process_monitor:
            await self.process_monitor.stop()
            self.process_monitor = None
    
    def _on_wow_start(self, proc_name, pid):
        self.log(f"Auto-sync: Pulling updates (WoW starting)")
        self.root.after(0, self._auto_pull)
    
    def _on_wow_stop(self, pid):
        self.log(f"Auto-sync: Pushing changes (WoW closed)")
        self.root.after(0, self._auto_push)
    
    def _get_sync_controller(self):
        if not self.sync_controller:
            self.sync_controller = SyncController(
                Path(self.wow_path.get()),
                self.git_repo_url.get(),
                self.log
            )
        return self.sync_controller
    
    def _get_enabled_versions(self):
        return {
            '_retail_': self.sync_retail.get(),
            '_classic_': self.sync_classic.get(),
            '_classic_era_': self.sync_classic_era.get()
        }
    @async_handler
    async def _auto_pull(self):
        if not self._validate_inputs():
            return
        
        try:
            controller = self._get_sync_controller()
            await controller.pull(
                self._get_enabled_versions(),
                self.sync_config_wtf.get(),
                self.selected_accounts,
                self.selected_characters,
                self.available_characters
            )
            self.log("Auto-sync: Pull completed")
        except Exception as e:
            self.log(f"Auto-sync pull error: {e}")
    
    @async_handler
    async def _auto_push(self):
        if not self._validate_inputs():
            return
        
        try:
            controller = self._get_sync_controller()
            await controller.push(
                self._get_enabled_versions(),
                self.sync_config_wtf.get(),
                self.selected_accounts,
                self.selected_characters,
                self.available_characters
            )
            self.log("Auto-sync: Push completed")
        except Exception as e:
            self.log(f"Auto-sync push error: {e}")
    
    def _scan_wow_directory(self):
        if not self.wow_path.get() or not Path(self.wow_path.get()).exists():
            messagebox.showerror("Error", "Please set a valid WoW installation path first")
            return False
        
        sync_mgr = DirectoryManager(Path(self.wow_path.get()), LOCAL_REPO_PATH, self.log)
        self.available_versions, self.available_accounts, self.available_characters = sync_mgr.scan_directory()
        return True
    
    def _open_character_dialog(self):
        if not self._scan_wow_directory():
            return
        
        if not self.available_versions:
            messagebox.showinfo("No Data", "No WoW versions found in the installation directory")
            return
        
        version_enabled = {
            '_retail_': self.sync_retail.get(),
            '_classic_': self.sync_classic.get(),
            '_classic_era_': self.sync_classic_era.get()
        }
        
        def on_save(selected_accounts, selected_characters):
            self.selected_accounts = selected_accounts
            self.selected_characters = selected_characters
            self._update_selection_status()
            self._auto_save()
        
        CharacterDialog(self.root, self.available_versions, self.available_characters,
                       self.selected_characters, version_enabled, on_save)
    
    def _update_selection_status(self):
        chars_dict = {k: v for k, v in self.selected_characters.items() if k != '_explicit_selection'}
        total_chars = sum(len(chars) for chars in chars_dict.values())
        
        has_explicit_selection = '_explicit_selection' in self.selected_characters
        
        if not has_explicit_selection:
            status = "(All characters)"
        elif total_chars == 0:
            status = "(No characters selected)"
        else:
            status = f"({total_chars} character(s) selected)"
        
        self.selection_status_label.config(text=status)
    
    def _update_button_visibility(self):
        repo_exists = LOCAL_REPO_PATH.exists()
        
        for widget in self.button_frame.winfo_children():
            widget.pack_forget()
        
        if not repo_exists:
            self.init_button.pack(side=tk.LEFT, padx=5)
        else:
            self.pull_button.pack(side=tk.LEFT, padx=5)
            self.push_button.pack(side=tk.LEFT, padx=5)
    
    def _validate_inputs(self):
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
    
    def _update_button_visibility(self):
        repo_exists = LOCAL_REPO_PATH.exists()
        
        for widget in self.button_frame.winfo_children():
            widget.pack_forget()
        
        if not repo_exists:
            self.init_button.pack(side=tk.LEFT, padx=5)
        else:
            self.pull_button.pack(side=tk.LEFT, padx=5)
            self.push_button.pack(side=tk.LEFT, padx=5)
    
    @async_handler
    async def _init_repo(self):
        if not self._validate_inputs():
            return
        
        try:
            controller = self._get_sync_controller()
            await controller.init_repo()
            self._update_button_visibility()
            messagebox.showinfo("Success", "Repository initialized successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize repository:\n{e}")
    
    @async_handler
    async def _pull_from_remote(self):
        if not self._validate_inputs():
            return
        
        try:
            controller = self._get_sync_controller()
            await controller.pull(
                self._get_enabled_versions(),
                self.sync_config_wtf.get(),
                self.selected_accounts,
                self.selected_characters,
                self.available_characters
            )
            messagebox.showinfo("Success", "Successfully pulled changes from remote and updated WoW!")
        except Exception as e:
            if "MERGE_CONFLICT" in str(e):
                await self._handle_merge_conflict()
            else:
                messagebox.showerror("Error", f"Failed to pull from remote:\n{e}")
    
    async def _handle_merge_conflict(self):
        from ..git_manager import GitManager
        
        self.log("Merge conflict detected - user intervention required")
        
        response = messagebox.askyesnocancel(
            "Merge Conflict",
            "Conflict detected between local and remote changes.\n\n"
            "YES: Use remote changes (discard local)\n"
            "NO: Keep local changes (discard remote)\n"
            "CANCEL: Abort (manual resolution needed)"
        )
        
        if response is None:
            self.log("Conflict resolution cancelled by user")
            messagebox.showwarning(
                "Manual Resolution Required",
                f"Merge conflict not resolved.\n\nRepository location: {LOCAL_REPO_PATH}\n\n"
                f"You may need to resolve conflicts manually or delete the local repository to start fresh."
            )
            return
        
        try:
            controller = self._get_sync_controller()
            git_mgr = GitManager(self.git_repo_url.get(), self.log)
            repo = git_mgr.init_or_clone()
            
            await controller.resolve_conflict(
                repo, git_mgr, response,
                self._get_enabled_versions(),
                self.sync_config_wtf.get(),
                self.selected_accounts,
                self.selected_characters,
                self.available_characters
            )
            
            if response:
                messagebox.showinfo("Success", "Remote changes applied successfully!")
            else:
                messagebox.showinfo("Success", "Local changes kept. You may want to push your changes.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to resolve conflict:\n{e}")
    
    @async_handler
    async def _push_to_remote(self):
        if not self._validate_inputs():
            return
        
        try:
            controller = self._get_sync_controller()
            has_changes = await controller.push(
                self._get_enabled_versions(),
                self.sync_config_wtf.get(),
                self.selected_accounts,
                self.selected_characters,
                self.available_characters
            )
            
            if has_changes:
                messagebox.showinfo("Success", "Successfully pushed changes to remote!")
            else:
                messagebox.showinfo("Info", "No changes to push - everything is up to date")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to push to remote:\n{e}")
