"""
Core image processing functionality.
"""

import os
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from src.core.image_enhancement import apply_clahe_enhancement
from src.core.file_manager import FileManager


class ImageProcessor:
    """Handles individual image processing operations."""
    
    @staticmethod
    def is_valid_image_file(filename):
        """Check if file is a valid image file."""
        return FileManager.is_valid_image_file(filename)
    
    @staticmethod
    def process_images_multithreaded(image_paths, num_threads, progress_callback=None):
        """
        Process multiple images with enhancement using multiple threads.
        
        Args:
            image_paths: List of image file paths to process
            num_threads: Number of worker threads
            progress_callback: Optional callback function(current, total, success, message)
        
        Returns:
            Tuple (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        total = len(image_paths)
        current = 0
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_image = {
                executor.submit(ImageProcessor.process_single_image, image_path): image_path 
                for image_path in image_paths
            }
            
            for future in as_completed(future_to_image):
                image_path = future_to_image[future]
                current += 1
                
                try:
                    success, message = future.result()
                    if success:
                        successful += 1
                    else:
                        failed += 1
                    
                    if progress_callback:
                        progress_callback(current, total, success, message)
                        
                except Exception as e:
                    failed += 1
                    if progress_callback:
                        progress_callback(current, total, False, f"Exception: {str(e)}")
        
        return successful, failed
    
    @staticmethod
    def process_single_image(image_path):
        """Process a single image with enhancement."""
        try:
            # Validate file
            if not os.path.exists(image_path):
                return False, f"File not found: {image_path}"
            
            if not os.path.isfile(image_path):
                return False, f"Path is not a file: {image_path}"
            
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return False, f"Could not read image (corrupted or unsupported format): {image_path}"
            
            # Get EXIF data
            exif_data = ImageProcessor._get_exif_data(image_path)
            
            # Create enhanced folder
            enhanced_folder = os.path.join(os.path.dirname(image_path), "Enhanced")
            os.makedirs(enhanced_folder, exist_ok=True)
            
            # Apply enhancement
            enhanced_img = apply_clahe_enhancement(img)
            output_name = os.path.splitext(os.path.basename(image_path))[0] + '.jpg'
            output_path = os.path.join(enhanced_folder, output_name)
            
            # Save enhanced image
            success = cv2.imwrite(output_path, enhanced_img)
            if not success:
                return False, f"Failed to save enhanced image: {output_path}"
            
            # Preserve EXIF data
            if exif_data:
                ImageProcessor._preserve_exif_data(output_path, exif_data)
            
            return True, f"Successfully processed: {os.path.basename(image_path)}"
            
        except Exception as e:
            return False, f"Error processing {image_path}: {str(e)}"
    
    @staticmethod
    def _get_exif_data(image_path):
        """Extract EXIF data from image."""
        try:
            pil_image = Image.open(image_path)
            exif_data = pil_image.info.get('exif')
            pil_image.close()  # Explicitly close to free resources
            return exif_data
        except Exception as e:
            print(f"Warning: Could not read EXIF data from {image_path}: {e}")
            return None
    
    @staticmethod
    def _preserve_exif_data(image_path, exif_data):
        """Preserve EXIF data in processed image."""
        try:
            enhanced_pil_image = Image.open(image_path)
            enhanced_pil_image.save(image_path, exif=exif_data)
            enhanced_pil_image.close()
        except Exception as e:
            print(f"Warning: Could not preserve EXIF data for {image_path}: {e}")
