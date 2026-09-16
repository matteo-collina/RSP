"""RSP Metashape plugin package. Importing it registers the RSP menu (see
menu.py) as a side effect. Registration failures are caught and surfaced
via messageBox instead of a raw traceback in Metashape's script console.
"""

try:
    from . import menu

    menu.register()
except Exception as e:
    import Metashape

    Metashape.app.messageBox(f"RSP plugin failed to load: {e}")
