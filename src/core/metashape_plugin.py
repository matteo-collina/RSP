"""
Install the RSP Metashape plugin into Metashape's startup scripts folder.

Metashape runs every script in that folder at launch, so the plugin's
loader goes in as startup.py next to the rsp_plugin/ package and
scalebars.csv it imports and reads from its own folder. Pure Python (no Qt),
shared by the GUI's Install RSP Metashape Plugin dialog.
"""

import os
import platform
import shutil
from pathlib import Path

PACKAGE_DIR = "rsp_plugin"
LOADER_FILE = "rsp_plugin_loader.py"
SCALEBARS_FILE = "scalebars.csv"
STARTUP_FILE = "startup.py"

# First line of rsp_plugin_loader.py's docstring; tells our own startup.py
# apart from one the user wrote themselves.
_LOADER_MARKER = "RSP plugin loader."


def default_scripts_dir(system=None):
    """Metashape Pro's startup scripts folder for this OS, or None if the OS
    is unsupported (or %APPDATA% is unset on Windows)."""
    system = system or platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        return Path(appdata) / "Agisoft" / "Metashape Pro" / "scripts"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Agisoft" / "Metashape Pro" / "scripts"
    if system == "Linux":
        return Path.home() / ".local" / "share" / "Agisoft" / "Metashape Pro" / "scripts"
    return None


def missing_source_files(source_dir):
    """Names of plugin files absent from source_dir (empty if complete)."""
    source_dir = Path(source_dir)
    required = [(PACKAGE_DIR, Path.is_dir), (LOADER_FILE, Path.is_file), (SCALEBARS_FILE, Path.is_file)]
    return [name for name, exists in required if not exists(source_dir / name)]


def has_foreign_startup(target_dir):
    """True if target_dir already holds a startup.py that isn't ours."""
    startup = Path(target_dir) / STARTUP_FILE
    if not startup.is_file():
        return False
    try:
        return _LOADER_MARKER not in startup.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True


def install_plugin(source_dir, target_dir):
    """Copy the plugin from source_dir into target_dir, replacing any
    previous RSP install there.

    A startup.py that isn't ours is kept as startup.py.bak rather than
    overwritten. A leftover rsp_plugin_loader.py from a manual install is
    removed, since Metashape would otherwise load the plugin twice.

    Returns a list of human-readable notes about what was done. Raises
    FileNotFoundError if source_dir is incomplete, OSError on copy failure.
    """
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)

    missing = missing_source_files(source_dir)
    if missing:
        raise FileNotFoundError(f"Plugin files missing from {source_dir}: {', '.join(missing)}")

    target_dir.mkdir(parents=True, exist_ok=True)
    notes = []

    startup = target_dir / STARTUP_FILE
    if has_foreign_startup(target_dir):
        backup = startup.with_name(STARTUP_FILE + ".bak")
        shutil.copy2(startup, backup)
        notes.append(f"Your existing {STARTUP_FILE} was backed up as {backup.name}.")

    package_target = target_dir / PACKAGE_DIR
    if package_target.exists():
        shutil.rmtree(package_target)
    shutil.copytree(
        source_dir / PACKAGE_DIR,
        package_target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    shutil.copy2(source_dir / SCALEBARS_FILE, target_dir / SCALEBARS_FILE)
    shutil.copy2(source_dir / LOADER_FILE, startup)

    old_loader = target_dir / LOADER_FILE
    if old_loader.exists():
        old_loader.unlink()
        notes.append(f"Removed an older {LOADER_FILE} so the plugin isn't loaded twice.")

    return notes
