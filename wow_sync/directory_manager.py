import shutil
import filecmp
import os
from pathlib import Path
from typing import List, Tuple, Dict, Callable
from .constants import VERSION_MAP


class DirectoryManager:
    def __init__(self, wow_path: Path, repo_path: Path, log_callback=None):
        self.wow_path = wow_path
        self.repo_path = repo_path
        self.log = log_callback or print
    
    def scan_directory(self) -> Tuple[Dict, Dict, Dict]:
        available_versions = {}
        available_accounts = {}
        available_characters = {}
        
        for version_dir, version_name in VERSION_MAP.items():
            version_path = self.wow_path / version_dir
            if not version_path.exists():
                continue
            
            available_versions[version_dir] = version_name
            
            wtf_path = version_path / 'WTF' / 'Account'
            if not wtf_path.exists():
                continue
            
            accounts = []
            for account_dir in wtf_path.iterdir():
                if not account_dir.is_dir() or account_dir.name.startswith('.'):
                    continue
                
                accounts.append(account_dir.name)
                
                for server_dir in account_dir.iterdir():
                    if not server_dir.is_dir() or server_dir.name.startswith('.'):
                        continue
                    if server_dir.name == 'SavedVariables':
                        continue
                    
                    for char_dir in server_dir.iterdir():
                        if not char_dir.is_dir() or char_dir.name.startswith('.'):
                            continue
                        
                        char_key = f"{version_dir}:{account_dir.name}:{server_dir.name}:{char_dir.name}"
                        available_characters[char_key] = {
                            'version': version_dir,
                            'account': account_dir.name,
                            'server': server_dir.name,
                            'character': char_dir.name
                        }
            
            if accounts:
                available_accounts[version_dir] = accounts
        
        return available_versions, available_accounts, available_characters
    
    def get_sync_paths(self, enabled_versions: Dict[str, bool]) -> List[Tuple[str, Path, str]]:
        paths_to_sync = []
        
        for version in ['_retail_', '_classic_', '_classic_era_']:
            if not enabled_versions.get(version, False):
                continue
            
            version_path = self.wow_path / version
            if not version_path.exists():
                continue
            
            wtf_path = version_path / 'WTF'
            addons_path = version_path / 'Interface' / 'AddOns'
            
            if wtf_path.exists():
                paths_to_sync.append(('WTF', wtf_path, version))
            if addons_path.exists():
                paths_to_sync.append(('AddOns', addons_path, version))
        
        return paths_to_sync
    
    def copy_to_repo(self, paths_to_sync: List, sync_config_wtf: bool, 
                     selected_accounts: Dict, selected_characters: Dict,
                     available_characters: Dict):
        for sync_type, source_path, version in paths_to_sync:
            dest_path = self.repo_path / version / sync_type
            self.log(f"Syncing {sync_type} from {version}...")
            
            ignore_fn = self._create_ignore_function(
                sync_type, version, sync_config_wtf,
                selected_accounts, selected_characters, available_characters
            )
            
            if dest_path.exists():
                # Use efficient differential copy
                copied_count = self._copy_folder_diff(source_path, dest_path, ignore_fn)
                self.log(f"Updated {copied_count} file(s) in {dest_path}")
            else:
                # First time - full copy
                shutil.copytree(source_path, dest_path, ignore=ignore_fn)
                self.log(f"Copied {source_path} to {dest_path}")
            
            self._log_filters(sync_type, version, sync_config_wtf, selected_accounts, selected_characters)
    
    def copy_from_repo(self, enabled_versions: Dict[str, bool], sync_config_wtf: bool,
                      selected_accounts: Dict, selected_characters: Dict,
                      available_characters: Dict):
        for version_dir in self.repo_path.iterdir():
            if not version_dir.is_dir() or not version_dir.name.startswith('_'):
                continue
            
            if not enabled_versions.get(version_dir.name, False):
                self.log(f"Skipping {version_dir.name} (not selected)")
                continue
            
            version_path = self.wow_path / version_dir.name
            if not version_path.exists():
                self.log(f"Warning: {version_path} does not exist in your WoW installation, skipping...")
                continue
            
            self._copy_wtf(version_dir, version_path, sync_config_wtf, 
                          selected_accounts, selected_characters, available_characters)
            self._copy_addons(version_dir, version_path)
    
    def _copy_wtf(self, version_dir, version_path, sync_config_wtf,
                  selected_accounts, selected_characters, available_characters):
        wtf_source = version_dir / 'WTF'
        if not wtf_source.exists():
            return
        
        wtf_dest = version_path / 'WTF'
        self.log(f"Copying WTF to {version_dir.name}...")
        
        ignore_fn = self._create_ignore_function(
            'WTF', version_dir.name, sync_config_wtf,
            selected_accounts, selected_characters, available_characters
        )
        
        if wtf_dest.exists():
            # Use efficient differential copy
            copied_count = self._copy_folder_diff(wtf_source, wtf_dest, ignore_fn)
            self.log(f"  Updated {copied_count} file(s)")
        else:
            # First time - full copy
            shutil.copytree(wtf_source, wtf_dest, ignore=ignore_fn)
            self.log(f"  Copied WTF files")
        
        self._log_filters('WTF', version_dir.name, sync_config_wtf, selected_accounts, selected_characters)
    
    def _copy_addons(self, version_dir, version_path):
        addons_source = version_dir / 'AddOns'
        if not addons_source.exists():
            return
        
        addons_dest = version_path / 'Interface' / 'AddOns'
        self.log(f"Copying AddOns to {version_dir.name}...")
        
        if addons_dest.exists():
            # Use efficient differential copy
            copied_count = self._copy_folder_diff(addons_source, addons_dest)
            self.log(f"  Updated {copied_count} file(s)")
        else:
            # First time - full copy
            addons_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(addons_source, addons_dest)
            self.log(f"  Copied AddOns files")
    
    def _copy_folder_diff(self, source_dir: Path, dest_dir: Path, ignore_fn=None):
        """Efficiently copy only changed files between directories."""
        copied_count = 0
        
        # Apply ignore function if provided
        ignored_names = set()
        if ignore_fn:
            ignored_names = set(ignore_fn(str(source_dir), [p.name for p in source_dir.iterdir()]))
        
        # Get comparison report
        comparison = filecmp.dircmp(str(source_dir), str(dest_dir), ignore=list(ignored_names))
        
        # 1. Copy missing files/folders from source to destination
        for name in comparison.left_only:
            if name in ignored_names:
                continue
            
            src_path = source_dir / name
            dst_path = dest_dir / name
            
            if src_path.is_dir():
                shutil.copytree(str(src_path), str(dst_path))
                copied_count += sum(1 for _ in src_path.rglob('*') if _.is_file())
            else:
                shutil.copy2(str(src_path), str(dst_path))
                copied_count += 1
        
        # 2. Copy modified files from source to destination
        for name in comparison.diff_files:
            if name in ignored_names:
                continue
            
            src_path = source_dir / name
            dst_path = dest_dir / name
            shutil.copy2(str(src_path), str(dst_path))
            copied_count += 1
        
        # 3. Remove files that exist in destination but not in source (cleanup)
        for name in comparison.right_only:
            dst_path = dest_dir / name
            if dst_path.is_dir():
                shutil.rmtree(str(dst_path))
            else:
                dst_path.unlink()
        
        # 4. Recursively handle subdirectories
        for sub in comparison.common_dirs:
            if sub in ignored_names:
                continue
            
            sub_ignore_fn = None
            if ignore_fn:
                sub_ignore_fn = lambda d, files: ignore_fn(d, files) if str(source_dir / sub) in d else []
            
            copied_count += self._copy_folder_diff(source_dir / sub, dest_dir / sub, sub_ignore_fn)
        
        return copied_count
    
    def _create_ignore_function(self, sync_type, version, sync_config_wtf,
                                selected_accounts, selected_characters, available_characters):
        def ignore_function(dir, files):
            ignored = []
            
            # Exclude _classic_era_ SavedVariables directory
            if sync_type == 'WTF':
                dir_path = Path(dir)
                if dir_path.name == 'WTF':
                    ignored.extend([f for f in files if f == 'SavedVariables' and Path(dir, f).is_dir()])
            
            if not sync_config_wtf and sync_type == 'WTF':
                ignored.extend([f for f in files if f.lower() == 'config.wtf'])
            
            if sync_type == 'WTF' and version in selected_accounts:
                if Path(dir).name == 'Account':
                    selected = selected_accounts[version]
                    ignored.extend([f for f in files if f not in selected and Path(dir, f).is_dir()])
            
            if sync_type == 'WTF' and version in selected_characters:
                dir_path = Path(dir)
                parts = dir_path.parts
                
                if 'Account' in parts:
                    account_idx = parts.index('Account')
                    if len(parts) > account_idx + 2:
                        account = parts[account_idx + 1]
                        server = parts[account_idx + 2]
                        
                        if dir_path.name == server:
                            selected_chars = [
                                available_characters[k]['character']
                                for k in selected_characters[version]
                                if available_characters.get(k, {}).get('account') == account
                                and available_characters.get(k, {}).get('server') == server
                            ]
                            
                            if selected_chars:
                                char_folders = [f for f in files if Path(dir, f).is_dir() and f not in ['.', '..']]
                                ignored.extend([f for f in char_folders if f not in selected_chars])
            
            return ignored
        
        return ignore_function
    
    def _log_filters(self, sync_type, version, sync_config_wtf, selected_accounts, selected_characters):
        filters = []    
        
        if not sync_config_wtf and sync_type == 'WTF':
            filters.append("Config.wtf excluded")
        if version in selected_accounts and sync_type == 'WTF':
            filters.append(f"{len(selected_accounts[version])} account(s)")
        if version in selected_characters and version != '_explicit_selection' and sync_type == 'WTF':
            filters.append(f"{len(selected_characters[version])} character(s)")
        
        if filters:
            self.log(f"  Filters: {', '.join(filters)}")
