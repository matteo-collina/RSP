# Image Processor Setup Instructions

## Prerequisites
- Python 3.8 or higher
- Conda (Anaconda or Miniconda)

## Installation Options

### Option 1: Using Conda (Recommended)

1. Create a new conda environment:
```bash
conda env create -f environment.yml
```

2. Activate the environment:
```bash
conda activate GPSP
```

3. Run the application:
```bash
python imageprocessor.py
```
4. When you're done using the application:
```bash
conda deactivate
```

#### Updating Dependencies

To update all packages to their latest versions:
```bash
conda env update -f environment.yml --prune
```

### Option 2: Using pip

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python imageprocessor.py
```

## Required Files

Make sure these files are in your project directory:
- `imageprocessor.py` (your main application file)
- `sceneRadianceCLAHE.py` (custom image processing module)
- `requirements.txt` (Python dependencies)
- `environment.yml` (Conda environment specification)


### Platform-specific Notes:

- **Windows**: May need Visual C++ redistributables for OpenCV
- **macOS**: May need to install additional system dependencies
- **Linux**: May need to install system packages for GUI applications

