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

from config.settings import OPTIMAL_THREADS, MIN_THREADS
from src.core.pipeline import run_processing_pipeline
from src.core.image_enhancement import ENHANCEMENT_METHODS, DEFAULT_PARAMS
from src.utils.ui_utils import format_time  # pure Python, no PyQt6 -- see ui_utils.py's docstring

# NOTE: all CLI output must stay plain ASCII. Windows consoles commonly
# use the cp1252 codepage, where printing emoji raises UnicodeEncodeError
# -- which then masks the actual error being reported.


class CLIProcessor:
    """Command-line front-end: prints the shared pipeline's progress.

    The actual rename/enhance logic lives in src/core/pipeline.py,
    shared with the GUI's background thread.
    """

    @staticmethod
    def _print_progress(current, maximum, status_text):
        if maximum > 0:
            percent = int((current / maximum) * 100)
            print(f"Progress: {current}/{maximum} ({percent}%) - {status_text}")

    def process_images(self, paths, prefixes, enhancement_enabled, rename_enabled, num_threads,
                        sort_method="exif", enhancement_method="clahe", enhancement_params=None):
        """Run the pipeline, printing progress. Returns True on success."""
        print("Starting RSP Image Processing...")
        start_time = time.time()

        try:
            total_files = run_processing_pipeline(
                paths, prefixes, enhancement_enabled, rename_enabled, num_threads,
                sort_method=sort_method,
                enhancement_method=enhancement_method,
                enhancement_params=enhancement_params,
                progress_callback=self._print_progress,
                log=print,
            )
            if total_files == 0:
                print("No valid image files found in the specified directories.")
                return False

            print(f"\n[OK] Processing completed successfully! ({total_files} images)")
            print(f"Total processing time: {format_time(time.time() - start_time)}")
            return True

        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")
            print(f"Time elapsed: {format_time(time.time() - start_time)}")
            return False


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
  python rsp.py --center /path/to/center --prefix1 "dive1" --prefix2 "site1" --sort filename
  python rsp.py --left /path/to/left --right /path/to/right --thread 8 --rename false --enhance true
  python rsp.py --left /path/to/left --enhance true --method gray_world --param saturation=1.3
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
    parser.add_argument('--sort', type=str, choices=['exif', 'filename', 'mtime'], default='exif',
                       help='Order images are sorted in before renaming: exif (camera '
                            'timestamp), filename (alphabetical), or mtime (file modification '
                            'time). Only affects --rename (default: exif)')
    parser.add_argument('--method', type=str, choices=list(ENHANCEMENT_METHODS.keys()), default='clahe',
                       help='Enhancement method (default: clahe)')
    parser.add_argument('--param', action='append', default=[], metavar='KEY=VALUE',
                       help="Override an enhancement parameter, e.g. --param saturation=1.3 "
                            "(repeatable; unknown keys for the chosen --method are an error)")

    # Parse arguments
    args = parser.parse_args()

    # Parse --param key=value overrides
    enhancement_params = dict(DEFAULT_PARAMS.get(args.method, {}))
    for entry in args.param:
        if '=' not in entry:
            print(f"Error: --param must be KEY=VALUE, got: {entry!r}")
            sys.exit(1)
        key, _, value = entry.partition('=')
        if key not in enhancement_params:
            print(f"Error: unknown parameter {key!r} for method {args.method!r}. "
                  f"Valid keys: {sorted(enhancement_params.keys())}")
            sys.exit(1)
        if not isinstance(enhancement_params[key], (int, float)):
            print(f"Error: {key!r} isn't a plain number (default is {enhancement_params[key]!r}) "
                  f"and can't be set via --param.")
            sys.exit(1)
        try:
            enhancement_params[key] = float(value)
        except ValueError:
            print(f"Error: --param {key} value must be a number, got: {value!r}")
            sys.exit(1)
    
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
    if rename_enabled:
        print(f"Sort method: {args.sort}")
    print(f"Enhance images: {enhancement_enabled}")
    if enhancement_enabled:
        print(f"Enhancement method: {args.method}")
        print(f"Enhancement parameters: {enhancement_params}")
    print("=" * 50)

    # Create processor and run
    processor = CLIProcessor()
    success = processor.process_images(
        valid_paths,
        prefixes,
        enhancement_enabled,
        rename_enabled,
        num_threads,
        sort_method=args.sort,
        enhancement_method=args.method,
        enhancement_params=enhancement_params,
    )
    
    sys.exit(0 if success else 1)


def run_gui():
    """Launch the GUI mode."""
    # Must run before any PyQt6 import below: PyQt6 ships stale MSVC
    # runtime DLLs in Qt6/bin and puts that dir on the DLL search path
    # at import, and torch's c10.dll needs a newer runtime -- importing
    # torch afterward fails hard (WinError 1114). Loading torch first
    # binds its runtime deps to System32's current copies instead. See
    # gray_world.warmup(). The GUI can't know in advance
    # whether the user will pick the Adaptive Grading method, so this
    # always runs here -- unlike CLI mode, which only pays this cost
    # when gray_world is actually requested (see run_cli()).
    from src.core.gray_world import warmup as _warmup_torch
    _warmup_torch()

    from PyQt6.QtWidgets import QApplication
    from src.ui.main_window import ImageProcessor
    from src.ui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    apply_theme(app)  # Dark, glass-inspired theme

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