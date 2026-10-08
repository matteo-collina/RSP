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
    # Fix: repoint every unmangled MSVC runtime copy the analysis collected,
    # wherever it was found (torch\lib, PyQt6\Qt6\bin, ...), at the build
    # machine's newer System32 copy instead -- keeping its original
    # destination, not collapsing everything to one location. A newer
    # runtime satisfies every older consumer (Qt, cv2, numpy, torch); the
    # reverse was the bug. numpy's name-mangled msvcp140-<hash>.dll is
    # referenced by its mangled name and is left alone.
    #
    # Earlier versions of this fix deleted every matching entry and re-added
    # a single copy at the collection root (dist/RSP/_internal/). That broke
    # torch: shm.dll's own dependency search only covers its own torch\lib
    # directory (torch adds that one via os.add_dll_directory at import
    # time), not the collection root, so torch\lib's copy being gone made
    # shm.dll fail to load with "WinError 126: The specified module could
    # not be found." one-dir and onefile differ here because onefile's
    # single flat extraction dir happened to double as that search root;
    # one-dir's dist/RSP/_internal doesn't. Patching sources in place avoids
    # depending on any particular directory being on the search path.
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

    _system32 = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')

    def _system32_copy(name):
        path = os.path.join(_system32, name)
        return path if os.path.isfile(path) else None

    _patched_binaries = []
    _dests_present = set()
    for _dest, _src, _typecode in a.binaries:
        _base = os.path.basename(_dest).lower()
        if _base in _MSVC_RUNTIME_DLLS:
            _newer = _system32_copy(_base)
            if _newer:
                _src = _newer
        _patched_binaries.append((_dest, _src, _typecode))
        _dests_present.add(_dest.lower())
    a.binaries = _patched_binaries

    # Also guarantee a root-level copy, for any consumer that relies on the
    # default search path (application directory) rather than adding its own.
    for _dll in sorted(_MSVC_RUNTIME_DLLS):
        if _dll in _dests_present:
            continue
        _src = _system32_copy(_dll)
        if _src:
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
    # Windows (and Linux): one-dir build, same reasoning as macOS above.
    #
    # This used to be a onefile .exe, but onefile re-extracts its entire
    # payload to a fresh %TEMP% dir on every launch, and the CUDA build of
    # torch makes that payload ~4GB (cublasLt64_12.dll, cudnn*.dll,
    # torch_cuda.dll, ... -- individually hundreds of MB each). Worse, since
    # every launch uses a new temp directory, Windows Defender treats all of
    # those files as never-seen-before and re-scans the lot each time instead
    # of hitting its scan cache. Together that made the CUDA build extremely
    # slow to open. UPX is off for the same reason: it buys little on
    # already-dense CUDA binaries but still costs decompression time on every
    # launch and makes heavily-packed DLLs more likely to draw extra AV
    # scrutiny. A one-dir folder pays the extraction cost once (at install
    # time) and Defender's cache covers unchanged files on later launches.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='RSP',
        upx=False,
        console=False,
        version=_windows_version_info() if IS_WINDOWS else None,
        icon=[os.path.join('assets', 'app_icon.png')],
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        upx=False,
        name='RSP',
    )
