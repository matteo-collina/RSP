#!/usr/bin/env python3
"""
RSP Image Processor - Unified Entry Point

Usage:
  python rsp.py                    # Launch GUI (no arguments)
  python rsp.py [CLI arguments]    # Run CLI mode (any arguments present)
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from config.settings import OPTIMAL_THREADS, MIN_THREADS
from src.core.file_manager import FileManager
from src.core.image_processor import ImageProcessor


class CLIProcessor:
    """Command-line processor for RSP."""
    
    def __init__(self):
        self.progress_lock = Lock()
        self.total_files = 0
        self.current_progress = 0
        self.start_time = None
    
    def process_images(self, paths, prefixes, enhancement_enabled, rename_enabled, num_threads, sort_method="exif"):
        """Process images with the given parameters."""
        print("Starting RSP Image Processing...")
        self.start_time = time.time()
        
        try:
            # Count total files
            self.total_files = self._count_total_files(paths)
            if self.total_files == 0:
                print("No valid image files found in the specified directories.")
                return False
            
            print(f"Found {self.total_files} images to process")
            
            if enhancement_enabled:
                max_progress = self.total_files * 2  # rename + enhancement
                print("Processing mode: Rename + Enhancement")
            else:
                max_progress = self.total_files  # just rename
                print("Processing mode: Rename only")
                
            self.current_progress = 0
            processed_images = []
            
            # Process files phase (rename and collect valid paths)
            print("\n--- Phase 1: Processing and Renaming Files ---")
            for prefix, path in paths.items():
                if path:
                    print(f"Processing {prefix} directory: {path}")
                    self.current_progress = self._process_directory(
                        path, prefix, self.current_progress, processed_images, max_progress, prefixes, rename_enabled, sort_method
                    )
            
            # Enhancement phase (if enabled)
            if enhancement_enabled:
                print(f"\n--- Phase 2: Enhancing {len(processed_images)} Images ---")
                # Filter out any invalid paths before enhancement
                valid_images = [img_path for img_path in processed_images if os.path.exists(img_path) and os.path.isfile(img_path)]
                
                if valid_images:
                    self._apply_enhancement_multithreaded(valid_images, self.current_progress, max_progress, num_threads)
                else:
                    print("Warning: No valid images found for enhancement")
            else:
                self._update_progress(max_progress, max_progress, "Processing complete")
            
            # Calculate processing time
            processing_time = time.time() - self.start_time
            print(f"\n✅ Processing completed successfully!")
            print(f"⏱️  Total processing time: {self._format_time(processing_time)}")
            return True
            
        except Exception as e:
            processing_time = time.time() - self.start_time if self.start_time else 0
            print(f"❌ An error occurred: {e}")
            print(f"⏱️  Time elapsed: {self._format_time(processing_time)}")
            return False
    
    def _count_total_files(self, paths):
        """Count total valid image files across all directories."""
        total = 0
        for path in paths.values():
            if path and os.path.exists(path):
                files = FileManager.get_image_files_with_timestamps(path, "exif")
                total += len(files)
        return total
    
    def _process_directory(self, directory, prefix, current_progress, processed_images, max_progress, prefixes, rename_enabled, sort_method):
        """Process (and optionally rename) files in directory."""
        try:
            files = FileManager.get_image_files_with_timestamps(directory, sort_method)
            
            if rename_enabled:
                files.sort(key=lambda x: x[1])  # Sort by timestamp/filename
            
            counter = 0
            for filename, _ in files:
                old_file_path = os.path.join(directory, filename)
                
                if rename_enabled:
                    new_file_path = FileManager.generate_new_filename(
                        directory, filename, prefixes, prefix, counter
                    )
                    final_path = FileManager.rename_file_safely(old_file_path, new_file_path)
                    processed_images.append(final_path)
                    print(f"  Renamed: {filename} -> {os.path.basename(final_path)}")
                else:
                    processed_images.append(old_file_path)
                    print(f"  Processed: {filename}")
                
                counter += 1
                current_progress += 1
                self._update_progress(current_progress, max_progress, f"Processing {prefix} images")
        
        except Exception as e:
            print(f"Error processing directory {directory}: {e}")
        
        return current_progress
    
    def _apply_enhancement_multithreaded(self, image_paths, start_progress, max_progress, num_threads):
        """Apply image enhancement using multiple threads."""
        current_progress = start_progress
        
        print(f"Using {num_threads} threads for enhancement")
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
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
                    if success:
                        print(f"  ✅ Enhanced: {os.path.basename(image_path)}")
                    else:
                        print(f"  ⚠️  Warning: {message}")
                except Exception as e:
                    print(f"  ❌ Exception processing {os.path.basename(image_path)}: {e}")
                
                # Thread-safe progress update
                with self.progress_lock:
                    current_progress += 1
                    self._update_progress(current_progress, max_progress, "Enhancing images")
    
    def _update_progress(self, current, maximum, status_text):
        """Update progress display."""
        if maximum > 0:
            percent = int((current / maximum) * 100)
            print(f"Progress: {current}/{maximum} ({percent}%) - {status_text}")
    
    def _format_time(self, seconds):
        """Format time in seconds to a human-readable string."""
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


def validate_directory(path):
    """Validate that a directory path exists and is readable."""
    if not path:
        return False
    if not os.path.exists(path):
        print(f"Error: Directory does not exist: {path}")
        return False
    if not os.path.isdir(path):
        print(f"Error: Path is not a directory: {path}")
        return False
    return True


def run_cli():
    """Run the CLI mode."""
    parser = argparse.ArgumentParser(
        prog='rsp.py',
        description="RSP Image Processor - Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rsp.py --left /path/to/left --right /path/to/right --rename true --enhance true
  python rsp.py --center /path/to/center --prefix1 "dive1" --prefix2 "site1" --thread auto
  python rsp.py --left /path/to/left --right /path/to/right --thread 8 --rename false --enhance true
        """
    )
    
    # Prefix arguments
    parser.add_argument('--prefix1', type=str, default='', 
                       help='First prefix for file naming')
    parser.add_argument('--prefix2', type=str, default='', 
                       help='Second prefix for file naming')
    parser.add_argument('--prefix3', type=str, default='', 
                       help='Third prefix for file naming')
    
    # Thread argument
    parser.add_argument('--thread', type=str, default='auto',
                       help='Number of processing threads (minimum 1) or "auto" for optimal count (default: auto)')
    
    # Directory arguments
    parser.add_argument('--center', type=str, default='',
                       help='Path to center images directory')
    parser.add_argument('--left', type=str, default='',
                       help='Path to left images directory')
    parser.add_argument('--right', type=str, default='',
                       help='Path to right images directory')
    
    # Processing options
    parser.add_argument('--rename', type=str, choices=['true', 'false'], default='true',
                       help='Rename files with prefixes (default: true)')
    parser.add_argument('--enhance', type=str, choices=['true', 'false'], default='false',
                       help='Apply image enhancement (default: false)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and process thread argument
    if args.thread.lower() == 'auto':
        num_threads = OPTIMAL_THREADS
        print(f"Using automatic thread count: {num_threads} threads")
    else:
        try:
            num_threads = int(args.thread)
            if num_threads < MIN_THREADS:
                print(f"Error: Thread count must be at least {MIN_THREADS}")
                sys.exit(1)
        except ValueError:
            print(f"Error: Invalid thread count '{args.thread}'. Use a positive number or 'auto'")
            sys.exit(1)
    
    # Validate directories
    paths = {
        'center': args.center,
        'left': args.left,
        'right': args.right
    }
    
    # Remove empty paths and validate existing ones
    valid_paths = {}
    for prefix, path in paths.items():
        if path:  # Only process non-empty paths
            if validate_directory(path):
                valid_paths[prefix] = path
            else:
                sys.exit(1)  # Exit if any specified directory is invalid
    
    if not valid_paths:
        print("Error: At least one directory (--center, --left, or --right) must be specified")
        sys.exit(1)
    
    # Convert string booleans to actual booleans
    rename_enabled = args.rename.lower() == 'true'
    enhancement_enabled = args.enhance.lower() == 'true'
    
    # Check that at least one processing option is enabled
    if not rename_enabled and not enhancement_enabled:
        print("Error: At least one processing option (--rename or --enhance) must be set to 'true'")
        sys.exit(1)
    
    # Setup prefixes
    prefixes = [args.prefix1, args.prefix2, args.prefix3]
    
    # Display configuration
    print("RSP Image Processor - CLI Mode")
    print("=" * 50)
    print(f"Directories: {list(valid_paths.keys())}")
    print(f"Prefixes: {[p for p in prefixes if p]}")  # Only show non-empty prefixes
    print(f"Threads: {num_threads}")
    print(f"Rename files: {rename_enabled}")
    print(f"Enhance images: {enhancement_enabled}")
    print("=" * 50)
    
    # Create processor and run
    processor = CLIProcessor()
    success = processor.process_images(
        valid_paths, 
        prefixes,
        enhancement_enabled,
        rename_enabled,
        num_threads
    )
    
    sys.exit(0 if success else 1)


def run_gui():
    """Launch the GUI mode."""
    from PyQt6.QtWidgets import QApplication
    from src.ui.main_window import ImageProcessor
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = ImageProcessor()
    window.show()
    
    sys.exit(app.exec())


def main():
    """Main entry point - smart detection of GUI vs CLI mode."""
    
    # If no arguments provided, launch GUI
    if len(sys.argv) == 1:
        print("RSP Image Processor - Starting GUI...")
        run_gui()
    else:
        # Any arguments present = CLI mode
        run_cli()


if __name__ == "__main__":
    main()