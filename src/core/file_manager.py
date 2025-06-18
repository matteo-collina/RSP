"""
File management and renaming operations.
"""

import os
from src.core.image_processor import ImageProcessor


class FileManager:
    """Handles file operations like renaming and directory management."""
    
    @staticmethod
    def get_image_files_with_timestamps(directory):
        """Get all valid image files with their timestamps."""
        files = []
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if (os.path.isfile(file_path) and 
                not filename.startswith('.') and 
                ImageProcessor.is_valid_image_file(filename)):
                files.append((filename, os.path.getmtime(file_path)))
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
