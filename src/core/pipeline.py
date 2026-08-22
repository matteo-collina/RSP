"""
Shared two-phase (rename -> enhance) processing engine.

This is the single implementation behind both front-ends:
- the GUI's background thread (src/workers/processing_thread.py), which
  forwards progress to Qt signals, and
- the CLI (rsp.py's CLIProcessor), which prints progress to stdout.

Both used to carry near-identical copies of this logic; any change to
the pipeline belongs here, once.

No Qt imports allowed in this module -- it must stay usable by the CLI
path, which never loads PyQt6 (see src/utils/ui_utils.py's docstring).
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from src.core.file_manager import FileManager
from src.core.image_processor import ImageProcessor
from src.core.image_enhancement import warmup_method


def count_total_files(paths, sort_method="exif"):
    """Count valid image files across all non-empty directories."""
    total = 0
    for path in paths.values():
        if path and os.path.exists(path):
            files = FileManager.get_image_files_with_timestamps(path, sort_method)
            total += len(files)
    return total


def run_processing_pipeline(paths, prefixes, enhancement_enabled, rename_enabled,
                            num_threads, sort_method="exif",
                            enhancement_method="clahe", enhancement_params=None,
                            progress_callback=None, log=None):
    """Run the full rename/enhance pipeline over the given directories.

    Args:
        paths: dict of {prefix: directory}, e.g. {"left": "...", ...};
            empty-string directories are skipped.
        prefixes: [prefix1, prefix2, prefix3] naming prefixes for renames.
        enhancement_enabled / rename_enabled: which phases to run.
        num_threads: worker count for the enhancement phase.
        sort_method: 'exif', 'filename', or 'mtime'.
        enhancement_method: registry key from ENHANCEMENT_METHODS.
        enhancement_params: optional dict of method-specific parameters.
        progress_callback: optional callable(current, maximum, status_text).
        log: optional callable(message) for detailed per-file/phase lines
            (the CLI passes print; the GUI passes nothing).

    Returns:
        Total number of image files found across all directories.

    Raises:
        Propagates unexpected errors to the caller (both front-ends wrap
        this call and surface the failure their own way).
    """
    progress = progress_callback or (lambda *_: None)
    log = log or (lambda _: None)

    total_files = count_total_files(paths, sort_method)
    if total_files == 0:
        return 0

    max_progress = total_files * 2 if enhancement_enabled else total_files
    current_progress = 0
    processed_images = []

    log("--- Phase 1: Processing and Renaming Files ---")
    for prefix, path in paths.items():
        if not path:
            continue
        log(f"Processing {prefix} directory: {path}")
        current_progress = _process_directory(
            path, prefix, current_progress, processed_images, max_progress,
            prefixes, rename_enabled, sort_method, progress, log
        )

    if enhancement_enabled:
        valid_images = []
        for img_path in processed_images:
            if os.path.exists(img_path) and os.path.isfile(img_path):
                valid_images.append(img_path)
            else:
                log(f"[WARN] File not found or invalid: {img_path}")

        if valid_images:
            log(f"--- Phase 2: Enhancing {len(valid_images)} Images ---")
            _apply_enhancement_multithreaded(
                valid_images, current_progress, max_progress, num_threads,
                enhancement_method, enhancement_params, progress, log
            )
        else:
            log("[WARN] No valid images found for enhancement")
    else:
        # Ensure the progress bar reaches 100% for rename-only runs.
        progress(max_progress, max_progress, "Renaming complete")

    return total_files


def _process_directory(directory, prefix, current_progress, processed_images,
                       max_progress, prefixes, rename_enabled, sort_method,
                       progress, log):
    """Phase 1: rename (optional) and collect the files of one directory."""
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
                log(f"  Renamed: {filename} -> {os.path.basename(final_path)}")
            else:
                processed_images.append(old_file_path)
                log(f"  Collected: {filename}")

            counter += 1
            current_progress += 1
            status_text = f"Processing {prefix} images" if rename_enabled else f"Collecting {prefix} images"
            progress(current_progress, max_progress, status_text)

    except Exception as e:
        log(f"[ERROR] Error processing directory {directory}: {e}")

    return current_progress


def _apply_enhancement_multithreaded(image_paths, start_progress, max_progress,
                                     num_threads, method, params, progress, log):
    """Phase 2: apply the selected enhancement across worker threads."""
    current_progress = start_progress
    progress_lock = Lock()

    # Must happen on the orchestrating thread before any worker touches
    # the method: gray_world's torch import has a strict load-order
    # requirement on Windows -- see gray_world.warmup().
    warmup_method(method)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_image = {
            executor.submit(ImageProcessor.process_single_image, image_path, method, params): image_path
            for image_path in image_paths
        }

        for future in as_completed(future_to_image):
            image_path = future_to_image[future]

            try:
                success, message = future.result()
                if success:
                    log(f"  [OK] Enhanced: {os.path.basename(image_path)}")
                else:
                    log(f"  [WARN] {message}")
            except Exception as e:
                log(f"  [ERROR] Exception processing {os.path.basename(image_path)}: {e}")

            with progress_lock:
                current_progress += 1
                progress(current_progress, max_progress, "Enhancing images")
