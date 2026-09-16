"""
Agisoft Metashape Stereo Scaling Script

This script:
1. Finds stereo camera pairs (left/right naming convention)
2. Creates scalebars between stereo pairs

Usage: Run this script within Agisoft Metashape Python console
"""

import Metashape

def process_metashape_script(distance_value, optimize_cameras):
    # Get the active chunk
    chunk = Metashape.app.document.chunk

    # Get all regular cameras in the chunk
    cameras = [camera for camera in chunk.cameras if camera.type == Metashape.Camera.Type.Regular]

    # Check if there are any cameras
    if cameras:
        # Loop through each camera
        for camera1 in cameras:
            for camera2 in cameras:
                # Split the camera labels into parts
                parts1 = camera1.label.split("_")
                parts2 = camera2.label.split("_")
                
                # Ensure the labels have enough parts to process
                if len(parts1) >= 3 and len(parts2) >= 3:
                    # Extract the prefix, side, and number
                    prefix1 = "_".join(parts1[:-2])
                    prefix2 = "_".join(parts2[:-2])
                    side1 = parts1[-2]
                    side2 = parts2[-2]
                    num1 = parts1[-1]
                    num2 = parts2[-1]
                    
                    # Check if prefixes and numbers match and sides are "left" and "right"
                    if prefix1 == prefix2 and num1 == num2 and side1 == "left" and side2 == "right":
                        # Add scalebar with the provided distance
                        scalebar = chunk.addScalebar(camera1, camera2)
                        scalebar.reference.distance = distance_value
                
        # Update the chunk to reflect the changes
        chunk.updateTransform()
        
        # Count the total number of scalebars
        total_scalebars_count = len(chunk.scalebars)
        
        # Optimize cameras if requested
        if optimize_cameras:
            chunk.optimizeCameras()

        # Prepare the summary message
        summary_message = f"Total number of scalebars created: {total_scalebars_count}"
        
        Metashape.app.messageBox(summary_message)
    else:
        print("No matching cameras found in the chunk.")


def main():
    # Ask user for distance value
    distance_value = Metashape.app.getFloat("Enter distance for scalebars (m):", 1)
    
    # Ask user whether to optimize cameras
    optimize_cameras = Metashape.app.getBool("Do you want to optimize cameras after alignment?")
    
    # Call the Metashape processing function with user inputs
    process_metashape_script(distance_value, optimize_cameras,)

if __name__ == "__main__":
    main()
