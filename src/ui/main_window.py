"""
Main application window.
"""

import os
import webbrowser
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QIcon

from config.settings import (APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT, APP_ICON, 
                           TEMP_FOLDER, DOCUMENTATION_URL)
from src.ui.widgets import LeftPanel, RightPanel
from src.ui.dialogs import AboutDialog, GoProDialog, show_message_box
from src.workers.processing_thread import ImageProcessingThread
from src.utils.ui_utils import format_time


class ImageProcessor(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Set application icon
        if os.path.isfile(APP_ICON):
            self.setWindowIcon(QIcon(APP_ICON))
        
        # Initialize variables
        self.paths = {"center": "", "left": "", "right": ""}
        self.temp_folder = TEMP_FOLDER
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        self.setup_ui()
        self.setup_menu()
    
    def closeEvent(self, event):
        """Handle application close event - clean up memory."""
        if hasattr(self, 'right_panel'):
            self.right_panel.clear_memory()
        event.accept()
    
    def setup_ui(self):
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Create panels
        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)
        
        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.right_panel)
    
    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        gopro_action = tools_menu.addAction("GoPro QR Code")
        gopro_action.triggered.connect(self.show_gopro_dialog)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        doc_action = help_menu.addAction("Documentation")
        doc_action.triggered.connect(self.show_documentation)
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about_dialog)
    
    def show_gopro_dialog(self):
        """Show GoPro QR code dialog."""
        dialog = GoProDialog(self)
        dialog.exec()
    
    def show_about_dialog(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def show_documentation(self):
        """Open documentation in web browser."""
        webbrowser.open(DOCUMENTATION_URL)
    
    def toggle_enhancement_section(self):
        """Toggle the visibility of the enhancement section."""
        if self.left_panel.enhancement_checkbox.isChecked():
            self.right_panel.show()
        else:
            self.right_panel.hide()
    
    def validate_directories(self):
        """Validate that at least one directory is selected and exists."""
        valid_paths = {}
        for prefix, path in self.paths.items():
            if path and os.path.exists(path) and os.path.isdir(path):
                valid_paths[prefix] = path
            elif path:  # Path is set but doesn't exist
                show_message_box(self, "Invalid Directory", 
                              f"The {prefix} directory does not exist:\n{path}", "warning")
                return None
        
        if not valid_paths:
            show_message_box(self, "No Directories Selected", 
                          "Please select at least one directory to process.", "warning")
            return None
        
        return valid_paths
    
    def process_images(self):
        """Start the image processing workflow."""
        try:
            # Validate directories
            valid_paths = self.validate_directories()
            if not valid_paths:
                return
            
            # Get prefix values
            prefixes = [input_field.text().strip() for input_field in self.left_panel.prefix_inputs]
            
            # Get number of threads
            num_threads = self.left_panel.thread_spinbox.value()
            
            # Get sorting method
            sort_methods = {
                0: "exif",     # "EXIF Date Taken (Recommended)"
                1: "filename", # "Filename (Alphabetical)"
                2: "mtime"     # "File Modification Time"
            }
            sort_method = sort_methods.get(self.left_panel.sorting_combo.currentIndex(), "exif")
            
            # Check if any processing will be done
            if (not self.left_panel.enhancement_checkbox.isChecked() and 
                not self.left_panel.rename_checkbox.isChecked()):
                show_message_box(self, "No Processing Selected", 
                              "Please select at least one processing option (Rename Images or Image Enhancement).",
                              "warning")
                return
            
            # Disable the process button
            self.left_panel.process_btn.setEnabled(False)
            
            # Reset progress bar
            self.left_panel.progress_bar.setValue(0)
            self.left_panel.status_label.setText("Starting...")
            
            # Start processing thread
            self.processing_thread = ImageProcessingThread(
                valid_paths, 
                prefixes,
                self.left_panel.enhancement_checkbox.isChecked(),
                self.left_panel.rename_checkbox.isChecked(),
                num_threads,
                sort_method
            )
            self.processing_thread.progress_updated.connect(self.update_progress)
            self.processing_thread.finished_processing.connect(self.processing_finished)
            self.processing_thread.start()
            
        except Exception as e:
            show_message_box(self, "Error", f"An error occurred: {e}", "critical")
            self.left_panel.process_btn.setEnabled(True)
    
    def update_progress(self, current, maximum, status_text):
        """Update the progress bar and status."""
        self.left_panel.progress_bar.setMaximum(maximum)
        self.left_panel.progress_bar.setValue(current)
        self.left_panel.status_label.setText(status_text)
    
    def processing_finished(self, success, message, processing_time):
        """Handle the completion of image processing."""
        self.left_panel.process_btn.setEnabled(True)
        self.left_panel.status_label.setText("Ready")
        
        # Format the time nicely
        time_str = format_time(processing_time)
        
        if success:
            complete_message = f"{message}\n\nProcessing time: {time_str}"
            show_message_box(self, "Success", complete_message, "information")
        else:
            complete_message = f"{message}\n\nTime elapsed: {time_str}"
            show_message_box(self, "Error", complete_message, "critical")
