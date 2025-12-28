import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable


class CharacterDialog:
    def __init__(self, parent, available_versions: Dict, available_characters: Dict,
                 selected_characters: Dict, version_enabled: Dict, 
                 on_save: Callable):
        self.available_versions = available_versions
        self.available_characters = available_characters
        self.selected_characters = selected_characters
        self.version_enabled = version_enabled
        self.on_save = on_save
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Characters to Sync")
        self.dialog.geometry("700x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.character_vars = {}
        self._create_widgets()
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(main_frame, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        self._create_character_list(scrollable_frame)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._create_buttons()
    
    def _create_character_list(self, parent):
        for version_dir, version_name in self.available_versions.items():
            if not self.version_enabled.get(version_dir, False):
                continue
            
            version_chars = {k: v for k, v in self.available_characters.items() 
                           if v['version'] == version_dir}
            if not version_chars:
                continue
            
            version_frame = ttk.LabelFrame(parent, text=version_name, padding="10")
            version_frame.pack(fill=tk.X, padx=5, pady=5)
            
            chars_by_account = {}
            for char_key, char_data in version_chars.items():
                account_server = f"{char_data['account']} - {char_data['server']}"
                if account_server not in chars_by_account:
                    chars_by_account[account_server] = []
                chars_by_account[account_server].append((char_key, char_data['character']))
            
            for account_server, characters in sorted(chars_by_account.items()):
                self._create_collapsible_section(version_frame, version_dir, account_server, characters)
    
    def _create_collapsible_section(self, parent, version_dir, account_server, characters):
        section_frame = ttk.Frame(parent)
        section_frame.pack(fill=tk.X, pady=2)
        
        header_frame = ttk.Frame(section_frame)
        header_frame.pack(fill=tk.X)
        
        chars_container = ttk.Frame(section_frame)
        
        collapsed = tk.BooleanVar(value=False)
        toggle_btn = ttk.Button(header_frame, text="▼", width=3)
        toggle_btn.pack(side=tk.LEFT)
        
        ttk.Label(header_frame, text=account_server, font=('', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        
        def toggle():
            if collapsed.get():
                chars_container.pack_forget()
                toggle_btn.config(text="▶")
                collapsed.set(False)
            else:
                chars_container.pack(fill=tk.X, padx=20)
                toggle_btn.config(text="▼")
                collapsed.set(True)
        
        toggle_btn.config(command=toggle)
        
        for char_key, char_name in sorted(characters, key=lambda x: x[1]):
            has_explicit_selection = '_explicit_selection' in self.selected_characters
            
            if has_explicit_selection:
                default_selected = (version_dir in self.selected_characters and 
                                  char_key in self.selected_characters[version_dir])
            else:
                default_selected = True
            
            var = tk.BooleanVar(value=default_selected)
            self.character_vars[char_key] = var
            ttk.Checkbutton(chars_container, text=char_name, variable=var).pack(anchor=tk.W, padx=5)
        
        chars_container.pack(fill=tk.X, padx=20)
    
    def _create_buttons(self):
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Select All", 
                  command=lambda: [v.set(True) for v in self.character_vars.values()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", 
                  command=lambda: [v.set(False) for v in self.character_vars.values()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="OK", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _save(self):
        selected_accounts = {}
        selected_characters = {'_explicit_selection': True}
        
        for key, var in self.character_vars.items():
            if var.get():
                char_data = self.available_characters[key]
                version_dir = char_data['version']
                account = char_data['account']
                
                if version_dir not in selected_characters:
                    selected_characters[version_dir] = []
                selected_characters[version_dir].append(key)
                
                if version_dir not in selected_accounts:
                    selected_accounts[version_dir] = []
                if account not in selected_accounts[version_dir]:
                    selected_accounts[version_dir].append(account)
        
        self.on_save(selected_accounts, selected_characters)
        self.dialog.destroy()
