"""
Main application window.
"""

import os
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QMessageBox,
                            QFileDialog, QSplitter, QStackedWidget)
from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QIcon

from config.settings import (APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT, APP_ICON,
                           LEFT_PANEL_WIDTH, DOCUMENTATION_URL)
from src.ui.widgets import LeftPanel
from src.ui.gallery import GalleryPanel
from src.ui.compare_viewer import ImageViewerOverlay
from src.ui.enhancement_panel import AdaptiveGradingPanel
from src.ui.dialogs import AboutDialog, GoProDialog, show_message_box
from src.workers.processing_thread import ImageProcessingThread
from src.utils.ui_utils import format_time
from src.core.dataset import DatasetState, PathsView
from src.core.image_enhancement import METHOD_DISPLAY_NAMES
from src.core.gray_world import get_device_display_name


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
        self.dataset = DatasetState()
        self.paths = PathsView(self.dataset)  # backward-compatible dict-like view
        self.last_processing_params = None  # Store last processing parameters for report
        
        self.setup_ui()
        self.setup_menu()
    
    def closeEvent(self, event):
        """Handle application close event.

        Marks the gallery/viewer as no longer listening first (so a result
        that arrives after a timed-out wait below is a safe no-op, not a
        crash), then drops queued-but-not-started background jobs and
        waits briefly for any already-running one to actually finish.
        """
        self.gallery_panel.shutdown()
        self.image_viewer.shutdown()  # also flags itself, then drains its own pool

        pool = QThreadPool.globalInstance()
        pool.clear()
        pool.waitForDone(2000)
        event.accept()

    def setup_ui(self):
        """Setup the main UI layout: a resizable splitter with the controls
        panel on the left and a stack (gallery <-> full-screen viewer) on
        the right."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.left_panel = LeftPanel(self)
        self.gallery_panel = GalleryPanel()
        self.gallery_panel.image_clicked.connect(self.open_image_viewer)

        self.image_viewer = ImageViewerOverlay(method_provider=self.left_panel.get_enhancement_selection)
        self.image_viewer.closed.connect(self.close_image_viewer)

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.gallery_panel)  # index 0
        self.content_stack.addWidget(self.image_viewer)   # index 1

        # Adaptive Grading's parameter sliders live in their own panel to
        # the right of the gallery/viewer, not in the (already crowded)
        # left controls column. LeftPanel only needs a reference to read
        # current values from -- it doesn't own or place this widget.
        self.adaptive_grading_panel = AdaptiveGradingPanel()
        self.left_panel.params_panel = self.adaptive_grading_panel.params_panel
        self.adaptive_grading_panel.setVisible(False)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.content_stack)
        self.splitter.addWidget(self.adaptive_grading_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        # Collapsible panes let QSplitter silently shrink the (supposedly
        # fixed-width) left panel below its real width during its internal
        # layout passes, handing the freed space to content_stack instead --
        # which showed up as the viewer's image area growing partway
        # through the session for no visible reason.
        self.splitter.setChildrenCollapsible(False)
        # Without an explicit initial split, QSplitter falls back to a
        # sizeHint-based heuristic on first layout and only gives the
        # gallery/viewer side its real share of the window on a later
        # layout pass -- which made the viewer visibly change size right
        # after opening (still on the stale size) once correction ran.
        self.splitter.setSizes([LEFT_PANEL_WIDTH, WINDOW_WIDTH - LEFT_PANEL_WIDTH, 0])

        main_layout.addWidget(self.splitter)

        self.left_panel.enhancement_selection_changed.connect(self._on_enhancement_selection_changed)
        self._device_status_shown = False

    def _on_enhancement_selection_changed(self):
        """Keep the Adaptive Grading params panel and the compute-device
        status label in sync with the left panel's checkbox/method combo."""
        method_key, _ = self.left_panel.get_enhancement_selection()
        show_params = self.left_panel.enhancement_checkbox.isChecked() and method_key == "gray_world"
        self.adaptive_grading_panel.setVisible(show_params)

        if show_params and not self._device_status_shown:
            # Lazy by design: querying the device is only ever done once
            # Adaptive Grading is actually selected, not at app startup.
            # In practice torch is already loaded by this point (run_gui()
            # loads it before PyQt6, to sidestep a Windows DLL conflict --
            # see gray_world.warmup()), so this is instant, not a real
            # "detecting..." delay.
            self.adaptive_grading_panel.device_status_label.setText(f"Device: {get_device_display_name()}")
            self._device_status_shown = True

    def open_image_viewer(self, image_path):
        """Show the full-screen compare viewer for a clicked thumbnail."""
        self.image_viewer.open_image(image_path)
        self.content_stack.setCurrentWidget(self.image_viewer)
        self.image_viewer.setFocus()  # so Esc reaches the viewer, not the gallery

    def close_image_viewer(self):
        """Return from the full-screen viewer back to the gallery."""
        self.content_stack.setCurrentWidget(self.gallery_panel)
    
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
            
            enhancement_method, enhancement_params = self.left_panel.get_enhancement_selection()

            # Store processing parameters for report generation
            self.last_processing_params = {
                'paths': valid_paths.copy(),
                'prefixes': prefixes.copy(),
                'num_threads': num_threads,
                'sort_method': sort_method,
                'enhancement_enabled': self.left_panel.enhancement_checkbox.isChecked(),
                'rename_enabled': self.left_panel.rename_checkbox.isChecked(),
                'enhancement_method': enhancement_method,
                'enhancement_params': enhancement_params,
            }

            # Start processing thread
            self.processing_thread = ImageProcessingThread(
                valid_paths,
                prefixes,
                self.left_panel.enhancement_checkbox.isChecked(),
                self.left_panel.rename_checkbox.isChecked(),
                num_threads,
                sort_method,
                enhancement_method=enhancement_method,
                enhancement_params=enhancement_params,
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
    
    def processing_finished(self, success, message, processing_time, total_files):
        """Handle the completion of image processing."""
        self.left_panel.process_btn.setEnabled(True)
        self.left_panel.status_label.setText("Ready")
        
        # Format the time nicely
        time_str = format_time(processing_time)
        
        if success:
            complete_message = f"{message}\n\nProcessing time: {time_str}"
            show_message_box(self, "Success", complete_message, "information")

            # Renaming (and/or enhancement writing into an Enhanced/
            # subfolder) can leave the gallery's thumbnails pointing at
            # filenames that no longer exist -- reload the folders touched
            # by this run so it reflects what's actually on disk now.
            if self.last_processing_params:
                for prefix, path in self.last_processing_params['paths'].items():
                    self.gallery_panel.set_directory(prefix, path)

            # Prompt user to save report
            self.prompt_save_report(processing_time, total_files)
        else:
            complete_message = f"{message}\n\nTime elapsed: {time_str}"
            show_message_box(self, "Error", complete_message, "critical")
    
    def build_cli_command(self):
        """Build the equivalent CLI command from GUI parameters."""
        if not self.last_processing_params:
            return None
        
        params = self.last_processing_params
        cmd_parts = ["python rsp.py"]
        
        # Add directory paths
        for prefix, path in params['paths'].items():
            if path:
                cmd_parts.append(f"--{prefix} \"{path}\"")
        
        # Add prefixes
        for i, prefix_value in enumerate(params['prefixes'], 1):
            if prefix_value:
                cmd_parts.append(f"--prefix{i} \"{prefix_value}\"")
        
        # Add thread count
        cmd_parts.append(f"--thread {params['num_threads']}")
        
        # Add rename option, plus the sort order it depends on
        cmd_parts.append(f"--rename {'true' if params['rename_enabled'] else 'false'}")
        if params['rename_enabled']:
            cmd_parts.append(f"--sort {params['sort_method']}")
        
        # Add enhance option
        cmd_parts.append(f"--enhance {'true' if params['enhancement_enabled'] else 'false'}")

        # Add method + parameter overrides
        if params['enhancement_enabled']:
            cmd_parts.append(f"--method {params['enhancement_method']}")
            for key, value in params.get('enhancement_params', {}).items():
                cmd_parts.append(f"--param {key}={value}")

        return " ".join(cmd_parts)
    
    def prompt_save_report(self, processing_time, total_files):
        """Prompt user to save processing report."""
        # Ask user if they want to save the report
        reply = QMessageBox.question(
            self,
            "Save Processing Report",
            "Would you like to save a report of this processing session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.save_report(processing_time, total_files)
    
    def save_report(self, processing_time, total_files):
        """Save the processing report to a markdown file."""
        if not self.last_processing_params:
            return
        
        # Generate default filename from prefixes
        prefixes = self.last_processing_params['prefixes']
        prefix_parts = [p for p in prefixes if p.strip()]
        if prefix_parts:
            default_filename = "_".join(prefix_parts) + "_report.md"
        else:
            default_filename = "rsp_report.md"
        
        # Prompt user for save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Processing Report",
            default_filename,
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        # Generate CLI command
        cli_command = self.build_cli_command()
        
        # Generate report content
        report_content = self.generate_report_content(cli_command, processing_time, total_files)
        
        # Save to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            show_message_box(self, "Report Saved", f"Processing report saved to:\n{file_path}", "information")
        except Exception as e:
            show_message_box(self, "Error", f"Failed to save report:\n{e}", "critical")
    
    def generate_report_content(self, cli_command, processing_time, total_files):
        """Generate the markdown content for the report."""
        params = self.last_processing_params
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_str = format_time(processing_time)
        
        # Build report
        report = f"""# RSP Processing Report

## Processing Summary

**Date:** {timestamp}  
**Total Files Processed:** {total_files}  
**Processing Time:** {time_str}

## Processing Configuration

"""
        
        # Directories
        report += "### Directories\n\n"
        for prefix, path in params['paths'].items():
            if path:
                report += f"- **{prefix.capitalize()}:** `{path}`\n"
        
        # Prefixes
        report += "\n### File Naming Prefixes\n\n"
        prefix_values = [p for p in params['prefixes'] if p.strip()]
        if prefix_values:
            for i, prefix in enumerate(prefix_values, 1):
                report += f"- **Prefix {i}:** `{prefix}`\n"
        else:
            report += "*No prefixes specified*\n"
        
        # Processing options
        report += "\n### Processing Options\n\n"
        report += f"- **Rename Images:** {'Yes' if params['rename_enabled'] else 'No'}\n"
        report += f"- **Image Enhancement:** {'Yes' if params['enhancement_enabled'] else 'No'}\n"
        if params['enhancement_enabled']:
            method_name = METHOD_DISPLAY_NAMES.get(params['enhancement_method'], params['enhancement_method'])
            report += f"- **Enhancement Method:** {method_name}\n"
            if params.get('enhancement_params'):
                param_str = ", ".join(f"{k}={v}" for k, v in params['enhancement_params'].items())
                report += f"- **Enhancement Parameters:** {param_str}\n"
        report += f"- **Processing Threads:** {params['num_threads']}\n"
        
        # Sort method description
        sort_descriptions = {
            'exif': 'EXIF Date Taken',
            'filename': 'Filename (Alphabetical)',
            'mtime': 'File Modification Time'
        }
        sort_desc = sort_descriptions.get(params['sort_method'], params['sort_method'])
        report += f"- **Sort Method:** {sort_desc}\n"
        
        # CLI command
        report += f"\n## Equivalent CLI Command\n\n"
        report += "To reproduce this processing session from the command line:\n\n"
        report += f"```bash\n{cli_command}\n```\n"
        
        # Footer
        report += f"\n---\n*Report generated by RSP Image Processor*\n"
        
        return report
