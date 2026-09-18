# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for both platforms: a single-file RSP.exe on Windows,
a one-dir RSP.app bundle on macOS. All bundle metadata (name, version,
copyright, bundle id) comes from config/settings.py."""

import importlib.util
import os
import sys

from PyInstaller.utils.hooks import collect_all

IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'


def _load_settings():
    """Load config/settings.py so the bundle metadata comes from one place.

    Loaded by path rather than imported as a package: the spec runs outside
    the application's import context.
    """
    path = os.path.join(SPECPATH, 'config', 'settings.py')
    spec = importlib.util.spec_from_file_location('rsp_settings', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


settings = _load_settings()


def _windows_version_info():
    """Build the Windows version resource from the app's own metadata.

    Constructed here rather than kept in a version.txt so the resource can
    never drift from config/settings.py, whichever way the build is run.
    The import is local: PyInstaller's versioninfo module needs pefile,
    which is only installed on Windows.
    """
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo)

    return VSVersionInfo(
        # filevers/prodvers must be four integers; the string fields carry
        # the full version, suffix included, exactly as the app reports it.
        ffi=FixedFileInfo(
            filevers=settings.APP_VERSION_TUPLE,
            prodvers=settings.APP_VERSION_TUPLE,
        ),
        kids=[
            StringFileInfo([StringTable('040904B0', [
                StringStruct('CompanyName', settings.APP_ORGANIZATION),
                StringStruct('FileDescription', settings.APP_NAME),
                StringStruct('FileVersion', settings.APP_VERSION),
                StringStruct('InternalName', 'RSP'),
                StringStruct('LegalCopyright', settings.APP_COPYRIGHT),
                StringStruct('OriginalFilename', 'RSP.exe'),
                StringStruct('ProductName', settings.APP_NAME),
                StringStruct('ProductVersion', settings.APP_VERSION),
            ])]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])]),
        ],
    )


# torch's dynamic submodule imports and native DLLs are a known
# PyInstaller pain point -- collect_all pulls in everything its own
# hooks know it needs, rather than hand-maintaining a hiddenimports list.
torch_datas, torch_binaries, torch_hiddenimports = collect_all('torch')

a = Analysis(
    ['rsp.py'],
    binaries=torch_binaries,
    # scripts/: the Metashape plugin the Installation Wizard copies out.
    datas=[('assets', 'assets'), ('config', 'config'), ('src', 'src'),
           ('scripts/rsp_plugin', 'scripts/rsp_plugin'),
           ('scripts/rsp_plugin_loader.py', 'scripts'),
           ('scripts/scalebars.csv', 'scripts')] + torch_datas,
    hiddenimports=torch_hiddenimports,
)

if IS_WINDOWS:
    # -----------------------------------------------------------------------
    # MSVC runtime sanitation.
    #
    # PyInstaller resolves binary dependencies by searching the build machine's
    # PATH, so it can harvest msvcp140/vcruntime140 copies from arbitrary
    # installed software (observed: ImageMagick's 14.44 copies), and PyQt6 ships
    # its own ancient copies (14.26) in PyQt6/Qt6/bin. Whichever stale copy lands
    # in the bundle shadows System32's current redistributable at runtime, and
    # torch's c10.dll -- which needs a recent runtime -- then fails to load with
    # "WinError 1114: DLL initialization routine failed". (Verified via
    # Analysis-00.toc source paths and DLL version stamps: bundled 14.44/14.26
    # vs. System32's working 14.50.)
    #
    # Fix: drop every unmangled MSVC runtime copy the analysis collected, from
    # any source and any bundle subdirectory, then explicitly bundle the build
    # machine's System32 copies at the root. A newer runtime satisfies every
    # older consumer (Qt, cv2, numpy, torch); the reverse was the bug. numpy's
    # name-mangled msvcp140-<hash>.dll is referenced by its mangled name and is
    # left alone.
    _MSVC_RUNTIME_DLLS = {
        'msvcp140.dll',
        'msvcp140_1.dll',
        'msvcp140_2.dll',
        'msvcp140_atomic_wait.dll',
        'msvcp140_codecvt_ids.dll',
        'vcruntime140.dll',
        'vcruntime140_1.dll',
        'concrt140.dll',
    }

    a.binaries = [
        entry for entry in a.binaries
        if os.path.basename(entry[0]).lower() not in _MSVC_RUNTIME_DLLS
    ]

    _system32 = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')
    for _dll in sorted(_MSVC_RUNTIME_DLLS):
        _src = os.path.join(_system32, _dll)
        if os.path.isfile(_src):
            a.binaries.append((_dll, _src, 'BINARY'))
    # -----------------------------------------------------------------------

pyz = PYZ(a.pure)

if IS_MACOS:
    # ---------------------------------------------------------------------
    # macOS: one-dir build wrapped in an .app bundle.
    #
    # Deliberately NOT onefile: a onefile bundle re-extracts the whole
    # payload (torch alone is well over a GB) to a temp dir on every launch,
    # and the extracted copy is unsigned, which Gatekeeper dislikes. A
    # one-dir .app starts instantly and can be signed/notarised as a unit.
    #
    # UPX is off here as well -- it corrupts Mach-O binaries and invalidates
    # any code signature.
    # ---------------------------------------------------------------------

    # build.py generates assets/app_icon.icns; fall back to the 1024px macOS
    # PNG (the Dark variant, matching the app's own dark theme), which
    # PyInstaller converts itself when Pillow is available.
    _icns = os.path.join(SPECPATH, 'assets', 'app_icon.icns')
    if not os.path.isfile(_icns):
        _icns = os.path.join(
            SPECPATH, 'assets', 'icon', 'icon-macOS-Dark-1024x1024@2x.png'
        )

    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='RSP',
        upx=False,
        console=False,
        target_arch=None,  # native arch; torch ships no universal2 wheel
        # Ad-hoc signing unless RSP_CODESIGN_IDENTITY names a real Developer
        # ID, which is what notarised distribution builds need.
        codesign_identity=os.environ.get('RSP_CODESIGN_IDENTITY') or None,
        entitlements_file=os.environ.get('RSP_ENTITLEMENTS_FILE') or None,
        icon=[_icns],
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        upx=False,
        name='RSP',
    )

    app = BUNDLE(
        coll,
        name='RSP.app',
        icon=_icns,
        bundle_identifier=settings.APP_BUNDLE_ID,
        version=settings.APP_VERSION_NUMERIC,
        info_plist={
            'CFBundleName': 'RSP',
            'CFBundleDisplayName': settings.APP_NAME,
            # macOS only accepts period-separated integers here, so the
            # "-dev" suffix APP_VERSION carries is dropped; the About dialog
            # still shows the full string.
            'CFBundleShortVersionString': settings.APP_VERSION_NUMERIC,
            'CFBundleVersion': settings.APP_VERSION_NUMERIC,
            'NSHighResolutionCapable': True,
            # The app draws its own dark theme; without this macOS forces
            # the light Aqua appearance on the native chrome.
            'NSRequiresAquaSystemAppearance': False,
            'LSApplicationCategoryType': 'public.app-category.photography',
            'LSMinimumSystemVersion': '11.0',
            'NSHumanReadableCopyright': settings.APP_COPYRIGHT,
        },
    )
else:
    # Windows (and Linux): single-file executable.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='RSP',
        upx=True,
        console=False,
        version=_windows_version_info() if IS_WINDOWS else None,
        icon=[os.path.join('assets', 'app_icon.png')],
    )
