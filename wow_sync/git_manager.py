import shutil
import subprocess
import json
from pathlib import Path
import pygit2
from .constants import LOCAL_REPO_PATH, TOKEN_FILE, WOW_SYNC_DIR


class GitManager:
    def __init__(self, repo_url: str, log_callback=None):
        self.repo_url = repo_url
        self.repo_path = LOCAL_REPO_PATH
        self.log = log_callback or print
        self.credentials = self._get_credentials()
        self._cached_token = None
    
    def _get_credentials(self):
        def credential_callback(url, username_from_url, allowed_types):
            if allowed_types & pygit2.GIT_CREDENTIAL_SSH_KEY:
                ssh_key = Path.home() / ".ssh" / "id_rsa"
                ssh_pub = Path.home() / ".ssh" / "id_rsa.pub"
                if ssh_key.exists() and ssh_pub.exists():
                    return pygit2.Keypair("git", str(ssh_pub), str(ssh_key), "")
            
            if allowed_types & pygit2.GIT_CREDENTIAL_USERPASS_PLAINTEXT:
                if self._cached_token:
                    return pygit2.UserPass(self._cached_token, "x-oauth-basic")
                
                token = self._get_github_token()
                if token:
                    self._cached_token = token
                    return pygit2.UserPass(token, "x-oauth-basic")
            
            return None
        
        return pygit2.RemoteCallbacks(credentials=credential_callback)
    
    def _get_github_token(self):
        if 'github.com' not in self.repo_url.lower():
            return None
        
        try:
            result = subprocess.run(['gh', 'auth', 'token'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                self.log("Using GitHub CLI authentication")
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE) as f:
                    data = json.load(f)
                    token = data.get('access_token')
                    if token:
                        self.log("Using cached GitHub token")
                        return token
            except Exception:
                pass
        
        try:
            import tkinter as tk
            
            dialog = tk.Toplevel()
            dialog.title("GitHub Authentication")
            dialog.geometry("500x280")
            dialog.resizable(False, False)
            
            frame = tk.Frame(dialog, padx=20, pady=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            tk.Label(frame, text="GitHub Personal Access Token needed", 
                    font=("", 10, "bold")).pack(pady=(0, 10))
            
            text = tk.Text(frame, height=5, width=55, wrap=tk.WORD, 
                          relief=tk.FLAT, bg=dialog.cget('bg'))
            text.pack(pady=5)
            
            text.insert("1.0", "1. Go to: ")
            text.insert("end", "https://github.com/settings/personal-access-tokens/new", "link")
            text.insert("end", "\n2. Set expiration and repository access")
            text.insert("end", "\n3. Repository permissions: Contents (Read and write)")
            text.insert("end", "\n4. Generate and copy the token below")
            
            text.tag_config("link", foreground="blue", underline=True)
            text.tag_bind("link", "<Button-1>", 
                         lambda e: __import__('webbrowser').open('https://github.com/settings/personal-access-tokens/new'))
            text.tag_bind("link", "<Enter>", lambda e: text.config(cursor="hand2"))
            text.tag_bind("link", "<Leave>", lambda e: text.config(cursor=""))
            text.config(state=tk.DISABLED)
            
            tk.Label(frame, text="Paste your token:").pack(pady=(15, 5))
            
            token_var = tk.StringVar()
            entry = tk.Entry(frame, textvariable=token_var, width=50, show='*')
            entry.pack(pady=5)
            entry.focus_set()
            
            result = {'token': None}
            
            def on_ok():
                result['token'] = token_var.get()
                dialog.destroy()
            
            def on_cancel():
                dialog.destroy()
            
            btn_frame = tk.Frame(frame)
            btn_frame.pack(pady=15)
            tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
            tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
            
            entry.bind('<Return>', lambda e: on_ok())
            entry.bind('<Escape>', lambda e: on_cancel())
            
            dialog.transient()
            dialog.grab_set()
            dialog.wait_window()
            
            token = result['token']
            if token:
                try:
                    WOW_SYNC_DIR.mkdir(parents=True, exist_ok=True)
                    with open(TOKEN_FILE, 'w') as f:
                        json.dump({'access_token': token}, f)
                    TOKEN_FILE.chmod(0o600)
                    self.log("Token saved for future use")
                except Exception:
                    pass
                return token
        except Exception:
            pass
        
        return None
    
    def init_or_clone(self):
        if self.repo_path.exists():
            try:
                repo = pygit2.Repository(str(self.repo_path))
                self._ensure_git_config(repo)
                self.log("Existing repository loaded")
                return repo
            except Exception:
                self.log("Directory exists but is not a git repo, removing...")
                shutil.rmtree(self.repo_path)
        
        return self.clone()
    
    def _ensure_git_config(self, repo):
        """Ensure git user.name and user.email are configured."""
        config = repo.config
        
        # Check if user.name exists
        try:
            config['user.name']
        except KeyError:
            # Set default name
            config['user.name'] = 'WoW Sync'
            self.log("Set git user.name to 'WoW Sync'")
        
        # Check if user.email exists
        try:
            config['user.email']
        except KeyError:
            # Set default email
            config['user.email'] = 'wowsync@local'
            self.log("Set git user.email to 'wowsync@local'")
        
        # Disable file mode tracking (ignore permission changes)
        # This prevents spurious changes on macOS/Linux
        try:
            if config['core.filemode']:
                config['core.filemode'] = False
                self.log("Disabled file mode tracking")
        except KeyError:
            config['core.filemode'] = False
            self.log("Disabled file mode tracking")
    
    def clone(self):
        self.log(f"Cloning repository from {self.repo_url}...")
        try:
            repo = pygit2.clone_repository(self.repo_url, str(self.repo_path), callbacks=self.credentials)
            self._ensure_git_config(repo)
            self.log("Repository cloned successfully")
            return repo
        except Exception as e:
            if "exists and is not an empty directory" in str(e):
                self.log("Repository already exists")
                repo = pygit2.Repository(str(self.repo_path))
                self._ensure_git_config(repo)
                return repo
            else:
                self.log("Remote repository not found, creating new local repository...")
                return self._create_new_repo()
    
    def _create_new_repo(self):
        self.repo_path.mkdir(parents=True, exist_ok=True)
        repo = pygit2.init_repository(str(self.repo_path))
        
        # Ensure git config is set before making commits
        self._ensure_git_config(repo)
        
        gitignore_path = self.repo_path / '.gitignore'
        with open(gitignore_path, 'w') as f:
            f.write("# WoW Sync\n*.bak\n*.tmp\n")
        
        index = repo.index
        index.add('.gitignore')
        index.write()
        
        tree = index.write_tree()
        sig = repo.default_signature
        repo.create_commit('HEAD', sig, sig, "Initial commit", tree, [])
        
        try:
            repo.remotes.create('origin', self.repo_url)
            self.log("Remote 'origin' added")
        except Exception:
            self.log("Remote 'origin' already exists")
        
        self.log("New repository created")
        return repo
    
    def pull(self, repo):
        remote = repo.remotes['origin']
        remote.fetch(callbacks=self.credentials)
        
        remote_branch = repo.lookup_branch('origin/master', pygit2.GIT_BRANCH_REMOTE)
        if not remote_branch:
            remote_branch = repo.lookup_branch('origin/main', pygit2.GIT_BRANCH_REMOTE)
        
        if not remote_branch:
            return
        
        merge_result, _ = repo.merge_analysis(remote_branch.target)
        
        if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
            self.log("Already up to date")
        elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
            try:
                repo.checkout_tree(repo.get(remote_branch.target), strategy=pygit2.GIT_CHECKOUT_FORCE)
                
                branch_name = 'master' if 'master' in remote_branch.branch_name else 'main'
                local_branch_ref = f'refs/heads/{branch_name}'
                
                try:
                    master_ref = repo.lookup_reference(local_branch_ref)
                    master_ref.set_target(remote_branch.target)
                except KeyError:
                    master_ref = repo.create_reference(local_branch_ref, remote_branch.target)
                
                repo.set_head(local_branch_ref)
                self.log("Pull successful")
            except Exception as e:
                if "conflicts prevent checkout" in str(e):
                    self.log("Local changes conflict with remote. Using remote version...")
                    repo.reset(remote_branch.target, pygit2.GIT_RESET_HARD)
                    self.log("Pull successful (local changes discarded)")
                else:
                    raise
        elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
            repo.merge(remote_branch.target)
            
            if repo.index.conflicts:
                raise Exception("MERGE_CONFLICT")
            
            tree = repo.index.write_tree()
            sig = repo.default_signature
            repo.create_commit('HEAD', sig, sig, 'Merge from remote', tree, 
                             [repo.head.target, remote_branch.target])
            repo.state_cleanup()
            self.log("Pull successful")
    
    def push(self, repo):
        index = repo.index
        index.add_all()
        index.write()
        
        if not repo.diff('HEAD'):
            self.log("No changes to commit")
            return False
        
        tree = index.write_tree()
        sig = repo.default_signature
        repo.create_commit('HEAD', sig, sig, "Update WoW addons and settings", tree, [repo.head.target])
        self.log("Changes committed")
        
        remote = repo.remotes['origin']
        remote.push([repo.head.name], callbacks=self.credentials)
        self.log("Push completed successfully!")
        return True
    
    def resolve_conflict(self, repo, use_remote: bool):
        if use_remote:
            self.log("Resolving conflict: using remote changes...")
            remote_branch = repo.lookup_branch('origin/master', pygit2.GIT_BRANCH_REMOTE)
            if not remote_branch:
                remote_branch = repo.lookup_branch('origin/main', pygit2.GIT_BRANCH_REMOTE)
            
            repo.checkout_tree(repo.get(remote_branch.target))
            repo.head.set_target(remote_branch.target)
            repo.state_cleanup()
            self.log("Applied remote changes")
        else:
            self.log("Resolving conflict: keeping local changes...")
            repo.state_cleanup()
            self.log("Kept local changes")
