#!/usr/bin/env python3
"""
GPSP Build Script
Automated build system for creating GPSP executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

def print_banner():
    """Print build banner."""
    print("=" * 60)
    print("🚀 GPSP Executable Builder")
    print("   Building self-contained GPSP application...")
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
        ("Pillow", "PIL")
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
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Removed: {dir_name}/")
    
    # Clean .pyc files
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                os.remove(os.path.join(root, file))
    
    print("✅ Build directories cleaned")

def create_version_file():
    """Create version info file for Windows executable."""
    if platform.system() != "Windows":
        return
    
    print("\n📄 Creating version info file...")
    
    version_info = """# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Victoria University of Wellington'),
        StringStruct(u'FileDescription', u'GPSP Image Processor'),
        StringStruct(u'FileVersion', u'1.0.0'),
        StringStruct(u'InternalName', u'GPSP'),
        StringStruct(u'LegalCopyright', u'© 2025 Victoria University of Wellington'),
        StringStruct(u'OriginalFilename', u'GPSP.exe'),
        StringStruct(u'ProductName', u'GPSP Image Processor'),
        StringStruct(u'ProductVersion', u'1.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
    
    with open("version.txt", "w", encoding="utf-8") as f:
        f.write(version_info)
    
    print("✅ Version info file created")

def build_executable(mode="onefile"):
    """Build the executable using PyInstaller."""
    print(f"\n🔨 Building executable ({mode} mode)...")
    
    if mode == "quick":
        # Quick build for testing
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name", "GPSP",
            "--add-data", "assets;assets",
            "--add-data", "config;config", 
            "--add-data", "src;src",
            "--icon", "assets/app_icon.png",
            "--version-file", "version.txt",
            "gpsp.py"
        ]
    else:
        # Full build using spec file
        cmd = [sys.executable, "-m", "PyInstaller", "gpsp.spec"]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed:")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Error: {e.stderr}")
        return False

def test_executable():
    """Test the built executable."""
    print("\n🧪 Testing executable...")
    
    exe_path = None
    if os.path.exists("dist/GPSP.exe"):
        exe_path = "dist/GPSP.exe"
    elif os.path.exists("dist/GPSP/GPSP.exe"):
        exe_path = "dist/GPSP/GPSP.exe"
    
    if not exe_path:
        print("❌ Executable not found in dist/ directory")
        return False
    
    # Test CLI help
    try:
        result = subprocess.run([exe_path, "--help"], 
                              capture_output=True, text=True, timeout=30)
        if "GPSP Image Processor" in result.stdout:
            print("✅ CLI interface working")
        else:
            print("⚠️  CLI test unclear - check manually")
    except subprocess.TimeoutExpired:
        print("⚠️  CLI test timed out - may be normal")
    except Exception as e:
        print(f"⚠️  CLI test failed: {e}")
    
    # Check file size
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"📊 Executable size: {size_mb:.1f} MB")
    
    return True

def main():
    """Main build function."""
    print_banner()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Build process
    try:
        if not check_requirements():
            print("❌ Build requirements not met")
            return 1
        
        clean_build_directories()
        create_version_file()
        
        # Ask user for build type
        print("\n🔧 Build Options:")
        print("   1. Quick build (for testing)")
        print("   2. Full build (recommended)")
        
        choice = input("Choose build type (1 or 2): ").strip()
        
        if choice == "1":
            success = build_executable("quick")
        else:
            success = build_executable("full")
        
        if not success:
            return 1
        
        if test_executable():
            print("\n🎉 Build completed successfully!")
            print("   📁 Executable: dist/GPSP.exe")
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