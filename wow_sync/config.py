import json
from pathlib import Path
from typing import Dict, Any
from .constants import CONFIG_FILE, WOW_SYNC_DIR


class ConfigManager:
    def __init__(self):
        WOW_SYNC_DIR.mkdir(parents=True, exist_ok=True)
        self.config_file = CONFIG_FILE
        self.data = self.load()
    
    def load(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save(self, config: Dict[str, Any]):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise Exception(f"Error saving config: {e}")
    
    def get(self, key: str, default=None):
        return self.data.get(key, default)
    
    def update(self, updates: Dict[str, Any]):
        self.data.update(updates)
        self.save(self.data)
