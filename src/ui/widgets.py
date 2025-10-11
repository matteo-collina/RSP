"""
Custom widgets for the application.
"""

import os
import random
import cv2
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QFileDialog, QCheckBox, 
                            QProgressBar, QSpinBox, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

from config.settings import (UNIVERSITY_LOGO, LEFT_PANEL_WIDTH, IMAGE_PREVIEW_MIN_WIDTH,
                           IMAGE_PREVIEW_MIN_HEIGHT, OPTIMAL_THREADS, GUI_MAX_THREADS, MIN_THREADS,
                           DEFAULT_CPU_COUNT)
from src.core.image_processor import ImageProcessor
from src.core.image_enhancement import apply_clahe_enhancement


class LeftPanel(QWidget):
    """Left panel containing controls and inputs."""
    
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setFixedWidth(LEFT_PANEL_WIDTH)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the left panel UI."""
        layout = QVBoxLayout(self)
        
        # Logo
        if os.path.isfile(UNIVERSITY_LOGO):
            logo_label = QLabel()
            pixmap = QPixmap(UNIVERSITY_LOGO)
            logo_label.setPixmap(pixmap.scaled(300, 100, Qt.AspectRatioMode.KeepAspectRatio))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)
        
        # Add spacing under the logo
        layout.addSpacing(15)
        
        # Prefix inputs
        self.prefix_inputs = []
        for i in range(1, 4):
            prefix_layout = QHBoxLayout()
            prefix_label = QLabel(f"Prefix {i}:")
            prefix_input = QLineEdit()
            prefix_layout.addWidget(prefix_label)
            prefix_layout.addWidget(prefix_input)
            layout.addLayout(prefix_layout)
            self.prefix_inputs.append(prefix_input)
        
        # Thread count selection
        thread_layout = QHBoxLayout()
        thread_label = QLabel("Processing Threads:")
        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setMinimum(MIN_THREADS)
        self.thread_spinbox.setMaximum(GUI_MAX_THREADS)
        self.thread_spinbox.setValue(OPTIMAL_THREADS)
        self.thread_spinbox.setToolTip(f"Number of threads for image enhancement\n"
                                     f"Detected {DEFAULT_CPU_COUNT} logical CPU cores\n"
                                     f"Default: {OPTIMAL_THREADS} threads (optimized for image processing)\n"
                                     f"Apple Silicon: Uses ALL Performance cores\n"
                                     f"Intel/AMD: Uses estimated physical cores (no hyperthreading)")
        
        # AUTO button to reset to optimal threads
        auto_btn = QPushButton("AUTO")
        auto_btn.setMaximumWidth(60)
        auto_btn.setToolTip(f"Reset to optimal thread count ({OPTIMAL_THREADS} threads)\n"
                           f"Automatically optimized for your CPU architecture")
        auto_btn.clicked.connect(lambda: self.thread_spinbox.setValue(OPTIMAL_THREADS))
        
        thread_layout.addWidget(thread_label)
        thread_layout.addWidget(self.thread_spinbox)
        thread_layout.addWidget(auto_btn)
        layout.addLayout(thread_layout)
        
        # Directory selection
        self.path_labels = {}
        self.browse_buttons = {}
        self.clear_buttons = {}
        
        for prefix in self.parent.paths:
            # Directory label
            dir_label = QLabel(f"Select {prefix} directory:")
            layout.addWidget(dir_label)
            
            # Path display
            path_label = QLabel("No directory selected")
            path_label.setStyleSheet("border: 1px solid gray; padding: 5px;")
            layout.addWidget(path_label)
            self.path_labels[prefix] = path_label
            
            # Buttons
            button_layout = QHBoxLayout()
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda checked, p=prefix: self.browse_directory(p))
            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked, p=prefix: self.clear_directory(p))
            
            button_layout.addWidget(browse_btn)
            button_layout.addWidget(clear_btn)
            layout.addLayout(button_layout)
            
            self.browse_buttons[prefix] = browse_btn
            self.clear_buttons[prefix] = clear_btn
        
        # Clear all button
        clear_all_btn = QPushButton("Clear All Directories")
        clear_all_btn.clicked.connect(self.clear_all_directories)
        layout.addWidget(clear_all_btn)
        
        # Checkboxes
        self.enhancement_checkbox = QCheckBox("Image Enhancement")
        self.enhancement_checkbox.toggled.connect(self.parent.toggle_enhancement_section)
        layout.addWidget(self.enhancement_checkbox)
        
        self.rename_checkbox = QCheckBox("Rename Images")
        self.rename_checkbox.setChecked(True)
        layout.addWidget(self.rename_checkbox)
        
        # Sorting method selection
        sorting_layout = QHBoxLayout()
        sorting_label = QLabel("Sort images by:")
        self.sorting_combo = QComboBox()
        self.sorting_combo.addItems([
            "EXIF Date Taken (Recommended)", 
            "Filename (Alphabetical)", 
            "File Modification Time"
        ])
        self.sorting_combo.setToolTip("Choose how to sort images before renaming:\n"
                                    "• EXIF Date Taken: Uses camera timestamp (most accurate)\n"
                                    "• Filename: Alphabetical order\n"
                                    "• File Modification Time: When file was last modified")
        sorting_layout.addWidget(sorting_label)
        sorting_layout.addWidget(self.sorting_combo)
        layout.addLayout(sorting_layout)
        
        # Process button
        self.process_btn = QPushButton("Process Images")
        self.process_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.process_btn.setMinimumHeight(50)
        self.process_btn.clicked.connect(self.parent.process_images)
        layout.addWidget(self.process_btn)
        
        # Progress status and bar
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)  # Ensure percentage is visible
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
    
    def browse_directory(self, prefix):
        """Browse for a directory."""
        directory = QFileDialog.getExistingDirectory(self, f"Select {prefix} directory")
        if directory:
            self.parent.paths[prefix] = directory
            self.path_labels[prefix].setText(directory)
    
    def clear_directory(self, prefix):
        """Clear a directory selection."""
        self.parent.paths[prefix] = ""
        self.path_labels[prefix].setText("No directory selected")
    
    def clear_all_directories(self):
        """Clear all directory selections."""
        for prefix in self.parent.paths:
            self.clear_directory(prefix)


class RightPanel(QWidget):
    """Right panel containing image preview and enhancement controls."""
    
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setMinimumWidth(IMAGE_PREVIEW_MIN_WIDTH)
        self.current_pixmap = None  # Store current image in memory
        self.setup_ui()
        self.hide()  # Initially hidden
    
    def setup_ui(self):
        """Setup the right panel UI."""
        layout = QVBoxLayout(self)
        
        # Image preview
        self.image_preview = QLabel()
        self.image_preview.setMinimumSize(IMAGE_PREVIEW_MIN_WIDTH, IMAGE_PREVIEW_MIN_HEIGHT)
        self.image_preview.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setText("Image preview will appear here")
        layout.addWidget(self.image_preview)
        
        # Test button
        test_btn = QPushButton("Test Image Enhancement")
        test_btn.clicked.connect(self.test_image_enhancement)
        layout.addWidget(test_btn)
    
    def test_image_enhancement(self):
        """Test image enhancement with a random image from the left folder."""
        left_folder = self.parent.paths.get("left")
        if not left_folder:
            from src.ui.dialogs import show_message_box
            show_message_box(self, "Warning", 
                          "Left folder is not selected.\nPlease select a left folder in the main panel.",
                          "warning")
            return
        
        # Clean previous image from memory
        self.clear_memory()
        
        # Select random image
        from src.core.file_manager import FileManager
        file_data = FileManager.get_image_files_with_timestamps(left_folder, "filename")
        files = [filename for filename, _ in file_data]
        
        if not files:
            from src.ui.dialogs import show_message_box
            show_message_box(self, "Warning", "No valid images found in the left folder.", "warning")
            return
        
        random_file = random.choice(files)
        random_image_path = os.path.join(left_folder, random_file)
        
        # Load and process image in memory
        img = cv2.imread(random_image_path)
        if img is not None:
            if self.parent.left_panel.enhancement_checkbox.isChecked():
                img = apply_clahe_enhancement(img)
            self.display_cv2_image(img)
    
    def display_cv2_image(self, cv2_img):
        """Display a CV2 image in the preview label (memory-based)."""
        try:
            # Convert CV2 image (BGR) to RGB
            rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            
            # Create QImage from RGB data
            from PyQt6.QtGui import QImage
            q_image = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Convert to pixmap and scale
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.image_preview.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Clean previous pixmap and store new one
            self.clear_memory()
            self.current_pixmap = scaled_pixmap
            self.image_preview.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Warning: Could not display image: {e}")
    
    def clear_memory(self):
        """Clear current image from memory."""
        if self.current_pixmap is not None:
            self.current_pixmap = None
            self.image_preview.clear()
