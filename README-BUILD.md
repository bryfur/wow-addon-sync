# Building WoW Sync for Distribution

## Prerequisites

Install PyInstaller in your virtual environment:

```bash
pip install pyinstaller
```

## Quick Build

### Option 1: Using the build script (recommended)

```bash
python build.py
```

### Option 2: Using the spec file

```bash
pyinstaller WoWSync.spec
```

### Option 3: Manual PyInstaller command

```bash
pyinstaller --name=WoWSync \
    --onefile \
    --windowed \
    --icon=icons/icon.png \
    --add-data="icons:icons" \
    wow_sync/__main__.py
```

## Platform-Specific Notes

### Windows
- Creates: `dist/WoWSync.exe`
- GUI application (no console window)
- Requires: Windows 10 or later
- Consider creating an installer with Inno Setup or NSIS

### macOS
- Creates: `dist/WoWSync.app` (if using BUNDLE in spec)
- Or: `dist/WoWSync` (single executable)
- May need to sign the app for distribution
- Create DMG with: `hdiutil create -volname "WoW Sync" -srcfolder dist/WoWSync.app -ov -format UDZO WoWSync.dmg`
- **Note**: GitHub Actions builds create separate artifacts for Intel (macOS 13) and Apple Silicon (ARM) architectures

### Linux
- Creates: `dist/WoWSync`
- Console application (can be hidden in .desktop file)
- Consider packaging as:
  - AppImage: Universal Linux package
  - .deb: Debian/Ubuntu
  - .rpm: Fedora/RHEL
  - Flatpak: Cross-distro sandboxed app

## Output Location

Built executables are in the `dist/` folder.

## Clean Build

To remove build artifacts:

```bash
rm -rf build/ dist/ *.spec __pycache__/
find . -type d -name __pycache__ -exec rm -rf {} +
```

## Testing the Build

After building, test the executable:

```bash
# Linux/macOS
./dist/WoWSync

# Windows
dist\WoWSync.exe
```

## Troubleshooting

### Icon not showing
- Ensure icon file exists in `icons/` folder
- Windows: Convert PNG to ICO format
- macOS: Convert PNG to ICNS format

### Missing modules at runtime
- Add to `hiddenimports` in the spec file
- Check PyInstaller warnings during build

### Large file size
- Remove `--onefile` to create a folder distribution
- Use `--exclude-module` for unused packages
- Enable UPX compression (included by default)

### D-Bus issues on Linux
- Ensure `dbus_next` is included
- Test on target Linux distribution

## Creating an Installer

### Windows (Inno Setup)
1. Install Inno Setup
2. Create a script referencing `dist/WoWSync.exe`
3. Compile to create installer

### macOS (DMG)
```bash
create-dmg \
  --volname "WoW Sync" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "WoWSync.app" 175 120 \
  --app-drop-link 425 120 \
  "WoWSync.dmg" \
  "dist/WoWSync.app"
```

### Linux (AppImage)
Use `appimage-builder` or manual AppImage creation tools.

## Distribution Checklist

- [ ] Test on clean system without Python
- [ ] Verify all features work (tray, git, sync)
- [ ] Check file size is reasonable
- [ ] Include LICENSE and README in package
- [ ] Test auto-sync functionality
- [ ] Verify icon displays correctly
- [ ] Test on target OS version

## File Size Optimization

Typical size: 50-80 MB (includes Python runtime + dependencies)

To reduce:
1. Use `--exclude-module` for unused packages
2. Consider folder distribution instead of `--onefile`
3. Strip debug symbols: `--strip`
4. Enable UPX: `--upx-dir=/path/to/upx`
