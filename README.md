# **RSP**
# *A Reef Stereo Photogrammetry toolkit for Underwater 3D Reconstruction*

## Introduction
RSP is a comprehensive toolkit designed to streamline the capture and processing of large-scale reef photogrammetry data using cheap hardware. By leveraging dual stereo cameras and an integrated workflow of software and scripts, RSP enables users to create accurate, scaled photogrammetric models of vast underwater scenes without the need for traditional scalebars. Tailored for those with little to no experience in photogrammetry, this user-friendly system automates the process, allowing for rapid generation of detailed previews of large reef environments. Whether for scientific research, conservation efforts, or underwater exploration, RSP simplifies and accelerates the production of high-quality, immersive 3D models of marine ecosystems.

***

## Main Features:

- **Automatic GoPro setup for photogrammetry** — Labs QR code and sync script, no manual configuration
- **Dataset management** — up to 3 cameras, EXIF / filename / modification-time ordering, safe batch renaming, multithreaded processing
- **Image enhancement** — CLAHE *(officially supported)* and Adaptive Grading *(beta)*
- **Desktop GUI** — dark theme, folder gallery, drag-and-drop, before/after compare viewer with live parameter preview
- **Full CLI parity** — every GUI run can be reproduced from the command line, and the saved processing report contains the exact equivalent command
- **Accurate 3D model scaling** — Metashape scripts, no physical scalebars needed
- **Standalone builds** for Windows and macOS — download them from the [Releases page](https://github.com/matteo-collina/RSP/releases), or run from source *(see [INSTALL.md](INSTALL.md))*

***

## Description

RSP take advantage of the stereo-vision to simply the production of scaled photogrammetric model for researcher and citizien scientist using common used GoPros. After the acquisition of the picture using the settings provided, the images can be imported on the data manager software, which takes care of the organization of the dataset and can perform some basic image enhancment. Later, simply import the images in the Agisoft Metashape Pro software, align your project and run the Metashape script provided.

RSP is composed of 4 elements:

1. A GoPros array *(up to 3 supported)*
2. A GoPros Sync script
3. A data manager and Image Enhancement software (GUI and CLI)
4. A series of Metashape scripts to scale the model

### 1. GoPros Array

The GoPros array can be easily crafted using rod-rails used in video-production, few rod-rails connectors and camera mounts. The rig has to contain at least 2 GoPros, but the Data Manager can handle up to 3 (check below).

IMAGE

### 2. GoPro Sync script

The GoPro sync script needs to be executed in all the GoPros of the array and keep the acquisition synced among cameras. The script is launched during GoPro boot and get executed automatically. Just shake the GoPro array to start scanning!

![GoPro Shacking Action](documentation/gopro_shake.gif)

### 3. RSP Data Manager software

When you download the images on your computer, just copy the file from each GoPro in different folders (for instance "left" and "right"). Data Manager will organize the dataset, improve the image quality and prepare the dataset to be processed in Agisoft Metashape Pro.

**Easy Usage:** 
```bash
python rsp.py                    # Launch GUI (no arguments)
python rsp.py [CLI options]      # Run CLI mode (any arguments)
```

**GUI Mode:** Launch the graphical interface for interactive processing:
```bash
python rsp.py
```

The interface lets you drag and drop the camera folders, browse the dataset in a
built-in gallery, and compare the original and enhanced version of any image
side by side before committing to a full run. When the processing is done you
can save a report of the session, which includes the equivalent CLI command so
the same run can be reproduced or scripted later.

**CLI Mode:** Any command-line argument switches to CLI mode for automated batch
processing:
```bash
python rsp.py --left /path/to/left --right /path/to/right --prefix1 "dive1" --rename true --enhance true
```

Available CLI options:

| Option | Values | Default |
| --- | --- | --- |
| `--center` / `--left` / `--right` | Path to a camera's image directory | — *(at least one required)* |
| `--prefix1` / `--prefix2` / `--prefix3` | Text prefixes for file naming | *(empty)* |
| `--thread` | Number of processing threads (minimum 1, no upper limit), or `auto` | `auto` |
| `--rename` | `true` / `false` — rename files with the prefixes | `true` |
| `--enhance` | `true` / `false` — apply image enhancement | `false` |
| `--sort` | `exif` / `filename` / `mtime` — image order before renaming | `exif` |
| `--method` | `clahe` / `gray_world` *(beta)* — enhancement method | `clahe` |
| `--param KEY=VALUE` | Override one enhancement parameter, repeatable | *(method defaults)* |
| `--help` | Show the full option list and exit | — |

At least one of `--rename` and `--enhance` must be `true`. `--param` keys are
validated against the chosen `--method`, and accept numbers only: for
`gray_world` these are `gray_world`, `warmth`, `tint`, `saturation`,
`blue_reduction`, `brightness`, `contrast`, `shadows`, `blacks`, `highlights`
and `dehaze_strength`, while `clahe`'s `clip_limit` can be set this way but its
`tile_grid_size` cannot, since it is a pair rather than a single number.

```bash
# Rename only, in alphabetical order instead of by camera timestamp
python rsp.py --left ./left --right ./right --prefix1 "2026-03-14" --prefix2 "reef" --sort filename

# Rename and enhance with the supported CLAHE method, on 8 threads
python rsp.py --left ./left --right ./right --prefix1 "dive1" --thread 8 --enhance true

# Enhance only, using the beta Adaptive Grading method with a custom saturation
python rsp.py --center ./center --rename false --enhance true --method gray_world --param saturation=1.3
```

The full command-line reference lives in [CLI_USAGE.md](CLI_USAGE.md).

#### Image Enhancement Methods

Two methods are available, both in the GUI and through `--method`:

**CLAHE** *(default, officially supported)* — Contrast Limited Adaptive
Histogram Equalization, applied per channel. This is the method we recommend and
the one to use for anything you intend to publish.

**Adaptive Grading** *(`gray_world`) — ⚠️ BETA* — A colour-correction pipeline
for underwater imagery: gray-world white balance, warmth and tint, saturation,
blue-cast reduction, brightness and contrast, shadow, black and highlight
recovery, and dehazing. It implements the same method used by
[Wildflow.ai](https://wildflow.ai) and is compatible with it — with thanks to
Sergei Nozdrenkov (wildflow.ai), whose
[gist](https://gist.github.com/nozdrenkov/e3aece3dd78489fb7862ea2bbdef0e65) this
port follows. It runs on PyTorch and automatically uses an NVIDIA GPU (CUDA),
Apple Silicon (Metal) or the CPU, whichever is available — the GUI shows which
device was detected. Every parameter is exposed as a slider with live preview in
the compare viewer.

**This method is in beta and under active development. Its output has not yet
been validated for scientific use, and its parameters and defaults may still
change. Use CLAHE for any work you intend to publish.** It also requires PyTorch,
which on Windows and Linux pulls a multi-gigabyte CUDA build by default — see
[INSTALL.md](INSTALL.md) for the much smaller CPU-only alternative.

In both cases the original pictures are never modified: enhanced images are
written to an `Enhanced` folder inside the dataset.

### 4. RSP Agisoft Metashape Pro Script

Based on the data acquired, this script will refine the alignment of your  images, and will scale the model automatically, cleaning up outliers. 

***

### Features

### Install GoPro script
To install the script you have to simply scan the QR code provided. Then, put the GoPros in Photo mode, and turn on the intervalometer function. You are ready to go!

When the GoPros turn on, you will see some values on the main scene. This means that the script has been executed. To trigger the acquistion shake vigorously the Array and the cameras will start acquiring pictures.

IMAGE

**NB: To scan the QR code the Lab version of the GoPro firmware needs to be installed. GoPro Labs currently supports HERO13/12/11/10/9/8/7 Black, HERO11 Black Mini, and HERO5 Session.**

*Please refere to the [GoPro Labs website](https://community.gopro.com/s/article/GoPro-Labs?language=en_US) on how to install the firmware on your GoPros. It requires to download and copy a zip file in your micro-sd and reboot the camera.*

### Manage the Data
When downloading the JPEGs from the SD cards, divide the dataset in three folder named center, left, right containing center, left and right camera dataset *(remove any pictures which is not part of the acquisition)*. In the Data Manager software, set up to 3 prefixes (we recommend date,divesite, dive), and specify the path of the folders (you can also drag and drop them straight onto the interface). By default the images are ordered by the camera timestamp stored in their EXIF data, but you can also sort them by filename or by file modification time. You can also decide to apply an image enhancment algorithm. If you check this option, a new panel will open and you can check how the algorithm perform on your dataset in the before/after compare viewer, adjusting its parameters until you are happy with the result. Then you can process the images.

**NB: During the process the original pictures will get renamed, but the raw data will never be modified. Image enhanced pictures will get saved in a "Enhanced" folder inside the original dataset, so you can always reverse back to non-enhanced images or perform your own enhancment.**

### Optimize the model
After the Alignment of the images in Agisoft Metashape Pro, run the script provided. Enter the distance between the Left and Right cameras *(in meters)*, set a threashold *(in meters)* to clean the data and optimize the model.

**Your model is now scaled and optimized, ready for further development!**

*For more detailed information about the usage please check our [Documention](link).*

*******

## Test Dataset

A dataset which includes physical markers to test RSP capabilities can be found at [LINK](https://vuw-my.sharepoint.com/:f:/g/personal/collinm4_staff_vuw_ac_nz/IgDWoawUu78cTLdXGB_Z39aMAeho1nQtU2GP3YPSIZHVYVs?e=x56G5I)

The dataset contains:
- RAW Images
- Enhanced and Renamed Images
- Baseline

*******

## Credits

**Software Development:** Matteo Collina

**Testing:** Manon Broadribb Payne, Miriam Pierotti

**Supervsion**: Prof. James J. Bell

**Acknowledgements:** Our thanks to Sergei Nozdrenkov ([wildflow.ai](https://wildflow.ai)) for the gray-world underwater colour-correction method that our Adaptive Grading is built on and stays compatible with, published as an open [gist](https://gist.github.com/nozdrenkov/e3aece3dd78489fb7862ea2bbdef0e65).

*A [Te Herenga Waka - Victoria University of Wellington](https://www.vuw.ac.nz) Project, Developed by [Seammetry](https://www.seammetry.org).*

If you are using this software for your research, please consider to cite:

Collina, M., Pierotti, M., Broadribb, M. et al. RSP: a reef stereo photogrammetry toolkit for time and cost-effective underwater 3D reconstruction. Coral Reefs (2026). https://doi.org/10.1007/s00338-026-02947-3
