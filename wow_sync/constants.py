from pathlib import Path

VERSION_MAP = {
    '_retail_': 'Retail',
    '_classic_': 'Classic',
    '_classic_era_': 'Classic Era'
}

ICON_DIR = Path(__file__).parent.parent / "icons"
WOW_SYNC_DIR = Path.home() / ".wow_sync"
CONFIG_FILE = WOW_SYNC_DIR / "config.json"
LOCAL_REPO_PATH = WOW_SYNC_DIR / "repo"
TOKEN_FILE = WOW_SYNC_DIR / "github_token.json"
LOCK_FILE = WOW_SYNC_DIR / "app.lock"
