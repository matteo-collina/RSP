"""RSP plugin loader. In Metashape: Tools > Run Script... > this file.

Bootstraps scripts/ onto sys.path and imports rsp_plugin, whose __init__.py
registers the "RSP" menu as an import side effect.

Every rsp_plugin* module is dropped from sys.modules first, so re-running
this script picks up code changes. Do not replace this with
importlib.reload(sys.modules["rsp_plugin"]): reload() only re-executes that
one module's top-level code and doesn't recurse into submodules it imports,
so menu.py and everything it imports would stay stale.
"""

import os
import sys

PLUGIN_ROOT = os.path.dirname(os.path.abspath(__file__))
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

for _name in [n for n in sys.modules if n == "rsp_plugin" or n.startswith("rsp_plugin.")]:
    del sys.modules[_name]

import rsp_plugin  # noqa: F401
