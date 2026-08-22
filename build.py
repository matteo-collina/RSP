#!/usr/bin/env python3
"""
RSP Build Script
Builds the self-contained RSP application with PyInstaller via rsp.spec:
a single-file RSP.exe on Windows, an RSP.app bundle (optionally packaged
as a DMG) on macOS. All bundle metadata lives in config/settings.py.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Import the app's own metadata regardless of where build.py was invoked
# from. rsp.spec loads the same module, so every name, version and copyright
# the bundles carry has a single source.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import APP_NAME, APP_VERSION

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

# Where PyInstaller leaves the finished product on each platform.
WINDOWS_EXE = Path("dist/RSP.exe")
MACOS_APP = Path("dist/RSP.app")
MACOS_BINARY = MACOS_APP / "Contents" / "MacOS" / "RSP"

def print_banner():
    """Print build banner."""
    print("=" * 60)
    print(f"🚀 {APP_NAME} {APP_VERSION} Builder")
    print(f"   Building self-contained application for {platform.system()}...")
    print("=" * 60)

def check_requirements():
    """Check if all build requirements are installed."""
    print("\n📋 Checking build requirements...")

    try:
        import PyInstaller
        print(f"✅ PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller installed successfully")

    # Check main dependencies
    dependencies = [
        ("PyQt6", "PyQt6"),
        ("opencv-python", "cv2"),
        ("numpy", "numpy"),
        ("Pillow", "PIL"),
        ("torch", "torch"),
    ]
    for dep_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"✅ {dep_name}: Found")
        except ImportError:
            print(f"❌ {dep_name}: Missing - install with: pip install {dep_name}")
            return False

    return True

def clean_build_directories():
    """Clean previous build artifacts."""
    print("\n🧹 Cleaning build directories...")

    for dir_name in ("build", "dist", "__pycache__"):
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Removed: {dir_name}/")

    # Clean .pyc files, skipping dot-directories (.git, .venv, ...)
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if file.endswith(".pyc"):
                os.remove(os.path.join(root, file))

    print("✅ Build directories cleaned")

def create_macos_icon():
    """Build assets/app_icon.icns from the 1024px macOS icon artwork.

    PyInstaller can convert a PNG itself, but only via Pillow and only into a
    single-resolution icon; iconutil produces a proper multi-resolution .icns
    so the app looks right in the Dock, Finder and Cmd-Tab alike.
    """
    if not IS_MACOS:
        return

    print("\n🎨 Creating macOS app icon...")

    # The Dark variant (dark rounded-square background) matches the app's own
    # dark theme. An .icns holds a single static image -- macOS only swaps
    # light/dark icon variants for the Icon Composer .icon format, which needs
    # Xcode to compile and PyInstaller can't consume -- so this picks one.
    source = Path("assets/icon/icon-macOS-Dark-1024x1024@2x.png")
    if not source.exists():
        source = Path("assets/app_icon.png")
    target = Path("assets/app_icon.icns")

    if not source.exists():
        print("⚠️  No icon artwork found - building without a custom icon")
        return

    if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        print(f"✅ Icon up to date: {target}")
        return

    if shutil.which("iconutil") is None or shutil.which("sips") is None:
        print("⚠️  iconutil/sips unavailable - PyInstaller will convert the PNG")
        return

    iconset = Path("build/app_icon.iconset")
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)

    try:
        for size in (16, 32, 64, 128, 256, 512):
            for scale, suffix in ((1, f"{size}x{size}"), (2, f"{size}x{size}@2x")):
                subprocess.run(
                    ["sips", "-z", str(size * scale), str(size * scale),
                     str(source), "--out", str(iconset / f"icon_{suffix}.png")],
                    check=True, capture_output=True,
                )
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(target)],
            check=True, capture_output=True, text=True,
        )
        print(f"✅ Icon created: {target}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Icon generation failed ({e.stderr}) - falling back to the PNG")
        if target.exists():
            target.unlink()
    finally:
        shutil.rmtree(iconset, ignore_errors=True)

def build_executable():
    """Run PyInstaller on rsp.spec, which handles both platforms."""
    print("\n🔨 Building executable...")

    cmd = [sys.executable, "-m", "PyInstaller", "rsp.spec"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed:")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Error: {e.stderr}")
        return False

def find_executable():
    """Return the path of the built binary, or None if it isn't there.

    The .app's inner binary is the one to run for CLI mode: `open RSP.app`
    detaches and swallows stdout, so it's useless for testing.
    """
    for path in (MACOS_BINARY, WINDOWS_EXE):
        if path.is_file():
            return path
    return None

def directory_size_mb(path):
    """Total size of a file or directory tree, in MB.

    Symlinks are skipped: an .app bundle is full of them (PyInstaller
    cross-links Contents/Frameworks and Contents/Resources), and following
    them counts most of the payload twice.
    """
    path = Path(path)
    if path.is_symlink():
        return 0.0
    if path.is_file():
        return path.stat().st_size / (1024 * 1024)
    total = sum(f.stat().st_size for f in path.rglob("*")
                if f.is_file() and not f.is_symlink())
    return total / (1024 * 1024)

def verify_signature():
    """Check the .app's code signature, ad-hoc signing it if it has none.

    PyInstaller ad-hoc signs the bundle it creates, but any post-build edit
    (or a stripped/UPX'd binary) invalidates that, and macOS refuses to
    launch a bundle whose signature is broken -- reporting it, unhelpfully,
    as "damaged".
    """
    if not IS_MACOS or not MACOS_APP.exists() or shutil.which("codesign") is None:
        return

    print("\n🔏 Verifying code signature...")
    result = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(MACOS_APP)],
                            capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Signature valid")
        return

    print("⚠️  Signature invalid or missing - re-signing ad-hoc...")
    identity = os.environ.get("RSP_CODESIGN_IDENTITY", "-")
    result = subprocess.run(
        ["codesign", "--force", "--deep", "--sign", identity, str(MACOS_APP)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"✅ Signed with identity: {identity}")
    else:
        print(f"⚠️  Signing failed: {result.stderr.strip()}")

def create_dmg():
    """Package dist/RSP.app into a distributable disk image."""
    if not MACOS_APP.exists():
        print("❌ dist/RSP.app not found - nothing to package")
        return False

    if shutil.which("hdiutil") is None:
        print("⚠️  hdiutil unavailable - skipping DMG")
        return False

    print("\n💿 Creating disk image...")

    staging = Path("build/dmg")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.copytree(MACOS_APP, staging / MACOS_APP.name, symlinks=True)
    # The customary drag-to-install target.
    (staging / "Applications").symlink_to("/Applications")

    dmg_path = Path(f"dist/RSP-{platform.machine()}.dmg")
    if dmg_path.exists():
        dmg_path.unlink()

    try:
        subprocess.run(
            ["hdiutil", "create", "-volname", "RSP", "-srcfolder", str(staging),
             "-ov", "-format", "UDZO", str(dmg_path)],
            check=True, capture_output=True, text=True,
        )
        print(f"✅ Disk image created: {dmg_path} ({directory_size_mb(dmg_path):.1f} MB)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ DMG creation failed: {e.stderr}")
        return False
    finally:
        shutil.rmtree(staging, ignore_errors=True)

def test_executable():
    """Test the built executable."""
    print("\n🧪 Testing executable...")

    exe_path = find_executable()

    if not exe_path:
        print("❌ Executable not found in dist/ directory")
        return False

    # Test CLI help
    try:
        result = subprocess.run([str(exe_path), "--help"],
                              capture_output=True, text=True, timeout=60)
        if APP_NAME in result.stdout:
            print("✅ CLI interface working")
        else:
            print("⚠️  CLI test unclear - check manually")
    except subprocess.TimeoutExpired:
        print("⚠️  CLI test timed out - may be normal")
    except Exception as e:
        print(f"⚠️  CLI test failed: {e}")

    # Check size of the whole deliverable, not just the launcher stub
    target = MACOS_APP if MACOS_APP.exists() else exe_path
    print(f"📊 {target.name} size: {directory_size_mb(target):.1f} MB")

    return True

def main():
    """Main build function."""
    print_banner()

    # Change to script directory
    os.chdir(Path(__file__).parent)

    try:
        if not check_requirements():
            print("❌ Build requirements not met")
            return 1

        clean_build_directories()
        create_macos_icon()

        if not build_executable():
            return 1

        verify_signature()
        tests_passed = test_executable()

        if MACOS_APP.exists():
            if input("\nPackage as a .dmg for distribution? (y/N): ").strip().lower() == "y":
                create_dmg()

        if tests_passed:
            print("\n🎉 Build completed successfully!")
            built = MACOS_APP if MACOS_APP.exists() else find_executable()
            if built:
                print(f"   📁 {'Application' if built == MACOS_APP else 'Executable'}: {built}")
            print("\n   Ready for distribution! 🚀")
        else:
            print("\n⚠️  Build completed but tests failed")

        return 0

    except KeyboardInterrupt:
        print("\n❌ Build cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Build failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
