# **RSP DOCUMENTATION**

This document is the official documentation for RSP.

> **NB:** This documentation is still a work in progress. The **Image Processor** is feature-complete and documented in full in the paper, with new features implemented since such as the Image Gallery and a new color-correction method in BETA. It will documented soon here. The new **RSP Metashape Plugin** is documented below, which allow for both the **Calibration** and the **Scaling**.

---

## Contents
- [GoPro Setup]() - *MISSING (REFER TO [ARTICLE](https://doi.org/10.1007/s00338-026-02947-3))*
- [RSP Image Processor]() - *MISSING (REFER TO [ARTICLE](https://doi.org/10.1007/s00338-026-02947-3))*
- [The RSP Metashape Plugin](#the-rsp-metashape-plugin)
  - [Installing the plugin](#installing-the-plugin)
  - [The RSP menu](#the-rsp-menu)
- [Stereo Baseline Calibration](#stereo-baseline-calibration)
  - [What calibration does and why it is needed](#what-calibration-does-and-why-it-is-needed)
  - [Requirements](#requirements)
  - [Step 1. Prepare the calibration target](#step-1-prepare-the-calibration-target)
  - [Step 2. Configure the cameras](#step-2-configure-the-cameras)
  - [Step 3. Acquire the calibration dataset](#step-3-acquire-the-calibration-dataset)
  - [Step 4. Sort and pre-process the images in RSP](#step-4-sort-and-pre-process-the-images-in-rsp)
  - [Step 5. Run the Calibration Wizard](#step-5-run-the-calibration-wizard)
  - [When to recalibrate](#when-to-recalibrate)
- [Scaling and Filtering a 3D Reconstruction](#scaling-and-filtering-a-3d-reconstruction)
  - [RSP > Scaling](#rsp--scaling)
  - [RSP > Filter Scalebars](#rsp--filter-scalebars)
- [Troubleshooting]() - *TO BE WRITTEN*
- [Frequent Asked Questions]() - *TO BE WRITTEN*

---

## The RSP Metashape Plugin

The RSP Metashape plugin adds an **RSP** menu to Agisoft Metashape, replacing the older standalone scripts described in the original paper (`stereo_scale.py`, `stereo_report.py`, `stereo_calibration.py`) with a guided, in-app workflow for calibrating a stereo rig and scaling reconstructions. The legacy scripts remain in `/archive` with the [OLD DOCUMENTATION](/archive/OLD_CALIBRATION.md) and still work if you prefer them, but __the plugin is the recommended way__ to do both from here on.

Requires **Agisoft Metashape Professional** — the Standard edition cannot run Python scripts or plugins.

---

### Installing the plugin

There are two ways to get the **RSP** menu into Metashape. 

#### Option A: Permanent installation (recommended)

1. Close Metashape.
2. Open **RSP Image Processor** and choose **Tools > Install RSP Metashape Plugin**.
3. Check the **Metashape scripts folder**. RSP detects your operating system and fills in Metashape Pro's startup scripts folder:

   | OS | Metashape scripts folder |
   | --- | --- |
   | Windows | `%APPDATA%\Agisoft\Metashape Pro\scripts` (e.g. `C:\Users\YourName\AppData\Roaming\Agisoft\Metashape Pro\scripts`) |
   | macOS | `~/Library/Application Support/Agisoft/Metashape Pro/scripts` |
   | Linux | `~/.local/share/Agisoft/Metashape Pro/scripts` |

   Use **Browse...** only if your Metashape installation keeps its scripts somewhere else.
4. Click **Install**.
5. Start Metashape. The **RSP** menu appears in the menu bar.

- **Updating:** after updating RSP, run **Install RSP Metashape Plugin** again. It replaces the previous version of the plugin.

#### Option B: Manual launch (alternative)

If you prefer not to install anything, you can load the plugin by hand. This has to be repeated every time Metashape is started:

1. Open Metashape.
2. **Tools > Run Script...**
3. Select `scripts/rsp_plugin_loader.py` from this repository.

An **RSP** menu appears in Metashape's menu bar until Metashape is closed. Keep `rsp_plugin_loader.py`, the `rsp_plugin` folder and `scalebars.csv` together in the `scripts` folder: the loader expects them next to it.

---

### The RSP menu

| Menu item | Purpose |
| --- | --- |
| **RSP > Calibration Wizard** | Guided end-to-end stereo baseline calibration — see [Stereo Baseline Calibration](#stereo-baseline-calibration). |
| **RSP > Scaling** | Apply a known baseline to a new survey and create scalebars — see [Scaling and Filtering](#scaling-and-filtering-a-3d-reconstruction). |
| **RSP > Filter Scalebars** | Re-open the filtering panel against scalebars that already exist in the chunk. |

---

## Stereo Baseline Calibration

This guide describes how to calibrate the stereo baseline of an RSP camera rig and how to apply the resulting value when scaling reconstructions.

---

### What calibration does and why it is needed

A photogrammetric reconstruction built from a single moving camera is geometrically correct but dimensionless: the model has shape, but not size. Introducing a second camera at a fixed, known separation supplies that missing dimension. Every synchronised image pair observes the scene from two viewpoints whose relative distance is constant, so the reconstruction can be scaled without placing any physical reference object in the scene.

The purpose of calibration is to measure the **baseline**, as accurately as possible. It is not sufficient to measure the distance between the housings with a ruler: the value that matters is the distance between the optical centres of the two lenses, which sits somewhere inside each housing and cannot be reached directly.

The output is a single value in metres, together with a report describing how consistent the individual pair estimates were. That scale is then reused to scale every subsequent survey acquired with the same rig, for as long as the rig geometry is undisturbed. 

__PLEASE REMEMBER TO SAVE AND STORE THE CALIBRATION FILE__

---

### Requirements

**Hardware**

- An RSP rig with two cameras (`left`, `right`). Three-camera rigs are supported: the third position is treated as `center`.
- The printed scalebar sheet from `scripts/` (see Step 1), or your own set of coded targets with known separations.
- A rigid, flat surface on which to lay the targets.

**Software**

- Agisoft Metashape **Professional** edition. The Standard edition cannot run Python scripts and cannot be used for calibration.
- The RSP data manager (GUI or CLI).
- The RSP Metashape plugin, installed or loaded as described [above](#installing-the-plugin).

**Conditions**

Calibration can be performed dry. In most cases a dry calibration is preferable because the targets stay flat and the session is quicker.

---

#### Step 1. Prepare the calibration target

A printable PDF of coded markers with certified spacings is included in the `scripts/` folder of this repository. Print it at **100 % scale**, with any "fit to page" or "shrink to fit" option disabled, then verify one known distance with a ruler or calipers before use.

Custom targets are equally acceptable. The only requirement is that you know the distances between markers to a precision at least as good as the accuracy you expect from the final reconstruction. Mount the sheet on foam board, acrylic, or another rigid backing: paper that curls or lifts introduces error that is difficult to detect afterwards.

---

#### Step 2. Configure the cameras

Scan the RSP QR configuration code with each camera. You can find the QR code under `Tools/GoPro QR code` in the RSP Image Processor. This sets the capture parameters shared across the rig.
Set the interval-shooting to 1s.

**The intervalometer must be set manually on each camera. The QR code does not set it.**

Everything else in the capture configuration is applied by the QR code and should not be changed by hand.

---

#### Step 3. Acquire the calibration dataset

Lay the targets on the floor or on a rigid surface, then perform a normal photogrammetric acquisition over them.

Practical guidance:

- Cover an area of roughly **1 x 1 m**.
- Collect **50 to 70 images per camera**. In practice this is about a minute of capture.
- Move steadily around and across the target area, varying viewing angle and height so that each marker is seen from several directions. Convergent geometry produces a far more stable solution than a single flat pass.
- Keep the whole target in frame for both cameras as often as possible.
- Use even, diffuse lighting and avoid specular reflections on the printed sheet, which can defeat marker detection.

---

#### Step 4. Sort and pre-process the images in RSP

1. Download the images from each camera into **separate folders**, one per camera position: `left`, `right`, and `center` if the rig carries three.
2. Open RSP and import the folders, assigning each to its camera position.
3. Set a project **prefix**. Choose something that identifies the rig and the session, for example `rigA_calib_2026-08`.
4. Run **image processing**. It is not necessary to run the Image Enhancement if the calibration has not been performed in the water.

RSP renames every file according to the pattern below, which is what allows the plugin to recognise which images belong to which camera and which images form a pair:

```
<prefix>_left_XXXX
<prefix>_right_XXXX
<prefix>_center_XXXX
```

**Do not rename or reorder the outputs after this step.**

---

#### Step 5. Run the Calibration Wizard

With the plugin [loaded](#installing-the-plugin):

1. **RSP > Calibration Wizard.**

2. In the setup panel, browse to the **Left** and **Right** folders from Step 4 (and **Center**, if your rig has a third camera).

3. Choose whether you used **RSP's printed calibration target** or **custom markers**. If custom, pick the marker type you used from the dropdown (circular targets, AprilTags, etc.) once detection runs.

4. Pick the **camera / lens model** (Frame, Fisheye, etc.) that matches your rig. This applies to every camera in the rig — a mismatched setting here will hurt alignment quality.

5. Click **OK**. The wizard imports the photos, applies the camera model, detects the markers, aligns the cameras, and computes the baseline directly from the aligned project.

>If custom markers are used, after the marker detection you will be asked to enter the distance between the custom coded markers.

6. The results dialog shows the recommended baseline (median), the mean, standard deviation and coefficient of variation across every detected pair, and a chart of the individual estimates. A coefficient of variation under 2% is excellent; above 10% suggests recalibrating.

7. Click **Save calibration file...** to save the report, and record the baseline value together with the rig identifier and date somewhere durable — it is easy to lose track of which value belongs to which rig once you are running more than one.

---

## When to recalibrate

Recalibrate whenever the physical relationship between the cameras may have changed:

- after any disassembly, remounting, or opening of the housings;
- after a knock, a drop, or shipping;
- when moving to a different rig or swapping a camera body;
- periodically during long field campaigns, as a check on drift.

A calibration takes about a minute of capture and a short processing run. Repeating it when in doubt costs far less than discovering afterwards that a season of surveys was scaled with a wrong value.

---

## Scaling and Filtering a 3D Reconstruction

Once a rig's baseline is known (see [Calibration](#stereo-baseline-calibration)), use it to scale every subsequent survey captured with that rig.

Process and align the survey images in RSP and Metashape as usual, using the same `<prefix>_left/right/center_XXXX` naming convention, then use the RSP menu.

---

### RSP > Scaling

1. With the aligned chunk active, **RSP > Scaling**.
2. Enter the **baseline distance** (in metres) measured during calibration, and choose whether to optimize cameras afterwards.
3. Click **OK**. The plugin creates a scalebar for every detected stereo pair at that baseline and updates the scene.

A stats panel then opens and stays open:

- **RMS, mean, standard deviation and max error** across all current scalebars.

- A **per-scalebar error chart**, plotted by camera sequence, so a desync partway through the dive (the error drifting from the first camera pair to the last) is visible at a glance.

- **Should exist / Created / Remaining** counts.

**Filtering:** drag the dashed threshold lines on the chart (or type a value into the threshold field) to preview which scalebars would be removed — they highlight in red. Click **Apply Filter** to actually remove them and refresh the scene. 

You can repeat this with different thresholds without closing the panel.

---

### RSP > Filter Scalebars

Opens the same stats/filtering panel directly against whatever scalebars already exist in the active chunk. Use this to revisit filtering later in a session.

---

*Last updated: `16/09/2026`*
