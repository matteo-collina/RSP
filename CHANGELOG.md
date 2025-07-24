# Changelog

All notable changes to the GPSP (GoPro Stereo Photogrammetry) Image Processor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-07-24

### Added
- **EXIF-based image sorting**: Images are now sorted by actual capture timestamp from EXIF data instead of unreliable file modification times
- **Flexible sorting options**: Users can choose between EXIF date taken (recommended), filename alphabetical, or file modification time
- **Multi-threaded image enhancement**: Parallel processing with CLAHE (Contrast Limited Adaptive Histogram Equalization)
- **Stereo camera support**: Handles left, right, and center camera workflows
- **Batch renaming system**: Customizable prefixes with automatic sequential numbering
- **Metashape integration scripts**: 
  - `stereo_scale.py`: Automated scalebar creation for stereo pairs
  - `stereo_calibration.py`: Camera calibration workflows
  - `stereo_report.py`: Analysis and reporting tools
- **Cross-platform GUI**: Modern PyQt6-based interface with intuitive controls
- **Image enhancement preview**: Test enhancement algorithms before batch processing
- **Progress tracking**: Real-time progress bars and status updates
- **File validation**: Automatic detection and filtering of valid image files

### Fixed
- **Critical sorting bug**: Images no longer get shuffled during batch renaming
- **EXIF date parsing**: Robust handling of various EXIF date formats and corrupted data
- **Thread safety**: Proper synchronization for multi-threaded operations
- **File conflict handling**: Safe renaming with automatic conflict resolution

### Technical Details
- Built with Python 3.12+
- Dependencies: PyQt6, OpenCV, NumPy, Pillow
- Supports JPEG, PNG, TIFF, and other common image formats
- Optimized for stereo photogrammetry workflows
- Compatible with Agisoft Metashape Professional

### Known Issues
- None reported for this stable release

---

## How to Use This Release

1. **Download**: Get the source code from the [v0.1.0 release](https://github.com/matteo-collina/GPSP/releases/tag/v0.1.0)
2. **Install**: Follow the instructions in `INSTALL.md`
3. **Run**: Execute `python main.py` to start the application
4. **Sort Settings**: Use "EXIF Date Taken (Recommended)" for best results

### Reverting to This Version
If you need to return to this stable state later:
```bash
git checkout v0.1.0
```

### Next Steps
Future releases will focus on:
- Enhanced Metashape automation
- Additional image enhancement algorithms
- Improved batch processing workflows
- Performance optimizations
