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
conda activate rsp
```

3. Run the application:
```bash
python rsp.py              # GUI mode (no arguments)
python rsp.py --help       # CLI mode help
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
python rsp.py              # GUI mode (no arguments)  
python rsp.py --help       # CLI mode help
```


