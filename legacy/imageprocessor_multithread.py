import os
import sys
import random
import shutil
import cv2
import numpy as np
import webbrowser
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                            QFileDialog, QMessageBox, QCheckBox, QProgressBar,
                            QFrame, QTextEdit, QMenuBar, QMenu, QSpinBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QFont, QAction
from sceneRadianceCLAHE import RecoverCLAHE


class ImageProcessingThread(QThread):
    progress_updated = pyqtSignal(int, int, str)  # current, maximum, percentage_text
    finished_processing = pyqtSignal(bool, str, float)  # success, message, processing_time
    
    def __init__(self, paths, prefixes, enhancement_enabled, rename_enabled, num_threads=4):
        super().__init__()
        self.paths = paths
        self.prefixes = prefixes
        self.enhancement_enabled = enhancement_enabled
        self.rename_enabled = rename_enabled
        self.num_threads = num_threads
        self.progress_lock = Lock()  # Thread-safe progress updates
        self.start_time = None
        
    def run(self):
        # Record start time
        self.start_time = time.time()
        
        try:
            total_files = sum(
                len([f for f in os.listdir(path) 
                    if not f.startswith('.') and os.path.isfile(os.path.join(path, f))
                    and self.is_valid_image_file(f)])
                for path in self.paths.values() if path
            )
            
            if self.enhancement_enabled:
                max_progress = total_files * 2  # rename + enhancement
            else:
                max_progress = total_files  # just rename
                
            current_progress = 0
            processed_images = []  # Changed from renamed_images to processed_images
            
            # Process files phase (rename and collect valid paths)
            for prefix, path in self.paths.items():
                if path:
                    current_progress = self.process_files_in_directory(
                        path, prefix, current_progress, processed_images, max_progress
                    )
            
            # Enhancement phase (if enabled) - NOW MULTI-THREADED
            if self.enhancement_enabled:
                # Filter out any invalid paths before enhancement
                valid_images = []
                for img_path in processed_images:
                    if os.path.exists(img_path) and os.path.isfile(img_path):
                        valid_images.append(img_path)
                    else:
                        print(f"Warning: File not found or invalid: {img_path}")
                
                if valid_images:
                    self.apply_image_enhancement_multithreaded(valid_images, current_progress, max_progress)
                else:
                    print("Warning: No valid images found for enhancement")
            else:
                # Ensure we reach 100% for rename-only operations
                self.progress_updated.emit(max_progress, max_progress, "100%")
            
            # Calculate processing time
            processing_time = time.time() - self.start_time
            self.finished_processing.emit(True, "Processing completed successfully!", processing_time)
            
        except Exception as e:
            processing_time = time.time() - self.start_time if self.start_time else 0
            self.finished_processing.emit(False, f"An error occurred: {e}", processing_time)
    
    def process_files_in_directory(self, directory, prefix, current_progress, processed_images, max_progress):
        """Process (and optionally rename) files in directory"""
        try:
            # Get all files with their timestamps
            files = []
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path) and not filename.startswith('.'):
                    # Check if it's a valid image file
                    if self.is_valid_image_file(filename):
                        files.append((filename, os.path.getmtime(file_path)))
            
            if self.rename_enabled:
                files.sort(key=lambda x: x[1])  # Sort by modification time
            
            counter = 0
            for filename, _ in files:
                old_file_path = os.path.join(directory, filename)
                
                if self.rename_enabled:
                    new_file_path = self.generate_new_filename(directory, filename, prefix, counter)
                    
                    # Perform rename operation safely
                    if old_file_path != new_file_path:
                        try:
                            # Ensure target doesn't exist
                            if os.path.exists(new_file_path):
                                counter += 1
                                new_file_path = self.generate_new_filename(directory, filename, prefix, counter)
                            
                            os.rename(old_file_path, new_file_path)
                            processed_images.append(new_file_path)
                        except OSError as e:
                            print(f"Warning: Could not rename {old_file_path}: {e}")
                            # If rename fails, use original path
                            processed_images.append(old_file_path)
                    else:
                        processed_images.append(old_file_path)
                else:
                    processed_images.append(old_file_path)
                
                counter += 1
                current_progress += 1
                progress_percent = int((current_progress / max_progress) * 100)
                self.progress_updated.emit(current_progress, max_progress, f"{progress_percent}%")
        
        except Exception as e:
            print(f"Error processing directory {directory}: {e}")
        
        return current_progress
    
    def is_valid_image_file(self, filename):
        """Check if file is a valid image file"""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        return os.path.splitext(filename.lower())[1] in valid_extensions
    
    def generate_new_filename(self, directory, original_filename, prefix, counter):
        """Generate new filename based on prefixes"""
        prefix1, prefix2, prefix3 = self.prefixes
        file_extension = os.path.splitext(original_filename)[1]
        
        # Build filename with available prefixes
        name_parts = []
        if prefix1:
            name_parts.append(prefix1)
        if prefix2:
            name_parts.append(prefix2)
        if prefix3:
            name_parts.append(prefix3)
        
        name_parts.append(prefix)  # Directory prefix (left/right/center)
        name_parts.append(str(counter).zfill(5))
        
        new_name = "_".join(name_parts) + file_extension
        return os.path.join(directory, new_name)
    
    def process_single_image(self, image_path):
        """Process a single image - this will run in parallel"""
        try:
            # Double-check file exists and is readable
            if not os.path.exists(image_path):
                return False, f"File not found: {image_path}"
            
            if not os.path.isfile(image_path):
                return False, f"Path is not a file: {image_path}"
            
            # Try to read the image
            img = cv2.imread(image_path)
            if img is None:
                return False, f"Could not read image (corrupted or unsupported format): {image_path}"
            
            # Get EXIF data
            exif_data = None
            try:
                pil_image = Image.open(image_path)
                exif_data = pil_image.info.get('exif')
                pil_image.close()  # Explicitly close to free resources
            except Exception as e:
                print(f"Warning: Could not read EXIF data from {image_path}: {e}")
            
            # Create enhanced folder if it doesn't exist
            enhanced_folder = os.path.join(os.path.dirname(image_path), "Enhanced")
            os.makedirs(enhanced_folder, exist_ok=True)
            
            # Apply enhancement
            enhanced_img_clahe = RecoverCLAHE(img)
            temp_name_clahe = os.path.splitext(os.path.basename(image_path))[0] + '.jpg'
            temp_path_clahe = os.path.join(enhanced_folder, temp_name_clahe)
            
            # Save enhanced image
            success = cv2.imwrite(temp_path_clahe, enhanced_img_clahe)
            if not success:
                return False, f"Failed to save enhanced image: {temp_path_clahe}"
            
            # Preserve EXIF data if available
            if exif_data:
                try:
                    enhanced_pil_image = Image.open(temp_path_clahe)
                    enhanced_pil_image.save(temp_path_clahe, exif=exif_data)
                    enhanced_pil_image.close()
                except Exception as e:
                    print(f"Warning: Could not preserve EXIF data for {temp_path_clahe}: {e}")
            
            return True, f"Successfully processed: {os.path.basename(image_path)}"
            
        except Exception as e:
            return False, f"Error processing {image_path}: {str(e)}"
    
    def apply_image_enhancement_multithreaded(self, image_paths, start_progress, max_progress):
        """Apply image enhancement using multiple threads"""
        current_progress = start_progress
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(self.process_single_image, image_path): image_path 
                for image_path in image_paths
            }
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_image):
                image_path = future_to_image[future]
                
                try:
                    success, message = future.result()
                    if not success:
                        print(f"Warning: {message}")  # Log warnings but continue
                except Exception as e:
                    print(f"Exception processing {image_path}: {e}")
                
                # Thread-safe progress update
                with self.progress_lock:
                    current_progress += 1
                    progress_percent = int((current_progress / max_progress) * 100)
                    self.progress_updated.emit(current_progress, max_progress, f"{progress_percent}%")


