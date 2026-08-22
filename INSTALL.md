# Image Processor Setup Instructions

## Prerequisites
- Python 3.8 or higher
- Conda (Anaconda or Miniconda)

## Installation Options

### Option 1: Using Conda (Recommended)

1. Create a new conda environment:
```bash
conda env create -f environment.yml
```

2. Activate the environment:
```bash
conda activate rsp
```

3. Run the application:
```bash
python rsp.py              # GUI mode (no arguments)
python rsp.py --help       # CLI mode help
```
4. When you're done using the application:
```bash
conda deactivate
```

#### Updating Dependencies

To update all packages to their latest versions:
```bash
conda env update -f environment.yml --prune
```

### Option 2: Using pip

1. Install requirements:
```bash
pip install -r requirements.txt
```
This pulls PyTorch's default wheel for your platform, which on Windows/Linux
is typically the CUDA build (multiple GB). If you don't have an NVIDIA GPU
(or don't want CUDA installed), install the much smaller CPU-only build
instead, before or after the step above:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

2. Run the application:
```bash
python rsp.py              # GUI mode (no arguments)  
python rsp.py --help       # CLI mode help
```

## Building a standalone application

`build.py` drives PyInstaller through `rsp.spec` and produces a self-contained
application for whichever platform you run it on. Cross-compiling is not
possible: build the Windows executable on Windows, the macOS app on a Mac.
All bundle metadata (name, version, copyright) comes from `config/settings.py`.

```bash
pip install pyinstaller
python build.py
```

### Windows

Produces a single-file `dist/RSP.exe`. The spec replaces every MSVC runtime
DLL PyInstaller collects with the build machine's System32 copies -- a stale
copy harvested from another application shadows the system one and stops
torch from loading.

### macOS

Produces `dist/RSP.app`, a one-dir bundle (not one-file: a one-file app would
re-extract more than a gigabyte of torch on every launch). The build also:

- generates a multi-resolution `assets/app_icon.icns` with `sips`/`iconutil`;
- ad-hoc code-signs the bundle, which macOS requires in order to launch it;
- optionally packages `dist/RSP-<arch>.dmg` with a drag-to-Applications link.

The `.app` is built for the architecture of the build machine -- an Apple
Silicon build won't run on an Intel Mac and vice versa, because torch ships no
universal2 wheel. Build once per architecture if you need to support both.

CLI mode still works inside the bundle:
```bash
dist/RSP.app/Contents/MacOS/RSP --help
```

#### Signing and distribution

An ad-hoc signature is enough to run the app on the machine that built it. To
distribute it, sign with a Developer ID and notarise:

```bash
export RSP_CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export RSP_ENTITLEMENTS_FILE=entitlements.plist   # optional, for hardened runtime
python build.py
```

Without notarisation, users who download the app get Gatekeeper's "damaged and
can't be opened" warning, which is really a quarantine flag:

```bash
xattr -dr com.apple.quarantine /Applications/RSP.app
```


