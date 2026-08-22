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

Every GUI run can be reproduced from the command line: the report saved at the
end of a processing session contains the equivalent `python rsp.py ...` command.

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
- `--sort exif|filename|mtime`: Order the images are sorted in before renaming (default: exif). Only affects `--rename`:
  - `exif`: camera timestamp from the image's EXIF data (most accurate)
  - `filename`: alphabetical order
  - `mtime`: file modification time

**Enhancement Options** *(only used when `--enhance true`)*:
- `--method clahe|gray_world`: Enhancement method (default: clahe)
  - `clahe`: Contrast Limited Adaptive Histogram Equalization. The officially
    supported method — use it for anything you intend to publish.
  - `gray_world`: **Adaptive Grading — BETA.** Underwater colour correction
    (white balance, warmth/tint, saturation, blue-cast reduction, brightness
    and contrast, shadow/black/highlight recovery, dehazing), running on PyTorch
    with automatic CUDA / Apple Metal / CPU selection. Under active development:
    its output is not yet validated for scientific use, and its parameters and
    defaults may change.
- `--param KEY=VALUE`: Override a single enhancement parameter of the chosen
  method. Repeatable. Values must be plain numbers, and unknown keys for the
  selected `--method` are an error.

Valid `--param` keys per method:

| Method | Keys |
| --- | --- |
| `clahe` | `clip_limit` *(`tile_grid_size` is a pair, not a number, and cannot be set this way)* |
| `gray_world` | `gray_world`, `warmth`, `tint`, `saturation`, `blue_reduction`, `brightness`, `contrast`, `shadows`, `blacks`, `highlights`, `dehaze_strength` |

### Examples

**Basic rename only:**
```bash
python rsp.py --left /path/to/left --right /path/to/right
```

**Rename with prefixes:**
```bash
python rsp.py --left /path/to/left --prefix1 "dive1" --prefix2 "site1" --rename true
```

**Rename in alphabetical order instead of by camera timestamp:**
```bash
python rsp.py --left /path/to/left --right /path/to/right --prefix1 "dive1" --sort filename
```

**Enhance images only (no renaming):**
```bash
python rsp.py --center /path/to/center --rename false --enhance true
```

**Full processing with custom threads:**
```bash
python rsp.py --left /path/to/left --right /path/to/right --prefix1 "dive1" --thread 8 --rename true --enhance true
```

**Tune CLAHE's contrast limit:**
```bash
python rsp.py --left /path/to/left --enhance true --method clahe --param clip_limit=3.0
```

**Beta Adaptive Grading with custom saturation and dehazing:**
```bash
python rsp.py --left /path/to/left --enhance true --method gray_world --param saturation=1.3 --param dehaze_strength=0.25
```

**High-performance server processing:**
```bash
python rsp.py --left /path/to/left --thread 64 --enhance true
```

### Help

```bash
python rsp.py --help
```

### Output

Renaming happens in place, in the source directories. Enhanced images are always
written to a separate `Enhanced` folder inside each source directory, so the
original pictures are never modified.

### Error Handling

The CLI will validate:
- Directory paths exist and are accessible
- At least one directory is specified
- At least one processing option (rename or enhance) is enabled
- Thread count is a positive number (no upper limit)
- `--param` entries are in `KEY=VALUE` form, name a parameter that exists for the
  chosen `--method`, and have a numeric value
