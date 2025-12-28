# GitHub Copilot Instructions for WoW Addon Sync

## Project Overview

WoW Addon Sync is a cross-platform GUI application for syncing World of Warcraft addons and settings using Git. The application supports Windows, macOS, and Linux, and manages sync for Retail, Classic, and Classic Era WoW versions.

### Architecture

- **Language**: Python 3.7+
- **GUI Framework**: tkinter with sv-ttk theme
- **Git Integration**: pygit2 library
- **Platform Detection**: darkdetect for theme support
- **System Tray**: Platform-specific implementations (pywin32, pyobjc, dbus-fast)

### Key Components

- `wow_sync/ui/` - GUI components (tkinter-based)
- `wow_sync/tray/` - System tray implementations (platform-specific)
- `wow_sync/sync_controller.py` - Main sync orchestration logic
- `wow_sync/git_manager.py` - Git operations wrapper
- `wow_sync/directory_manager.py` - File system operations
- `wow_sync/config.py` - Configuration management
- `wow_sync/constants.py` - Application constants

## Coding Standards

### Python Style

- Follow PEP 8 conventions for Python code
- Use type hints where applicable (Python 3.7+ compatible)
- Prefer `pathlib.Path` for file system operations over string paths
- Use async/await patterns for long-running operations to keep GUI responsive

### File Organization

- Keep platform-specific code isolated in separate modules
- Use factory patterns for platform-specific implementations (see `tray/__init__.py`)
- Maintain clear separation between UI, business logic, and system operations

### Error Handling

- Use try/except blocks for file system and Git operations
- Provide user-friendly error messages through the GUI
- Log errors and important operations via the log callback pattern

### Documentation

- Include docstrings for classes and non-trivial functions
- Update README.md for user-facing changes
- Update README-BUILD.md for build-related changes

## Building and Testing

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m wow_sync
```

### Building Executables

Use the provided build script which handles platform-specific configurations:

```bash
python build.py
```

Or use PyInstaller directly with the appropriate icon format:
- Windows: `--icon=icons/icon.ico`
- macOS: `--icon=icons/icon.icns`
- Linux: `--icon=icons/icon.png`

### Testing

- Currently, there is no automated test suite
- Manual testing is required across all three platforms (Windows, macOS, Linux)
- Test the following workflows:
  - Initial setup (WoW path, Git URL)
  - Repository initialization
  - Push to remote
  - Pull from remote
  - System tray functionality
  - Single instance enforcement

## Cross-Platform Considerations

### Critical Platform Differences

1. **File Paths**:
   - Always use `pathlib.Path` for cross-platform compatibility
   - Avoid hardcoded path separators

2. **System Tray**:
   - Windows: Uses `pywin32` for system tray
   - macOS: Uses `pyobjc-framework-Cocoa` for menu bar
   - Linux: Uses `dbus-fast` for system tray

3. **Icons**:
   - Windows requires `.ico` format
   - macOS requires `.icns` format
   - Linux uses `.png` format

4. **GUI Behavior**:
   - Windows: Application can run in background via system tray
   - macOS: Application runs in menu bar
   - Linux: System tray support varies by desktop environment

### Platform-Specific Dependencies

Dependencies are conditionally installed based on platform (see `requirements.txt`):
- `pywin32` - Windows only (system tray support)
- `pyobjc-framework-Cocoa` - macOS only (menu bar support)
- `dbus-fast` - Cross-platform but primarily used for Linux system tray
- All other dependencies (pygit2, sv-ttk, Pillow, etc.) are cross-platform

## Dependency Management

### Adding New Dependencies

1. Add to `requirements.txt` with specific version
2. Use platform conditionals if needed: `; sys_platform == "platform"`
3. Update `build.py` hidden imports if dependency is not auto-detected by PyInstaller
4. Test on all platforms before merging

### Security Considerations

- User WoW settings may contain sensitive information (account/character names)
- Recommend private Git repositories to users
- Handle Git credentials securely (SSH keys, GitHub CLI, or credential managers)
- Never commit or log authentication tokens

## Git and GitHub Workflow

### Authentication

The application supports multiple Git authentication methods:
1. SSH keys (recommended)
2. GitHub CLI (`gh auth`)
3. Git credential managers
4. Personal access tokens for HTTPS

### Code Review

- Keep pull requests focused and small
- Test on at least one platform before requesting review
- Document any platform-specific changes in the PR description

## GUI Framework Usage

### tkinter Best Practices

- Use `async_tkinter_loop` for async operations to prevent UI freezing
- Apply sv-ttk theme for modern appearance
- Use darkdetect to respect system theme preferences
- Keep UI updates on the main thread

### Adding New UI Elements

- Follow existing patterns in `wow_sync/ui/`
- Provide visual feedback for long-running operations
- Use the log callback pattern for status updates
- Ensure proper layout with responsive sizing

## Common Tasks

### Adding a New Feature

1. Identify affected components (UI, sync logic, Git operations)
2. Update relevant modules while maintaining separation of concerns
3. Update configuration schema if needed
4. Test across platforms
5. Update documentation

### Fixing Platform-Specific Bugs

1. Isolate platform-specific code in appropriate modules
2. Use platform detection (`sys.platform`) when necessary
3. Test fix on the specific platform
4. Consider impact on other platforms

### Updating Dependencies

1. Update version in `requirements.txt`
2. Test application functionality
3. Update `build.py` if PyInstaller configuration needs changes
4. Rebuild and test executables on all platforms
