# Build Documentation

This document describes the build process for creating distributable WoW Sync executables.

## Requirements

- Python 3.13
- PyInstaller 6.17.0
- Platform-specific dependencies (automatically installed by GitHub Actions)

### Linux Dependencies

```bash
sudo apt-get update
sudo apt-get install -y libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
```

### Python Dependencies

```bash
pip install -r requirements.txt
pip install pyinstaller==6.17.0
```

## Build Process

### Automated Build (Recommended)

The build process is automated via GitHub Actions. All pull requests and pushes to main/master branches trigger builds on:
- Ubuntu Latest
- macOS Latest
- Windows Latest

The workflow file is located at `.github/workflows/build.yml`.

### Local Build

Execute the build script:

```bash
python build.py
```

The script configures PyInstaller with the following parameters:
- Entry point: `wow_sync/__main__.py`
- Build mode: Single file (Windows/Linux), Single directory (macOS)
- GUI mode: No console window
- Icon: `icons/icon.png`
- Included data: Icons directory
- Hidden imports: tkinter, sv_ttk, darkdetect, pygit2, cffi, psutil, PIL, dbus_fast, async_tkinter_loop

### Manual PyInstaller Build

Alternative manual build command:

```bash
pyinstaller --name=WoWSync \
    --onefile \
    --noconsole \
    --icon=icons/icon.png \
    --add-data="icons:icons" \
    --hidden-import=tkinter \
    --hidden-import=sv_ttk \
    --hidden-import=darkdetect \
    --hidden-import=pygit2 \
    --hidden-import=cffi \
    --hidden-import=psutil \
    --hidden-import=PIL \
    --hidden-import=dbus_fast \
    wow_sync/__main__.py
```

Note: The data separator differs by platform (`--add-data="icons;icons"` on Windows).

## Build Artifacts

### Linux
- Executable: `dist/WoWSync`
- Archive: `dist/WoWSync-Linux.tar.gz`

### macOS
- Application bundle: `dist/WoWSync.app`
- Archive: `dist/WoWSync-macOS.zip`

### Windows
- Executable: `dist/WoWSync.exe`
- Archive: `dist/WoWSync-Windows.zip`

## GitHub Actions Workflow

The CI/CD pipeline performs the following steps:
1. Checkout source code
2. Set up Python 3.13
3. Install platform-specific system dependencies
4. Install Python dependencies
5. Execute build script
6. Create platform-specific archive
7. Upload build artifacts

On tagged releases (v*), artifacts are automatically published to GitHub Releases.

## Branch Protection

To ensure build quality, configure the following branch protection rules for main/master:
1. Require status checks before merging
2. Require "Build Status Check" to pass
3. Require branches to be up to date before merging

These settings ensure all pull requests successfully build on all platforms before merge.

## Testing Builds

Test the executable after building:

```bash
# Linux/macOS
./dist/WoWSync

# Windows
dist\WoWSync.exe
```

## Build Artifacts Cleanup

Remove build artifacts and cache:

```bash
rm -rf build/ dist/ *.spec
find . -type d -name __pycache__ -exec rm -rf {} +
```

## Troubleshooting

### Missing Modules
If runtime errors indicate missing modules, add them to the `--hidden-import` list in `build.py`.

### Icon Issues
- Windows: Icon must be .ico format
- macOS: Icon must be .icns format
- Linux: Icon format is flexible

### Large Executable Size
Typical executable size: 50-80 MB (includes Python runtime and dependencies).

To reduce size:
- Use `--exclude-module` for unused packages
- Consider directory-based distribution (`--onedir`)
- Enable UPX compression

### Platform-Specific Issues
- **Linux**: Ensure all GTK and D-Bus dependencies are installed
- **macOS**: Application may require code signing for distribution
- **Windows**: Antivirus software may flag unsigned executables
