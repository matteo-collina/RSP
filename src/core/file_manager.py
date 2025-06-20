"""
File management and renaming operations.
"""

import os
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from src.core.image_processor import ImageProcessor


class FileManager:
    """Handles file operations like renaming and directory management."""
    
    @staticmethod
    def get_exif_date_taken(image_path):
        """Extract the date taken from EXIF data, fallback to file modification time."""
        try:
            with Image.open(image_path) as img:
                exif_data = img.getexif()
                
                if exif_data:
                    # Try different EXIF date tags in order of preference
                    for tag_id in [36867, 36868, 306]:  # DateTimeOriginal, DateTimeDigitized, DateTime
                        if tag_id in exif_data:
                            date_str = exif_data[tag_id]
                            try:
                                # Parse EXIF date format: "YYYY:MM:DD HH:MM:SS"
                                date_taken = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                                return date_taken.timestamp()
                            except ValueError:
                                print(f"Warning: Invalid date format in EXIF for {image_path}: {date_str}")
                                continue
        except Exception as e:
            # This is normal for non-JPEG files or corrupted EXIF data
            pass
        
        # Fallback to file modification time
        return os.path.getmtime(image_path)
    
    @staticmethod
    def get_image_files_with_timestamps(directory, sort_method="exif"):
        """Get all valid image files with their timestamps.
        
        Args:
            directory: Directory to scan for images
            sort_method: 'exif', 'filename', or 'mtime'
        """
        files = []
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if (os.path.isfile(file_path) and 
                not filename.startswith('.') and 
                ImageProcessor.is_valid_image_file(filename)):
                
                if sort_method == "exif":
                    # Use EXIF date taken if available, otherwise file modification time
                    timestamp = FileManager.get_exif_date_taken(file_path)
                elif sort_method == "filename":
                    # Use filename for alphabetical sorting (converted to a comparable format)
                    timestamp = filename.lower()
                else:  # sort_method == "mtime"
                    # Use file modification time
                    timestamp = os.path.getmtime(file_path)
                
                files.append((filename, timestamp))
        return files
    
    @staticmethod
    def generate_new_filename(directory, original_filename, prefixes, dir_prefix, counter):
        """Generate new filename based on prefixes."""
        prefix1, prefix2, prefix3 = prefixes
        file_extension = os.path.splitext(original_filename)[1]
        
        # Build filename with available prefixes
        name_parts = []
        if prefix1:
            name_parts.append(prefix1)
        if prefix2:
            name_parts.append(prefix2)
        if prefix3:
            name_parts.append(prefix3)
        
        name_parts.append(dir_prefix)  # Directory prefix (left/right/center)
        name_parts.append(str(counter).zfill(5))
        
        new_name = "_".join(name_parts) + file_extension
        return os.path.join(directory, new_name)
    
    @staticmethod
    def rename_file_safely(old_path, new_path):
        """Safely rename a file, handling conflicts."""
        if old_path == new_path:
            return old_path
        
        try:
            # Ensure target doesn't exist
            if os.path.exists(new_path):
                base, ext = os.path.splitext(new_path)
                counter = 1
                while os.path.exists(new_path):
                    new_path = f"{base}_{counter}{ext}"
                    counter += 1
            
            os.rename(old_path, new_path)
            return new_path
        except OSError as e:
            print(f"Warning: Could not rename {old_path}: {e}")
            return old_path
