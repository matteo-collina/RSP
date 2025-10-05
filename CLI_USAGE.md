# RSP Usage Guide

## Unified Entry Point

The RSP Image Processor has a single entry point that automatically detects whether to launch GUI or CLI mode.

### Basic Usage

```bash
python rsp.py                    # Launch GUI (no arguments)
python rsp.py [CLI options]      # Run CLI mode (any arguments present)
```

### GUI Mode

Launch the graphical interface for interactive processing:

```bash
python rsp.py
```

### CLI Mode

Any command-line arguments will automatically switch to CLI mode for batch processing.

### Required Parameters

At least one directory must be specified:
- `--center PATH`: Path to center images directory
- `--left PATH`: Path to left images directory  
- `--right PATH`: Path to right images directory

### Optional Parameters

**Prefixes (for file naming):**
- `--prefix1 TEXT`: First prefix
- `--prefix2 TEXT`: Second prefix
- `--prefix3 TEXT`: Third prefix

**Processing Options:**
- `--thread NUMBER|auto`: Number of threads (minimum 1, no upper limit) or "auto" (default: auto)
- `--rename true|false`: Rename files with prefixes (default: true)
- `--enhance true|false`: Apply image enhancement (default: false)

### Examples

**Basic rename only:**
```bash
python rsp.py --left /path/to/left --right /path/to/right
```

**Rename with prefixes:**
```bash
python rsp.py --left /path/to/left --prefix1 "dive1" --prefix2 "site1" --rename true
```

**Enhance images only (no renaming):**
```bash
python rsp.py --center /path/to/center --rename false --enhance true
```

**Full processing with custom threads:**
```bash
python rsp.py --left /path/to/left --right /path/to/right --prefix1 "dive1" --thread 8 --rename true --enhance true
```

**High-performance server processing:**
```bash
python rsp.py --left /path/to/left --thread 64 --enhance true
```

### Help

```bash
python rsp.py --help
```

### Error Handling

The CLI will validate:
- Directory paths exist and are accessible
- At least one directory is specified
- At least one processing option (rename or enhance) is enabled
- Thread count is a positive number (no upper limit)