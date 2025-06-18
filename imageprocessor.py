import os
import sys
import random
import shutil
import cv2
import numpy as np
import webbrowser
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                            QFileDialog, QMessageBox, QCheckBox, QProgressBar,
                            QFrame, QTextEdit, QMenuBar, QMenu)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QFont, QAction
from sceneRadianceCLAHE import RecoverCLAHE


class ImageProcessingThread(QThread):
    progress_updated = pyqtSignal(int, str)
    finished_processing = pyqtSignal(bool, str)
    
    def __init__(self, paths, prefixes, enhancement_enabled, rename_enabled):
        super().__init__()
        self.paths = paths
        self.prefixes = prefixes
        self.enhancement_enabled = enhancement_enabled
        self.rename_enabled = rename_enabled
        
    def run(self):
        try:
            total_files = sum(
                len([f for f in os.listdir(path) 
                    if not f.startswith('.') and os.path.isfile(os.path.join(path, f))])
                for path in self.paths.values() if path
            )
            
            if self.enhancement_enabled:
                max_progress = total_files * 2
            else:
                max_progress = total_files
                
            current_file = 0
            renamed_images = []
            
            for prefix, path in self.paths.items():
                if path:
                    current_file = self.rename_files_in_directory(
                        path, prefix, current_file, renamed_images, max_progress
                    )
            
            if self.enhancement_enabled:
                self.apply_image_enhancement(renamed_images, current_file, max_progress)
                
            self.finished_processing.emit(True, "Processing completed successfully!")
            
        except Exception as e:
            self.finished_processing.emit(False, f"An error occurred: {e}")
    
    def rename_files_in_directory(self, directory, prefix, current_file, renamed_images, max_progress):
        files = [(filename, os.path.getmtime(os.path.join(directory, filename))) 
                for filename in os.listdir(directory)]
        
        if self.rename_enabled:
            files.sort(key=lambda x: x[1])
        
        counter = 0
        for filename, _ in files:
            file_path = os.path.join(directory, filename)
            
            if self.rename_enabled:
                prefix1, prefix2, prefix3 = self.prefixes
                
                if prefix1 and prefix2 and prefix3:
                    new_name = f"{prefix1}_{prefix2}_{prefix3}_{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
                elif prefix1 and prefix2:
                    new_name = f"{prefix1}_{prefix2}_{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
                elif prefix1:
                    new_name = f"{prefix1}_{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
                else:
                    new_name = f"{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
                
                new_file_path = os.path.join(directory, new_name)
                
                if os.path.exists(new_file_path):
                    counter += 1
                    new_name = f"{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
                    new_file_path = os.path.join(directory, new_name)
                
                os.rename(file_path, new_file_path)
                renamed_images.append(new_file_path)
            else:
                renamed_images.append(file_path)
            
            counter += 1
            current_file += 1
            progress_percent = int((current_file / max_progress) * 100)
            self.progress_updated.emit(current_file, f"{progress_percent}%")
        
        return current_file
    
    def apply_image_enhancement(self, renamed_images, start_index, max_progress):
        current_progress = start_index
        
        for image_path in renamed_images:
            img = cv2.imread(image_path)
            if img is None:
                continue
            
            try:
                pil_image = Image.open(image_path)
                exif_data = pil_image.info.get('exif')
            except Exception:
                continue
            
            enhanced_folder = os.path.join(os.path.dirname(image_path), "Enhanced")
            if not os.path.exists(enhanced_folder):
                os.makedirs(enhanced_folder)
            
            enhanced_img_clahe = RecoverCLAHE(img)
            temp_name_clahe = os.path.splitext(os.path.basename(image_path))[0] + '.jpg'
            temp_path_clahe = os.path.join(enhanced_folder, temp_name_clahe)
            cv2.imwrite(temp_path_clahe, enhanced_img_clahe)
            
            try:
                enhanced_pil_image = Image.open(temp_path_clahe)
                if exif_data:
                    enhanced_pil_image.save(temp_path_clahe, exif=exif_data)
                else:
                    enhanced_pil_image.save(temp_path_clahe)
            except Exception:
                continue
            
            current_progress += 1
            progress_percent = int((current_progress / max_progress) * 100)
            self.progress_updated.emit(current_progress, f"{progress_percent}%")


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
    
    def process_images(self):
        try:
            # Get prefix values
            prefixes = [input_field.text() for input_field in self.prefix_inputs]
            
            # Disable the process button
            self.process_btn.setEnabled(False)
            
            # Start processing thread
            self.processing_thread = ImageProcessingThread(
                self.paths, 
                prefixes,
                self.enhancement_checkbox.isChecked(),
                self.rename_checkbox.isChecked()
            )
            self.processing_thread.progress_updated.connect(self.update_progress)
            self.processing_thread.finished_processing.connect(self.processing_finished)
            self.processing_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            self.process_btn.setEnabled(True)
    
    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)
    
    def processing_finished(self, success, message):
        self.process_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
    
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
        files = [f for f in os.listdir(left_folder) if os.path.isfile(os.path.join(left_folder, f))]
        if not files:
            QMessageBox.warning(self, "Warning", "No images found in the left folder.")
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
    
    def delete_temp_folder(self):
        for filename in os.listdir(self.temp_folder):
            file_path = os.path.join(self.temp_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        if not os.listdir(self.temp_folder):
            os.rmdir(self.temp_folder)
    
    def display_image(self, image_path):
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            self.image_preview.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_preview.setPixmap(scaled_pixmap)
    
    def show_gopro_qr(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("GoPro QR Code")
        dialog.setWindowIcon(self.windowIcon())
        
        # Load QR code image
        image_path = os.path.join(os.path.dirname(__file__), "gopro_qr_code.png")
        if os.path.isfile(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio)
            dialog.setIconPixmap(scaled_pixmap)
        
        text = ("SETTINGS\n\n"
                "White-Balance: Auto\n\n\n"
                "YOU NEED THE LABS FIRMWARE IN ORDER TO USE IT. PLEASE, REFER TO DOCUMENTATION.\n\n"
                "PLEASE, REMEMBER TO TURN ON INTERVALOMETER FUNCTION ON THE GOPRO.")
        
        dialog.setText(text)
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