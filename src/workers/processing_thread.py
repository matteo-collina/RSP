"""
Background processing thread for image operations.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.image_processor import ImageProcessor
from src.core.file_manager import FileManager


class ImageProcessingThread(QThread):
    """Background thread for processing images."""
    
    progress_updated = pyqtSignal(int, int, str)  # current, maximum, status_text
    finished_processing = pyqtSignal(bool, str, float)  # success, message, processing_time
    
    def __init__(self, paths, prefixes, enhancement_enabled, rename_enabled, num_threads=4, sort_method="exif"):
        super().__init__()
        self.paths = paths
        self.prefixes = prefixes
        self.enhancement_enabled = enhancement_enabled
        self.rename_enabled = rename_enabled
        self.num_threads = num_threads
        self.sort_method = sort_method  # 'exif', 'filename', or 'mtime'
        self.progress_lock = Lock()  # Thread-safe progress updates
        self.start_time = None
    
    def run(self):
        """Main processing loop."""
        # Record start time
        self.start_time = time.time()
        
        try:
            total_files = self._count_total_files()
            
            if self.enhancement_enabled:
                max_progress = total_files * 2  # rename + enhancement
            else:
                max_progress = total_files  # just rename
                
            current_progress = 0
            processed_images = []  # Changed from renamed_images to processed_images
            
            # Process files phase (rename and collect valid paths)
            for prefix, path in self.paths.items():
                if path:
                    current_progress = self._process_directory(
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
                    self._apply_enhancement_multithreaded(valid_images, current_progress, max_progress)
                else:
                    print("Warning: No valid images found for enhancement")
            else:
                # Ensure we reach 100% for rename-only operations
                self.progress_updated.emit(max_progress, max_progress, "Renaming complete")
            
            # Calculate processing time
            processing_time = time.time() - self.start_time
            self.finished_processing.emit(True, "Processing completed successfully!", processing_time)
            
        except Exception as e:
            processing_time = time.time() - self.start_time if self.start_time else 0
            self.finished_processing.emit(False, f"An error occurred: {e}", processing_time)
    
    def _count_total_files(self):
        """Count total valid image files across all directories."""
        total = 0
        for path in self.paths.values():
            if path and os.path.exists(path):
                files = FileManager.get_image_files_with_timestamps(path, self.sort_method)
                total += len(files)
        return total
    
    def _process_directory(self, directory, prefix, current_progress, processed_images, max_progress):
        """Process (and optionally rename) files in directory"""
        try:
            files = FileManager.get_image_files_with_timestamps(directory, self.sort_method)
            
            if self.rename_enabled:
                files.sort(key=lambda x: x[1])  # Sort by timestamp/filename
            
            counter = 0
            for filename, _ in files:
                old_file_path = os.path.join(directory, filename)
                
                if self.rename_enabled:
                    new_file_path = FileManager.generate_new_filename(
                        directory, filename, self.prefixes, prefix, counter
                    )
                    final_path = FileManager.rename_file_safely(old_file_path, new_file_path)
                    processed_images.append(final_path)
                else:
                    processed_images.append(old_file_path)
                
                counter += 1
                current_progress += 1
                status_text = f"Processing {prefix} images" if self.rename_enabled else f"Collecting {prefix} images"
                self.progress_updated.emit(current_progress, max_progress, status_text)
        
        except Exception as e:
            print(f"Error processing directory {directory}: {e}")
        
        return current_progress
    
    def _apply_enhancement_multithreaded(self, image_paths, start_progress, max_progress):
        """Apply image enhancement using multiple threads."""
        current_progress = start_progress
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(ImageProcessor.process_single_image, image_path): image_path 
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
                    self.progress_updated.emit(current_progress, max_progress, "Enhancing images")
