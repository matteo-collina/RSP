"""Defensive Qt-binding import shim: Metashape may bundle PySide6 or PySide2."""

try:
    from PySide6 import QtWidgets, QtGui, QtCore
    QT_BINDING = "PySide6"
except ImportError:
    try:
        from PySide2 import QtWidgets, QtGui, QtCore
        QT_BINDING = "PySide2"
    except ImportError:
        QtWidgets = QtGui = QtCore = None
        QT_BINDING = None
