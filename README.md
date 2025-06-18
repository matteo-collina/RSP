# **GPSP**
# *A Stereo-Photogrammetric Tool for Reef 3D Reconstruction*

## Introduction
GPSP is a comprehensive toolbox designed to streamline the capture and processing of large-scale reef photogrammetry data using cheap hardware. By leveraging dual GoPro cameras and an integrated workflow of software and scripts, GPSP enables users to create accurate, scaled photogrammetric models of vast underwater scenes without the need for traditional scalebars. Tailored for those with little to no experience in photogrammetry, this user-friendly system automates the process, allowing for rapid generation of detailed previews of large reef environments. Whether for scientific research, conservation efforts, or underwater exploration, GPSP simplifies and accelerates the production of high-quality, immersive 3D models of marine ecosystems.

***

## Main Features:
- Automatic GoPro Setting for Photogramemtry
- Dataset Managment
- Image Enhancment 
- Accurate 3D modeling scaling

***

## Description

GPSP take advantage of the stereo-vision to simply the production of scaled photogrammetric model for researcher and citizien scientist using common used GoPros. After the acquisition of the picture using the settings provided, the images can be imported on the data manager software, which takes care of the organization of the dataset and can perform some basic image enhancment. Later, simply import the images in the Agisoft Metashape Pro software, align your project and run the Metashape script provided.

GPSP is composed of 4 elements:

1. A GoPros array *(up to 3 supported)*
2. A GoPros Sync script
3. A data manager and Image Enhancment software
4. A series of Metashape scripts to scale the model

### 1. GoPros Array

The GoPros array can be easily crafted using rod-rails used in video-production, few rod-rails connectors and camera mounts. The rig has to contain at least 2 GoPros, but the Data Manager can handle up to 3 (check below).

IMAGE

### 2. GoPro Sync script

The GoPro sync script needs to be executed in all the GoPros of the array and keep the acquisition synced among cameras. The script is launched during GoPro boot and get executed automatically. Just shake the GoPro array to start scanning!

### 3. GPSP Data Manager software

When you download the images on your computer, just copy the file from each GoPro in different folders (for instance "left" and "right"). Data Manager, will organize the dataset, improve the image quality and prepare the dataset to be processed in Agisoft Metashape Pro.

IMAGE

### 4. GPSP Agisoft Metashape Pro Script

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
When downloading the JPEGs from the SD cards, divide the dataset in three folder named center, left, right containing center, left and right camera dataset *(remove any pictures which is not part of the acquisition)*. In the Data Manager software, set up to 3 prefixes (we recommend date,divesite, dive), and specify the path of the folders. You can also decide to apply an image enhancment algorithm. If you check this option, a new panel will open and you can check how the algorithm perform on your dataset. If you are happy with the result, you can process the images.

**NB: During the process the original pictures will get renamed, but the raw data will never be modified. Image enhanced pictures will get saved in a "Enhanced" folder inside the original dataset, so you can always reverse back to non-enhanced images or perform your own enhancment.**

### Optimize the model
After the Alignment of the images in Agisoft Metashape Pro, run the script provided. Enter the distance between the Left and Right cameras *(in meters)*, set a threashold *(in meters)* to clean the data and optimize the model.

**Your model is now scaled and optimized, ready for further development!**

*For more detailed information about the usage please check our [Documention](link).*

*******

## Credits

**Software Development:** Matteo Collina

**Testing:** Manon Broadribb Payne, Miriam Pierotti

**Supervsion**: Prof. James J. Bell

*A [Te Herenga Waka - Victoria University of Wellington Project](https://www.vuw.ac.nz), Developed by [Seammetry](https://www.seammetry.org).*

If you are using this software for your research, please consider to cite:
PAPER REFERENCE