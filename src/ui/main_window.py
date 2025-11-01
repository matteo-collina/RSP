"""
Main application window.
"""

import os
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox, QFileDialog
from PyQt6.QtGui import QIcon

from config.settings import (APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT, APP_ICON, 
                           DOCUMENTATION_URL)
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
        # Initialize variables
        self.paths = {"center": "", "left": "", "right": ""}
        self.last_processing_params = None  # Store last processing parameters for report
        
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
            
            # Store processing parameters for report generation
            self.last_processing_params = {
                'paths': valid_paths.copy(),
                'prefixes': prefixes.copy(),
                'num_threads': num_threads,
                'sort_method': sort_method,
                'enhancement_enabled': self.left_panel.enhancement_checkbox.isChecked(),
                'rename_enabled': self.left_panel.rename_checkbox.isChecked()
            }
            
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
    
    def processing_finished(self, success, message, processing_time, total_files):
        """Handle the completion of image processing."""
        self.left_panel.process_btn.setEnabled(True)
        self.left_panel.status_label.setText("Ready")
        
        # Format the time nicely
        time_str = format_time(processing_time)
        
        if success:
            complete_message = f"{message}\n\nProcessing time: {time_str}"
            show_message_box(self, "Success", complete_message, "information")
            
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
        
        # Add rename option
        cmd_parts.append(f"--rename {'true' if params['rename_enabled'] else 'false'}")
        
        # Add enhance option
        cmd_parts.append(f"--enhance {'true' if params['enhancement_enabled'] else 'false'}")
        
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
