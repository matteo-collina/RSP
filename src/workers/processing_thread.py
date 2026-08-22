"""
Background processing thread for image operations.

Thin Qt wrapper around the shared engine in src/core/pipeline.py: this
class only owns the QThread lifecycle and signal plumbing -- the actual
rename/enhance logic lives in the engine, shared with the CLI.
"""

import time
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.pipeline import run_processing_pipeline


class ImageProcessingThread(QThread):
    """Background thread for processing images."""

    progress_updated = pyqtSignal(int, int, str)  # current, maximum, status_text
    finished_processing = pyqtSignal(bool, str, float, int)  # success, message, processing_time, total_files

    def __init__(self, paths, prefixes, enhancement_enabled, rename_enabled, num_threads=4,
                 sort_method="exif", enhancement_method="clahe", enhancement_params=None):
        super().__init__()
        self.paths = paths
        self.prefixes = prefixes
        self.enhancement_enabled = enhancement_enabled
        self.rename_enabled = rename_enabled
        self.num_threads = num_threads
        self.sort_method = sort_method  # 'exif', 'filename', or 'mtime'
        self.enhancement_method = enhancement_method  # registry key, e.g. 'clahe'
        self.enhancement_params = enhancement_params
        self.total_files = 0  # for the finished_processing signal / report

    def run(self):
        start_time = time.time()
        try:
            self.total_files = run_processing_pipeline(
                self.paths,
                self.prefixes,
                self.enhancement_enabled,
                self.rename_enabled,
                self.num_threads,
                sort_method=self.sort_method,
                enhancement_method=self.enhancement_method,
                enhancement_params=self.enhancement_params,
                progress_callback=self.progress_updated.emit,
            )
            self.finished_processing.emit(
                True, "Processing completed successfully!", time.time() - start_time, self.total_files
            )
        except Exception as e:
            self.finished_processing.emit(
                False, f"An error occurred: {e}", time.time() - start_time, self.total_files
            )
