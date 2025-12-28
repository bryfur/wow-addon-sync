from pathlib import Path
from typing import Callable

from .git_manager import GitManager
from .directory_manager import DirectoryManager
from .constants import LOCAL_REPO_PATH


class SyncController:
    def __init__(self, wow_path: Path, git_repo_url: str, log_callback: Callable):
        self.wow_path = wow_path
        self.git_repo_url = git_repo_url
        self.log = log_callback
        
    async def init_repo(self):
        self.log("Initializing repository...")
        git_mgr = GitManager(self.git_repo_url, self.log)
        git_mgr.init_or_clone()
    
    async def pull(self, enabled_versions: dict, sync_config_wtf: bool, 
                   selected_accounts: dict, selected_characters: dict,
                   available_characters: dict):
        self.log("Pulling from remote repository...")
        
        git_mgr = GitManager(self.git_repo_url, self.log)
        repo = git_mgr.init_or_clone()
        
        git_mgr.pull(repo)
        
        self.log("Applying changes to WoW installation...")
        sync_mgr = DirectoryManager(self.wow_path, LOCAL_REPO_PATH, self.log)
        sync_mgr.copy_from_repo(enabled_versions, sync_config_wtf,
                               selected_accounts, selected_characters,
                               available_characters)
        
        self.log("Pull and sync completed successfully!")
    
    async def push(self, enabled_versions: dict, sync_config_wtf: bool,
                   selected_accounts: dict, selected_characters: dict,
                   available_characters: dict):
        self.log("Copying WoW data to repository...")
        
        git_mgr = GitManager(self.git_repo_url, self.log)
        repo = git_mgr.init_or_clone()
        
        sync_mgr = DirectoryManager(self.wow_path, LOCAL_REPO_PATH, self.log)
        paths_to_sync = sync_mgr.get_sync_paths(enabled_versions)
        sync_mgr.copy_to_repo(paths_to_sync, sync_config_wtf,
                             selected_accounts, selected_characters,
                             available_characters)
        
        self.log("Committing changes...")
        return git_mgr.push(repo)
    
    async def resolve_conflict(self, repo, git_mgr: GitManager, use_remote: bool,
                              enabled_versions: dict, sync_config_wtf: bool,
                              selected_accounts: dict, selected_characters: dict,
                              available_characters: dict):
        git_mgr.resolve_conflict(repo, use_remote=use_remote)
        
        if use_remote:
            sync_mgr = DirectoryManager(self.wow_path, LOCAL_REPO_PATH, self.log)
            sync_mgr.copy_from_repo(enabled_versions, sync_config_wtf,
                                   selected_accounts, selected_characters,
                                   available_characters)
            self.log("Conflict resolved - remote changes applied")