class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Processor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(__file__), "app_icon.png")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize variables
        self.paths = {"center": "", "left": "", "right": ""}
        self.temp_folder = "TempImages"
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        self.setup_ui()
        self.setup_menu()
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        gopro_action = QAction("GoPro QR Code", self)
        gopro_action.triggered.connect(self.show_gopro_qr)
        tools_menu.addAction(gopro_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        doc_action = QAction("Documentation", self)
        doc_action.triggered.connect(self.show_documentation)
        help_menu.addAction(doc_action)
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_info)
        help_menu.addAction(about_action)
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel
        left_panel = QWidget()
        left_panel.setFixedWidth(400)
        left_layout = QVBoxLayout(left_panel)
        
        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "university_logo.png")
        if os.path.isfile(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(300, 100, Qt.AspectRatioMode.KeepAspectRatio))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            left_layout.addWidget(logo_label)
        
        # Prefix inputs
        self.prefix_inputs = []
        for i in range(1, 4):
            prefix_layout = QHBoxLayout()
            prefix_label = QLabel(f"Prefix {i}:")
            prefix_input = QLineEdit()
            prefix_layout.addWidget(prefix_label)
            prefix_layout.addWidget(prefix_input)
            left_layout.addLayout(prefix_layout)
            self.prefix_inputs.append(prefix_input)
        
        # Thread count selection
        thread_layout = QHBoxLayout()
        thread_label = QLabel("Processing Threads:")
        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setMinimum(1)
        self.thread_spinbox.setMaximum(32)
        
        # Set optimal default based on CPU count
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        optimal_threads = max(4, min(cpu_count - 2, 12))  # Leave 2 cores free, max 12
        self.thread_spinbox.setValue(optimal_threads)
        
        self.thread_spinbox.setToolTip(f"Number of threads for image enhancement\nDetected {cpu_count} CPU cores\nRecommended: {optimal_threads} threads")
        thread_layout.addWidget(thread_label)
        thread_layout.addWidget(self.thread_spinbox)
        left_layout.addLayout(thread_layout)
        
        # Directory selection
        self.path_labels = {}
        self.browse_buttons = {}
        self.clear_buttons = {}
        
        for prefix in self.paths:
            # Directory label
            dir_label = QLabel(f"Select {prefix} directory:")
            left_layout.addWidget(dir_label)
            
            # Path display
            path_label = QLabel("No directory selected")
            path_label.setStyleSheet("border: 1px solid gray; padding: 5px;")
            left_layout.addWidget(path_label)
            self.path_labels[prefix] = path_label
            
            # Buttons
            button_layout = QHBoxLayout()
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda checked, p=prefix: self.browse_directory(p))
            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked, p=prefix: self.clear_directory(p))
            
            button_layout.addWidget(browse_btn)
            button_layout.addWidget(clear_btn)
            left_layout.addLayout(button_layout)
            
            self.browse_buttons[prefix] = browse_btn
            self.clear_buttons[prefix] = clear_btn
        
        # Clear all button
        clear_all_btn = QPushButton("Clear All Directories")
        clear_all_btn.clicked.connect(self.clear_all_directories)
        left_layout.addWidget(clear_all_btn)
        
        # Checkboxes
        self.enhancement_checkbox = QCheckBox("Image Enhancement")
        self.enhancement_checkbox.toggled.connect(self.toggle_enhancement_section)
        left_layout.addWidget(self.enhancement_checkbox)
        
        self.rename_checkbox = QCheckBox("Rename Images")
        self.rename_checkbox.setChecked(True)
        left_layout.addWidget(self.rename_checkbox)
        
        # Process button
        self.process_btn = QPushButton("Process Images")
        self.process_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.process_btn.setMinimumHeight(50)
        self.process_btn.clicked.connect(self.process_images)
        left_layout.addWidget(self.process_btn)
        
        # Progress bar
        self.progress_label = QLabel("0%")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        left_layout.addWidget(self.progress_bar)
        
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        
        # Right panel (enhancement section)
        self.enhancement_frame = QWidget()
        self.enhancement_frame.setMinimumWidth(600)
        enhancement_layout = QVBoxLayout(self.enhancement_frame)
        
        # Image preview
        self.image_preview = QLabel()
        self.image_preview.setMinimumSize(600, 400)
        self.image_preview.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setText("Image preview will appear here")
        enhancement_layout.addWidget(self.image_preview)
        
        # Test button
        test_btn = QPushButton("Test Image Enhancement")
        test_btn.clicked.connect(self.test_image_enhancement)
        enhancement_layout.addWidget(test_btn)
        
        self.enhancement_frame.hide()
        main_layout.addWidget(self.enhancement_frame)
    
    def format_time(self, seconds):
        """Format time in seconds to a human-readable string"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = seconds % 60
            return f"{hours}h {minutes}m {remaining_seconds:.1f}s"
        
    def browse_directory(self, prefix):
        directory = QFileDialog.getExistingDirectory(self, f"Select {prefix} directory")
        if directory:
            self.paths[prefix] = directory
            self.path_labels[prefix].setText(directory)
    
    def clear_directory(self, prefix):
        self.paths[prefix] = ""
        self.path_labels[prefix].setText("No directory selected")
    
    def clear_all_directories(self):
        for prefix in self.paths:
            self.clear_directory(prefix)
    
    def toggle_enhancement_section(self):
        if self.enhancement_checkbox.isChecked():
            self.enhancement_frame.show()
        else:
            self.enhancement_frame.hide()
    
    def validate_directories(self):
        """Validate that at least one directory is selected and exists"""
        valid_paths = {}
        for prefix, path in self.paths.items():
            if path and os.path.exists(path) and os.path.isdir(path):
                valid_paths[prefix] = path
            elif path:  # Path is set but doesn't exist
                QMessageBox.warning(self, "Invalid Directory", 
                                  f"The {prefix} directory does not exist:\n{path}")
                return None
        
        if not valid_paths:
            QMessageBox.warning(self, "No Directories Selected", 
                              "Please select at least one directory to process.")
            return None
        
        return valid_paths
    
    def process_images(self):
        try:
            # Validate directories
            valid_paths = self.validate_directories()
            if not valid_paths:
                return
            
            # Get prefix values
            prefixes = [input_field.text().strip() for input_field in self.prefix_inputs]
            
            # Get number of threads
            num_threads = self.thread_spinbox.value()
            
            # Check if any processing will be done
            if not self.enhancement_checkbox.isChecked() and not self.rename_checkbox.isChecked():
                QMessageBox.warning(self, "No Processing Selected", 
                                  "Please select at least one processing option (Rename Images or Image Enhancement).")
                return
            
            # Disable the process button
            self.process_btn.setEnabled(False)
            
            # Reset progress bar
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            
            # Start processing thread
            self.processing_thread = ImageProcessingThread(
                valid_paths, 
                prefixes,
                self.enhancement_checkbox.isChecked(),
                self.rename_checkbox.isChecked(),
                num_threads
            )
            self.processing_thread.progress_updated.connect(self.update_progress)
            self.processing_thread.finished_processing.connect(self.processing_finished)
            self.processing_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            self.process_btn.setEnabled(True)
    
    def update_progress(self, current, maximum, text):
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(current)
        self.progress_label.setText(text)
    
    def processing_finished(self, success, message, processing_time):
        self.process_btn.setEnabled(True)
        
        # Format the time nicely
        time_str = self.format_time(processing_time)
        
        if success:
            complete_message = f"{message}\n\nProcessing time: {time_str}"
            QMessageBox.information(self, "Success", complete_message)
        else:
            complete_message = f"{message}\n\nTime elapsed: {time_str}"
            QMessageBox.critical(self, "Error", complete_message)
    
    def test_image_enhancement(self):
        left_folder = self.paths.get("left")
        if not left_folder:
            QMessageBox.warning(self, "Warning", 
                              "Left folder is not selected.\nPlease select a left folder in the main panel.")
            return
        
        # Ensure temp folder exists
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        # Clear temp folder
        for filename in os.listdir(self.temp_folder):
            file_path = os.path.join(self.temp_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Select random image
        files = [f for f in os.listdir(left_folder) 
                if os.path.isfile(os.path.join(left_folder, f)) and 
                self.is_valid_image_file(f)]
        
        if not files:
            QMessageBox.warning(self, "Warning", "No valid images found in the left folder.")
            return
        
        random_file = random.choice(files)
        random_image_path = os.path.join(left_folder, random_file)
        temp_image_path = os.path.join(self.temp_folder, random_file)
        
        # Copy image to temp folder
        shutil.copy(random_image_path, temp_image_path)
        
        # Apply enhancement if checked
        img = cv2.imread(temp_image_path)
        if img is not None:
            if self.enhancement_checkbox.isChecked():
                enhanced_img_clahe = RecoverCLAHE(img)
                temp_name_clahe = os.path.splitext(random_file)[0] + '_CLAHE.jpg'
                temp_path_clahe = os.path.join(self.temp_folder, temp_name_clahe)
                cv2.imwrite(temp_path_clahe, enhanced_img_clahe)
                self.display_image(temp_path_clahe)
            else:
                self.display_image(temp_image_path)
        
        # Schedule cleanup
        QTimer.singleShot(5000, self.delete_temp_folder)
    
    def is_valid_image_file(self, filename):
        """Check if file is a valid image file"""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        return os.path.splitext(filename.lower())[1] in valid_extensions
    
    def delete_temp_folder(self):
        try:
            for filename in os.listdir(self.temp_folder):
                file_path = os.path.join(self.temp_folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            if not os.listdir(self.temp_folder):
                os.rmdir(self.temp_folder)
        except Exception as e:
            print(f"Warning: Could not clean up temp folder: {e}")
    
    def display_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                self.image_preview.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_preview.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Warning: Could not display image {image_path}: {e}")
    
    def show_gopro_qr(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        
        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("GoPro QR Code")
        dialog.setWindowIcon(self.windowIcon())
        dialog.setModal(True)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Load and display QR code image
        image_path = os.path.join(os.path.dirname(__file__), "gopro_qr_code.png")
        if os.path.isfile(image_path):
            image_label = QLabel()
            pixmap = QPixmap(image_path)
            # Now you can make it as large as you want!
            scaled_pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(image_label)
        
        # Add text
        text_label = QLabel("SETTINGS\n\n"
                        "White-Balance: Auto\n\n\n"
                        "YOU NEED THE LABS FIRMWARE IN ORDER TO USE IT. PLEASE, REFER TO DOCUMENTATION.\n\n"
                        "PLEASE, REMEMBER TO TURN ON INTERVALOMETER FUNCTION ON THE GOPRO.")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # Add OK button
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Set dialog size and show
        dialog.resize(500, 600)  # Adjust size as needed
        dialog.exec()
    
    def show_about_info(self):
        about_text = """XXX
A Victoria University of Wellington project
Developed by Seammetry

CREDITS:
Software Development: Matteo Collina
Testing: Manon Payne Broadribb, Miriam Pierotti
Supervision: Prof. James Bell

Version: 1.0
Date: September 2024
Contact: matteo.collina@vuw.ac.nz"""
        
        QMessageBox.about(self, "About", about_text)
    
    def show_documentation(self):
        webbrowser.open("https://www.google.com")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = ImageProcessor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()