# WoW Addon & Settings Sync

A cross-platform GUI application for syncing World of Warcraft addons and settings using Git. Supports Windows, macOS, and Linux.

## Features

- 🎮 Sync WoW addons and settings across multiple computers
- 🔄 Support for Retail, Classic, and Classic Era versions
- 🌐 Cross-platform (Windows, macOS, Linux)
- 📦 Uses Git for version control and backup
- 💾 Persistent configuration storage
- 🖥️ Simple, intuitive GUI

## Installation

### Prerequisites

- Python 3.7 or higher
- Git installed and configured on your system

### Steps

1. Clone or download this repository:
```bash
git clone <repository-url>
cd wow-sync
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### First Time Setup

1. Run the application:
```bash
python wow_sync.py
```

2. **Set WoW Installation Path**: Click "Browse" and navigate to your World of Warcraft installation directory
   - Windows: Usually `C:\Program Files (x86)\World of Warcraft`
   - macOS: Usually `/Applications/World of Warcraft`
   - Linux: Depends on your installation (e.g., wine prefix)

3. **Set Git Repository URL**: Enter the URL of your Git repository
   - Example: `https://github.com/yourusername/wow-settings.git`
   - You can create a private repository on GitHub for your settings

4. **Save Configuration**: Click "Save Config" to persist your settings

5. **Initialize Repository**: Click "Initialize Repo" to set up the local Git repository

### Syncing Your Settings

#### Push Changes to Remote (Upload)
After making changes to your addons or settings in WoW:
1. Click "Push to Remote"
2. The app will copy your current WoW settings to the local Git repository
3. Commit the changes
4. Push them to your remote repository

#### Pull Changes from Remote (Download)
To sync settings from another computer:
1. Click "Pull from Remote"
2. The app will download the latest changes from your Git repository
3. Apply them to your WoW installation

## What Gets Synced

The application syncs the following directories for each WoW version found:

- **AddOns**: All installed addons (`Interface/AddOns`)
- **WTF**: All settings, saved variables, and configurations (`WTF`)

Supported WoW versions:
- `_retail_` (Current retail version)
- `_classic_` (Classic WoW)
- `_classic_era_` (Classic Era)

## Configuration

Settings are stored in `~/.wow_sync_config.json` and include:
- WoW installation path
- Git repository URL

The local Git repository is stored in `~/.wow_sync_repo`

## Typical Workflow

### Setting up a new computer:
1. Install the application
2. Set your WoW path and Git repository URL
3. Click "Initialize Repo"
4. Click "Pull from Remote" to download your settings

### After playing WoW:
1. Run the application
2. Click "Push to Remote" to backup your latest settings

### Before playing WoW on another computer:
1. Run the application
2. Click "Pull from Remote" to get the latest settings

## Troubleshooting

### "Repository not found" error
- Make sure your Git repository exists on GitHub/GitLab/etc.
- Verify the repository URL is correct
- Ensure you have push/pull access (may need to configure Git credentials)

### Git authentication issues
You may need to configure Git credentials. Options:
1. Use SSH keys (recommended)
2. Use Git credential manager
3. Use personal access tokens for HTTPS

### WoW path not found
- Make sure you've selected the main World of Warcraft directory
- The directory should contain folders like `_retail_`, `_classic_`, etc.

## Security Note

**Warning**: Your WoW settings may contain sensitive information like:
- Account names
- Character names
- Addon configurations

It's recommended to:
- Use a **private** Git repository
- Be careful about what you share
- Consider using `.gitignore` to exclude specific files if needed

## Platform-Specific Notes

### Windows
- Use forward slashes or escaped backslashes in paths
- Git must be in your PATH

### macOS
- May need to allow Python in Security & Privacy settings
- Git comes pre-installed on most recent versions

### Linux
- Install git via package manager if not already installed
- tkinter may need to be installed separately: `sudo apt install python3-tk` (Ubuntu/Debian)

## License

MIT License - Feel free to modify and distribute

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.
